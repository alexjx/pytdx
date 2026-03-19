#!/usr/bin/env python3
# coding: utf-8

"""
Experimental market APIs derived from pcap reverse-engineering.

These APIs are intentionally scoped to pcap analysis (offline),
but shaped as production-like interfaces for future live integration.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import csv
import re
import struct
import zlib
import json
from collections import defaultdict

from pytdx.helper import get_price

try:
    from scapy.all import rdpcap, TCP, Raw, IP
except ImportError:  # pragma: no cover
    rdpcap = None
    TCP = Raw = IP = None


REC_START_RE = re.compile(rb"([\x00-\x03])(\d{6})")


@dataclass
class PacketMeta:
    cmd: int
    ref: int
    zsize: int
    usize: int
    timestamp: Optional[float]


@dataclass
class QuoteRow:
    market: int
    code: str
    price: float
    open: float
    high: float
    low: float
    vol: int
    cur_vol: int
    active1: int


@dataclass
class MarketQuotesSnapshot:
    source_cmd: int
    packet: PacketMeta
    rows: List[QuoteRow]
    partial: bool
    errors: List[str]


@dataclass
class EtfPanelTable:
    source_cmd: int
    columns: List[str]
    rows: List[List[str]]
    packet_refs: List[int]
    incomplete: bool
    errors: List[str]
    focus_rows: Dict[str, List[str]]


def _ensure_scapy():
    if rdpcap is None:
        raise RuntimeError(
            "scapy not installed. Use: uv run --with scapy python <script>.py"
        )


def _dominant_server_stream(pcap_file: str, port: int):
    _ensure_scapy()
    streams = defaultdict(list)
    for p in rdpcap(pcap_file):
        if not (p.haslayer(IP) and p.haslayer(TCP) and p.haslayer(Raw)):
            continue
        ip = p[IP]
        tcp = p[TCP]
        raw = bytes(p[Raw].load)
        if tcp.sport != port or not raw:
            continue
        streams[(ip.src, tcp.sport, ip.dst, tcp.dport)].append(
            (int(tcp.seq), float(p.time), raw)
        )
    if not streams:
        return None, []
    key, segs = max(streams.items(), key=lambda kv: sum(len(x[2]) for x in kv[1]))
    return key, sorted(segs, key=lambda x: x[0])


def _reassemble_stream(segs):
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


def _parse_response_frames(reassembled, offset_time):
    frames = []
    pos = 0
    n = len(reassembled)
    while pos + 16 <= n:
        if not (
            reassembled[pos + 1:pos + 4] == b"\xcb\x74\x00"
            and reassembled[pos] in (0xB1, 0xBC)
        ):
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

        frames.append(
            {
                "cmd": cmd,
                "ref": ref,
                "zsize": zsize,
                "usize": usize,
                "timestamp": offset_time.get(pos),
                "decoded": payload,
            }
        )
        pos += total
    return frames


def _decode_6320_rows(payload: bytes) -> List[QuoteRow]:
    rec_starts = []
    last = -1000
    for m in REC_START_RE.finditer(payload, 4):
        s = m.start(0)
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
            price_raw, p = get_price(rec, p)
            last_close_diff, p = get_price(rec, p)
            open_diff, p = get_price(rec, p)
            high_diff, p = get_price(rec, p)
            low_diff, p = get_price(rec, p)
            _, p = get_price(rec, p)
            _, p = get_price(rec, p)
            vol, p = get_price(rec, p)
            cur_vol, p = get_price(rec, p)
        except Exception:
            continue

        rows.append(
            QuoteRow(
                market=market,
                code=code,
                price=price_raw / 100.0,
                open=(price_raw + open_diff) / 100.0,
                high=(price_raw + high_diff) / 100.0,
                low=(price_raw + low_diff) / 100.0,
                vol=vol,
                cur_vol=cur_vol,
                active1=active1,
            )
        )
    return rows


def _group_7d2c_contiguous_refs(rows):
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


def _assemble_7d2c_table(frames):
    chunks = [f for f in frames if f["cmd"] == 0x7D2C and len(f["decoded"]) >= 4]
    best = None
    for grp in _group_7d2c_contiguous_refs(chunks):
        blob = b"".join(x["decoded"][4:] for x in sorted(grp, key=lambda y: y["ref"]))
        start = blob.find(b"{")
        end = blob.rfind(b"}")
        if start < 0 or end <= start:
            continue
        try:
            obj = json.loads(blob[start:end + 1].decode("utf-8"))
        except Exception:
            continue
        rows = obj.get("data", [])
        if best is None or len(rows) > len(best["rows"]):
            best = {
                "columns": obj.get("colheader", []),
                "rows": rows,
                "refs": [x["ref"] for x in grp],
            }
    return best


def get_market_quotes_snapshot(
    pcap_file: str,
    market_hint: Optional[int] = None,
    codes: Optional[List[str]] = None,
    port: int = 7709,
) -> MarketQuotesSnapshot:
    """
    API-1: parse quote snapshot from 0x6320.

    market_hint: optional market filter, e.g. 2 for BJ
    codes: optional whitelist filter
    """
    key, segs = _dominant_server_stream(pcap_file, port)
    if not segs:
        return MarketQuotesSnapshot(
            source_cmd=0x6320,
            packet=PacketMeta(0x6320, 0, 0, 0, None),
            rows=[],
            partial=True,
            errors=["no server stream found"],
        )
    reassembled, offset_time = _reassemble_stream(segs)
    frames = _parse_response_frames(reassembled, offset_time)
    targets = [f for f in frames if f["cmd"] == 0x6320]
    if not targets:
        return MarketQuotesSnapshot(
            source_cmd=0x6320,
            packet=PacketMeta(0x6320, 0, 0, 0, None),
            rows=[],
            partial=True,
            errors=["no 0x6320 response frame found"],
        )

    decoded = [(f, _decode_6320_rows(f["decoded"])) for f in targets]

    def _apply_filters(rows):
        out = rows
        if market_hint is not None:
            out = [r for r in out if r.market == market_hint]
        if codes:
            keep = set(codes)
            out = [r for r in out if r.code in keep]
        return out

    ranked = []
    for f, rows in decoded:
        filtered = _apply_filters(rows)
        ranked.append((f, rows, filtered))

    # choose frame with maximum filtered rows; tie-break by original row count
    frame, rows, filtered_rows = max(ranked, key=lambda x: (len(x[2]), len(x[1])))
    rows = filtered_rows

    return MarketQuotesSnapshot(
        source_cmd=0x6320,
        packet=PacketMeta(
            cmd=0x6320,
            ref=frame["ref"],
            zsize=frame["zsize"],
            usize=frame["usize"],
            timestamp=frame["timestamp"],
        ),
        rows=rows,
        partial=False,
        errors=[],
    )


def get_etf_panel_table(
    pcap_file: str,
    focus_codes: Optional[List[str]] = None,
    port: int = 7709,
) -> EtfPanelTable:
    """
    API-2: parse 0x7d2c chunked ETF panel table.
    """
    key, segs = _dominant_server_stream(pcap_file, port)
    if not segs:
        return EtfPanelTable(
            source_cmd=0x7D2C,
            columns=[],
            rows=[],
            packet_refs=[],
            incomplete=True,
            errors=["no server stream found"],
            focus_rows={},
        )
    reassembled, offset_time = _reassemble_stream(segs)
    frames = _parse_response_frames(reassembled, offset_time)
    table = _assemble_7d2c_table(frames)
    if not table:
        return EtfPanelTable(
            source_cmd=0x7D2C,
            columns=[],
            rows=[],
            packet_refs=[],
            incomplete=True,
            errors=["cannot assemble/decode 0x7d2c table"],
            focus_rows={},
        )

    focus_rows: Dict[str, List[str]] = {}
    if focus_codes:
        for code in focus_codes:
            hit = next((r for r in table["rows"] if len(r) > 0 and str(r[0]) == code), None)
            if hit:
                focus_rows[code] = hit

    return EtfPanelTable(
        source_cmd=0x7D2C,
        columns=table["columns"],
        rows=table["rows"],
        packet_refs=table["refs"],
        incomplete=False,
        errors=[],
        focus_rows=focus_rows,
    )


def export_etf_panel_table_csv(table: EtfPanelTable, csv_path: str) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if table.columns:
            w.writerow(table.columns)
        for row in table.rows:
            w.writerow(row)
