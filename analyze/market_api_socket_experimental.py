#!/usr/bin/env python3
# coding: utf-8

"""
Experimental live-socket market APIs.

API-1
-----
Use native `get_security_quotes` (0x6320) over socket.

API-2
-----
Replay the observed sequence for ETF panel table:
`0x7c2c (init) -> 0xc920 (warmup) -> 0x7d2c (chunk pull)`.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple, Dict
import json
import struct
import time

from pytdx.hq import TdxHq_API
from pytdx.params import TDXParams

try:
    from .market_api_experimental import (
        EtfPanelTable,
        MarketQuotesSnapshot,
        PacketMeta,
        QuoteRow,
    )
except ImportError:  # pragma: no cover
    from market_api_experimental import (  # type: ignore
        EtfPanelTable,
        MarketQuotesSnapshot,
        PacketMeta,
        QuoteRow,
    )


DEFAULT_PANEL_PATH = "bi_diy/list/gxjty_etfjj101.jsn"
DEFAULT_ETF_WARMUP = (0, "159919")


def _build_7c2c_init_pkg(panel_path: str) -> bytes:
    path40 = panel_path.encode("ascii")[:40]
    path40 += b"\x00" * (40 - len(path40))
    return bytes.fromhex("0c012c7c00012a002a00c502") + path40


def _build_c920_warmup_pkg(market: int, code: str) -> bytes:
    # Template observed in capture; only market/code are substituted.
    pkg = bytearray.fromhex("0c0320c908010f000f00470501000031353939313900000000")
    pkg[17] = market & 0xFF
    code6 = code.encode("ascii", "ignore")[:6]
    pkg[19:25] = code6 + b"\x00" * (6 - len(code6))
    return bytes(pkg)


def _build_7d2c_pull_pkg(seq_index: int, offset: int, chunk_size: int, panel_path: str) -> bytes:
    path300 = panel_path.encode("ascii")[:300]
    path300 += b"\x00" * (300 - len(path300))
    header = struct.pack(
        "<HHHHHHII",
        0x020C + seq_index * 0x0100,
        0x7D2C,
        0x0100,
        0x0136,
        0x0136,
        0x06B9,
        offset,
        chunk_size,
    )
    return header + path300


def _infer_market(code: str) -> int:
    if code.startswith(("92", "8", "4")):
        return TDXParams.MARKET_BJ
    if code.startswith(("6", "5", "9")):
        return TDXParams.MARKET_SH
    return TDXParams.MARKET_SZ


def _normalize_stocks(
    stocks: Optional[Sequence[Tuple[int, str]]],
    codes: Optional[Sequence[str]],
) -> List[Tuple[int, str]]:
    if stocks:
        return [(int(m), str(c)) for m, c in stocks]
    if codes:
        return [(_infer_market(code), str(code)) for code in codes]
    raise ValueError("stocks or codes is required")


def _rows_from_quote_payload(rows: Iterable[dict]) -> List[QuoteRow]:
    out = []
    for r in rows:
        out.append(
            QuoteRow(
                market=int(r.get("market", 0)),
                code=str(r.get("code", "")),
                price=float(r.get("price", 0)),
                open=float(r.get("open", 0)),
                high=float(r.get("high", 0)),
                low=float(r.get("low", 0)),
                vol=int(r.get("vol", 0)),
                cur_vol=int(r.get("cur_vol", 0)),
                active1=int(r.get("active1", 0)),
            )
        )
    return out


def get_market_quotes_snapshot_socket(
    host: str = "47.100.132.162",
    port: int = 7709,
    stocks: Optional[Sequence[Tuple[int, str]]] = None,
    codes: Optional[Sequence[str]] = None,
    market_hint: Optional[int] = None,
    timeout: float = 5.0,
) -> MarketQuotesSnapshot:
    """
    API-1 socket version (0x6320).

    Prefer `stocks=[(market, code), ...]`.
    If only `codes` are provided, market is inferred by code prefix.
    """
    try:
        query = _normalize_stocks(stocks, codes)
    except Exception as e:
        return MarketQuotesSnapshot(
            source_cmd=0x6320,
            packet=PacketMeta(0x6320, 0, 0, 0, None),
            rows=[],
            partial=True,
            errors=[str(e)],
        )

    try:
        api = TdxHq_API(raise_exception=True)
        with api.connect(ip=host, port=port, time_out=timeout):
            raw = api.get_security_quotes(query) or []
    except Exception as e:
        return MarketQuotesSnapshot(
            source_cmd=0x6320,
            packet=PacketMeta(0x6320, 0, 0, 0, None),
            rows=[],
            partial=True,
            errors=[f"socket query failed: {e}"],
        )

    rows = _rows_from_quote_payload(raw)
    if market_hint is not None:
        rows = [r for r in rows if r.market == market_hint]
    if codes:
        keep = set(str(c) for c in codes)
        rows = [r for r in rows if r.code in keep]

    return MarketQuotesSnapshot(
        source_cmd=0x6320,
        packet=PacketMeta(0x6320, 0, 0, 0, time.time()),
        rows=rows,
        partial=False,
        errors=[],
    )


def get_etf_panel_table_socket(
    host: str = "47.100.132.162",
    port: int = 7709,
    panel_path: str = DEFAULT_PANEL_PATH,
    warmup: Tuple[int, str] = DEFAULT_ETF_WARMUP,
    chunk_size: int = 30000,
    max_chunks: int = 12,
    focus_codes: Optional[Sequence[str]] = None,
    timeout: float = 5.0,
) -> EtfPanelTable:
    """
    API-2 socket version (7c2c + c920 + 7d2c chunks).
    """
    blob = bytearray()
    offsets: List[int] = []

    try:
        api = TdxHq_API(raise_exception=True)
        with api.connect(ip=host, port=port, time_out=timeout):
            api.send_raw_pkg(_build_7c2c_init_pkg(panel_path))
            if warmup:
                api.send_raw_pkg(_build_c920_warmup_pkg(int(warmup[0]), str(warmup[1])))

            for i in range(max_chunks):
                offset = i * chunk_size
                pkg = _build_7d2c_pull_pkg(i, offset, chunk_size, panel_path)
                rsp = api.send_raw_pkg(pkg)
                if len(rsp) < 4:
                    break
                got = struct.unpack("<I", rsp[:4])[0]
                if got <= 0:
                    break
                blob.extend(rsp[4:4 + got])
                offsets.append(offset)
                if got < chunk_size:
                    break
    except Exception as e:
        return EtfPanelTable(
            source_cmd=0x7D2C,
            columns=[],
            rows=[],
            packet_refs=[],
            incomplete=True,
            errors=[f"socket sequence failed: {e}"],
            focus_rows={},
        )

    start = blob.find(b"{")
    end = blob.rfind(b"}")
    if start < 0 or end <= start:
        return EtfPanelTable(
            source_cmd=0x7D2C,
            columns=[],
            rows=[],
            packet_refs=offsets,
            incomplete=True,
            errors=["cannot find JSON body in reassembled chunks"],
            focus_rows={},
        )

    try:
        obj = json.loads(blob[start:end + 1].decode("utf-8"))
    except Exception as e:
        return EtfPanelTable(
            source_cmd=0x7D2C,
            columns=[],
            rows=[],
            packet_refs=offsets,
            incomplete=True,
            errors=[f"json decode failed: {e}"],
            focus_rows={},
        )

    columns = obj.get("colheader", [])
    rows = obj.get("data", [])
    focus_rows: Dict[str, List[str]] = {}
    if focus_codes:
        for code in focus_codes:
            hit = next((r for r in rows if len(r) > 0 and str(r[0]) == str(code)), None)
            if hit:
                focus_rows[str(code)] = hit

    incomplete = (len(offsets) >= max_chunks and len(rows) > 0)
    errors = ["reached max_chunks before terminal short chunk"] if incomplete else []

    return EtfPanelTable(
        source_cmd=0x7D2C,
        columns=columns,
        rows=rows,
        packet_refs=offsets,
        incomplete=incomplete,
        errors=errors,
        focus_rows=focus_rows,
    )
