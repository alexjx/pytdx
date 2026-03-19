#!/usr/bin/env python3
# coding: utf-8

import argparse
import csv
import datetime as dt
import re
import struct
import zlib
from collections import Counter, defaultdict

try:
    from scapy.all import rdpcap, TCP, Raw, IP
except ImportError:
    print("Error: scapy not installed. Run with:")
    print("  uv run --with scapy python analyze/market_flow_experiment.py <pcap>")
    raise SystemExit(1)


CODE_RE = re.compile(rb"\d{6}")
REC_START_RE = re.compile(rb"([\x00-\x03])(\d{6})")


def ts_str(epoch):
    return dt.datetime.fromtimestamp(float(epoch)).strftime("%H:%M:%S.%f")[:-3]


def printable_preview(blob, skip=0, size=220):
    s = blob[skip: skip + size].decode("utf-8", "replace")
    return "".join(ch if 32 <= ord(ch) < 127 else "." for ch in s)


def parse_requests(packets, port):
    req = []
    for p in packets:
        if not (p.haslayer(IP) and p.haslayer(TCP) and p.haslayer(Raw)):
            continue
        tcp = p[TCP]
        raw = bytes(p[Raw].load)
        if tcp.dport != port or len(raw) < 16:
            continue
        cmd = struct.unpack("<H", raw[2:4])[0]
        zsize = struct.unpack("<H", raw[12:14])[0]
        usize = struct.unpack("<H", raw[14:16])[0]
        body = raw[16:]
        codes = [m.decode() for m in CODE_RE.findall(body)]
        req.append({
            "time": float(p.time),
            "cmd": cmd,
            "len": len(raw),
            "zsize": zsize,
            "usize": usize,
            "head16": raw[:16],
            "body": body,
            "codes": codes,
        })
    return req


def dominant_server_stream(packets, port):
    streams = defaultdict(list)
    for p in packets:
        if not (p.haslayer(IP) and p.haslayer(TCP) and p.haslayer(Raw)):
            continue
        ip = p[IP]
        tcp = p[TCP]
        raw = bytes(p[Raw].load)
        if tcp.sport != port or len(raw) == 0:
            continue
        key = (ip.src, tcp.sport, ip.dst, tcp.dport)
        streams[key].append((int(tcp.seq), float(p.time), raw))
    if not streams:
        return None, []
    key, segs = max(streams.items(), key=lambda kv: sum(len(x[2]) for x in kv[1]))
    return key, sorted(segs, key=lambda x: x[0])


def reassemble_stream(segs):
    buf = b""
    offset_time = {}
    expected = None
    offset = 0
    for seq, t, pay in segs:
        if expected is None:
            expected = seq
        if seq > expected:
            gap = seq - expected
            buf += b"\x00" * gap
            offset += gap
            expected = seq
        if seq < expected:
            overlap = expected - seq
            if overlap >= len(pay):
                continue
            pay = pay[overlap:]
            seq = expected
        offset_time[offset] = t
        buf += pay
        offset += len(pay)
        expected = seq + len(pay)
    return buf, offset_time


def parse_response_frames(reassembled, offset_time):
    frames = []
    pos = 0
    n = len(reassembled)
    while pos + 16 <= n:
        # response header signature
        if not (reassembled[pos + 1:pos + 4] == b"\xcb\x74\x00" and reassembled[pos] in (0xb1, 0xbc)):
            pos += 1
            continue
        zsize = struct.unpack("<H", reassembled[pos + 12:pos + 14])[0]
        usize = struct.unpack("<H", reassembled[pos + 14:pos + 16])[0]
        total = 16 + zsize
        if zsize == 0 or zsize > 200000:
            pos += 1
            continue
        if pos + total > n:
            break
        fr = reassembled[pos: pos + total]
        cmd = struct.unpack("<H", fr[6:8])[0]
        ref = struct.unpack("<H", fr[4:6])[0]
        body = fr[16:]
        payload = body
        if zsize != usize:
            try:
                payload = zlib.decompress(body)
            except Exception:
                payload = body
        codes = [m.decode() for m in CODE_RE.findall(payload)]
        frames.append({
            "stream_offset": pos,
            "time": offset_time.get(pos),
            "cmd": cmd,
            "ref": ref,
            "zsize": zsize,
            "usize": usize,
            "raw_body_len": len(body),
            "decoded_len": len(payload),
            "decoded": payload,
            "codes": codes,
        })
        pos += total
    return frames


def command_name(cmd):
    names = {
        0x6320: "GetSecurityQuotes",
        0x6A10: "GetBlockInfo",
        0x9318: "SetupCmd1",
        0x9418: "SetupCmd2",
        0x9918: "SetupCmd3",
        0x6418: "GetSecurityList",
        0x6C18: "GetSecurityCount",
    }
    return names.get(cmd, "Unknown")


def print_request_summary(req):
    print("== Request Summary ==")
    print("request packets:", len(req))
    cnt = Counter(r["cmd"] for r in req)
    for cmd, n in cnt.most_common():
        lens = [r["len"] for r in req if r["cmd"] == cmd]
        print(f"  0x{cmd:04x} ({command_name(cmd)}): {n:3d}  len={min(lens)}-{max(lens)}")
    print("contains 0x6418(GetSecurityList):", any(r["cmd"] == 0x6418 for r in req))
    print("contains 0x6c18(GetSecurityCount):", any(r["cmd"] == 0x6C18 for r in req))
    print()


def print_time_buckets(req):
    print("== Request Timeline (per second) ==")
    by_sec = defaultdict(list)
    for r in req:
        by_sec[int(r["time"])].append(r["cmd"])
    for sec in sorted(by_sec):
        top = Counter(by_sec[sec]).most_common(8)
        msg = ", ".join([f"0x{cmd:04x}x{n}" for cmd, n in top])
        print(dt.datetime.fromtimestamp(sec).strftime("%H:%M:%S"), "->", msg)
    print()


def print_request_details(req, limit):
    print("== Request Details ==")
    for i, r in enumerate(req[:limit], 1):
        print(
            f"{i:03d} {ts_str(r['time'])} cmd=0x{r['cmd']:04x} "
            f"({command_name(r['cmd'])}) len={r['len']} z/u={r['zsize']}/{r['usize']}"
        )
        if r["codes"]:
            print("    codes:", ",".join(r["codes"][:16]))
    print()


def print_response_summary(frames):
    print("== Reassembled Response Summary ==")
    print("response frames:", len(frames))
    cnt = Counter(f["cmd"] for f in frames)
    for cmd, n in cnt.most_common():
        print(f"  0x{cmd:04x} ({command_name(cmd)}): {n:3d}")
    print()


def likely_list_commands(frames):
    by_cmd = defaultdict(list)
    for f in frames:
        by_cmd[f["cmd"]].append(f)

    candidates = []
    for cmd, arr in by_cmd.items():
        has_table_json = any((b"colheader" in f["decoded"] and b"data" in f["decoded"]) for f in arr)
        avg_codes = sum(len(f["codes"]) for f in arr) / max(1, len(arr))
        is_bulk_codes = len(arr) >= 3 and avg_codes >= 8
        if has_table_json or is_bulk_codes:
            candidates.append((cmd, len(arr), has_table_json, avg_codes))
    candidates.sort(key=lambda x: (-x[2], -x[3], -x[1], x[0]))
    return candidates


def decode_6320_prefix_rows(payload):
    if len(payload) < 4:
        return []
    rec_starts = []
    last = -1000
    for m in REC_START_RE.finditer(payload, 4):
        s = m.start(0)
        # drop nearby duplicate matches
        if s - last < 40:
            continue
        rec_starts.append(s)
        last = s

    rows = []
    for idx, s in enumerate(rec_starts):
        e = rec_starts[idx + 1] if idx + 1 < len(rec_starts) else len(payload)
        rec = payload[s:e]
        if len(rec) < 24:
            continue
        market = rec[0]
        code = rec[1:7].decode("ascii", "ignore")
        if len(code) != 6 or not code.isdigit():
            continue
        active1 = struct.unpack("<H", rec[7:9])[0]
        p = 9
        try:
            # same variable-int prefix encoding as pytdx helper.get_price
            from pytdx.helper import get_price

            price_raw, p = get_price(rec, p)
            last_close_diff, p = get_price(rec, p)
            open_diff, p = get_price(rec, p)
            high_diff, p = get_price(rec, p)
            low_diff, p = get_price(rec, p)
            _time_like, p = get_price(rec, p)
            _neg_price_like, p = get_price(rec, p)
            vol, p = get_price(rec, p)
            cur_vol, p = get_price(rec, p)
        except Exception:
            continue

        rows.append(
            {
                "market": market,
                "code": code,
                "active1": active1,
                "price": price_raw / 100.0,
                "last_close": (price_raw + last_close_diff) / 100.0,
                "open": (price_raw + open_diff) / 100.0,
                "high": (price_raw + high_diff) / 100.0,
                "low": (price_raw + low_diff) / 100.0,
                "vol": vol,
                "cur_vol": cur_vol,
            }
        )
    return rows


def print_6320_decode(frames, limit_frames=6, limit_rows=12):
    targets = [f for f in frames if f["cmd"] == 0x6320]
    print("== 0x6320 Decode Experiment ==")
    if not targets:
        print("no 0x6320 frames found")
        print()
        return
    print("0x6320 frames:", len(targets))
    for i, f in enumerate(targets[:limit_frames], 1):
        rows = decode_6320_prefix_rows(f["decoded"])
        ts = "?" if f["time"] is None else ts_str(f["time"])
        header_num = struct.unpack("<H", f["decoded"][2:4])[0] if len(f["decoded"]) >= 4 else None
        print(
            f"frame#{i} t={ts} ref=0x{f['ref']:04x} header_num={header_num} "
            f"decoded_rows={len(rows)}"
        )
        for r in rows[:limit_rows]:
            print(
                " ",
                r["market"],
                r["code"],
                f"price={r['price']:.2f}",
                f"open={r['open']:.2f}",
                f"high={r['high']:.2f}",
                f"low={r['low']:.2f}",
                f"vol={r['vol']}",
            )
        bj_rows = [r for r in rows if r["code"].startswith("920")]
        if bj_rows:
            print("  BJ codes:", ",".join(r["code"] for r in bj_rows))
    print()


def _group_contiguous_refs(rows):
    # 7d2c chunk refs in this capture increase by 0x100 for same table batch.
    rows = sorted(rows, key=lambda x: x["ref"])
    groups = []
    cur = []
    prev = None
    for r in rows:
        if prev is None or r["ref"] - prev == 0x0100:
            cur.append(r)
        else:
            groups.append(cur)
            cur = [r]
        prev = r["ref"]
    if cur:
        groups.append(cur)
    return groups


def assemble_7d2c_table(frames):
    chunks = [f for f in frames if f["cmd"] == 0x7D2C and len(f["decoded"]) >= 4]
    if not chunks:
        return None

    best = None
    for grp in _group_contiguous_refs(chunks):
        blob = b"".join(x["decoded"][4:] for x in sorted(grp, key=lambda y: y["ref"]))
        start = blob.find(b"{")
        end = blob.rfind(b"}")
        if start < 0 or end <= start:
            continue
        cand = blob[start:end + 1]
        try:
            obj = __import__("json").loads(cand.decode("utf-8"))
        except Exception:
            continue
        score = len(obj.get("data", []))
        if best is None or score > best["rows"]:
            best = {
                "group": grp,
                "json_obj": obj,
                "rows": score,
                "cols": len(obj.get("colheader", [])),
            }
    return best


def print_7d2c_table_info(frames, focus_codes):
    print("== 0x7d2c Table Decode ==")
    res = assemble_7d2c_table(frames)
    if not res:
        print("no decodable 0x7d2c table found")
        print()
        return None

    obj = res["json_obj"]
    headers = obj.get("colheader", [])
    data = obj.get("data", [])
    print(
        f"decoded table rows={len(data)} cols={len(headers)} "
        f"chunks={len(res['group'])} ref_range=0x{res['group'][0]['ref']:04x}-0x{res['group'][-1]['ref']:04x}"
    )
    print("headers:", headers)
    print("first row:", data[0] if data else None)

    if focus_codes:
        idx = 0
        for code in focus_codes:
            hit = [r for r in data if len(r) > idx and str(r[idx]) == code]
            print(f"focus {code}: {'FOUND' if hit else 'NOT_FOUND'}")
            if hit:
                print("  row:", hit[0])
    print()
    return obj


def export_table_csv(table_obj, csv_path):
    headers = table_obj.get("colheader", [])
    data = table_obj.get("data", [])
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if headers:
            w.writerow(headers)
        for row in data:
            w.writerow(row)


def print_7d2c_mapping(table_obj, focus_codes):
    print("== 0x7d2c Column Mapping (Hypothesis) ==")
    mapping = [
        ("$ZQDM", "代码", "high"),
        ("$SC", "市场(0=SZ,1=SH,2=BJ?)", "high"),
        ("$ZQDM1", "关联指数/标的代码", "high"),
        ("$SC1", "关联标的市场ID", "medium"),
        ("JZRQ", "净值日期", "high"),
        ("DWJZ", "单位净值", "high"),
        ("ZXFE", "规模(元)", "high"),
        ("FEBH", "规模日变化(份额/元口径待确认)", "high"),
        ("ZFEBH", "规模周变化(口径待确认)", "high"),
        ("YFEBH", "规模月变化(口径待确认)", "high"),
        ("YZGM", "份额或资产总量A(待确认)", "low"),
        ("YYGM", "份额或资产总量B(待确认)", "low"),
        ("ZXSSDW", "最小申赎单位(万份)", "high"),
    ]
    for raw, zh, conf in mapping:
        print(f"  {raw:8s} -> {zh}   confidence={conf}")

    if not table_obj:
        print()
        return

    headers = table_obj.get("colheader", [])
    rows = table_obj.get("data", [])
    idx = {h: i for i, h in enumerate(headers)}
    print("\nvalue check (focus codes):")
    for code in focus_codes:
        hit = next((r for r in rows if len(r) > 0 and str(r[0]) == code), None)
        if not hit:
            continue
        parts = [f"code={code}"]
        for h in ["JZRQ", "DWJZ", "ZXFE", "FEBH", "ZFEBH", "YFEBH", "YZGM", "YYGM", "ZXSSDW"]:
            if h in idx and idx[h] < len(hit):
                v = hit[idx[h]]
                if h in ("ZXFE", "FEBH", "ZFEBH", "YFEBH", "YZGM", "YYGM"):
                    try:
                        v = f"{float(v)/1e8:.2f}亿"
                    except Exception:
                        pass
                parts.append(f"{h}={v}")
        print("  " + " | ".join(parts))
    print()


def print_list_candidates(frames):
    print("== Likely List-Like Commands ==")
    cands = likely_list_commands(frames)
    if not cands:
        print("No obvious list-like command found.")
        print()
        return
    by_cmd = defaultdict(list)
    for f in frames:
        by_cmd[f["cmd"]].append(f)

    for cmd, n, has_table_json, avg_codes in cands:
        print(
            f"cmd=0x{cmd:04x} ({command_name(cmd)}) frames={n} "
            f"table_json={has_table_json} avg_codes={avg_codes:.1f}"
        )
        f = by_cmd[cmd][0]
        t = "?" if f["time"] is None else ts_str(f["time"])
        print(
            f"  sample t={t} ref=0x{f['ref']:04x} z/u={f['zsize']}/{f['usize']} "
            f"raw/dec={f['raw_body_len']}/{f['decoded_len']}"
        )
        if f["codes"]:
            print("  sample codes:", ",".join(f["codes"][:20]))
        for skip in (0, 2, 4):
            print(f"  preview+{skip}:", printable_preview(f["decoded"], skip=skip))
    print()


def main():
    ap = argparse.ArgumentParser(
        description="Experiment analyzer for market/list flow in TDX pcap files"
    )
    ap.add_argument("pcap_file", help="PCAP/PCAPNG file path")
    ap.add_argument("--port", type=int, default=7709, help="TDX port (default: 7709)")
    ap.add_argument(
        "--request-limit",
        type=int,
        default=140,
        help="print at most N request rows in details section",
    )
    ap.add_argument(
        "--focus-codes",
        default="513350,159518,515220,920000",
        help="comma-separated codes to check in decoded 0x7d2c table",
    )
    ap.add_argument(
        "--export-7d2c-csv",
        default="",
        help="if set, export decoded 0x7d2c table to this csv path",
    )
    args = ap.parse_args()

    packets = rdpcap(args.pcap_file)
    req = parse_requests(packets, args.port)
    stream_key, segs = dominant_server_stream(packets, args.port)

    print("== Input ==")
    print("file:", args.pcap_file)
    print("port:", args.port)
    print("total packets:", len(packets))
    print()

    print_request_summary(req)
    print_time_buckets(req)
    print_request_details(req, args.request_limit)

    if not segs:
        print("No server stream found for response reassembly.")
        return

    reassembled, offset_time = reassemble_stream(segs)
    frames = parse_response_frames(reassembled, offset_time)
    print("== Response Stream ==")
    print("stream:", stream_key)
    print("segments:", len(segs))
    print("reassembled bytes:", len(reassembled))
    print()

    print_response_summary(frames)
    print_list_candidates(frames)
    print_6320_decode(frames)
    focus_codes = [x.strip() for x in args.focus_codes.split(",") if x.strip()]
    table_obj = print_7d2c_table_info(frames, focus_codes)
    if table_obj and args.export_7d2c_csv:
        export_table_csv(table_obj, args.export_7d2c_csv)
        print("exported 0x7d2c table csv:", args.export_7d2c_csv)
    if table_obj:
        print_7d2c_mapping(table_obj, focus_codes)


if __name__ == "__main__":
    main()
