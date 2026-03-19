#!/usr/bin/env python3
# coding: utf-8

import argparse

if __package__ is None or __package__ == "":  # pragma: no cover
    import os
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from market_api_experimental import export_etf_panel_table_csv
from market_api_socket_experimental import (
    get_etf_panel_table_socket,
    get_market_quotes_snapshot_socket,
)


def _parse_stocks(text):
    out = []
    if not text:
        return out
    for item in text.split(","):
        part = item.strip()
        if not part:
            continue
        market, code = part.split(":", 1)
        out.append((int(market), code.strip()))
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Live socket experiments for 0x6320 and 0x7d2c."
    )
    parser.add_argument("--host", default="47.100.132.162")
    parser.add_argument("--port", type=int, default=7709)
    parser.add_argument("--timeout", type=float, default=5.0)

    sub = parser.add_subparsers(dest="mode", required=True)

    q = sub.add_parser("quotes", help="query quotes via 0x6320")
    q.add_argument("--stocks", help="market:code list, e.g. 2:920088,1:513350")
    q.add_argument("--codes", help="code list, market auto inferred")
    q.add_argument("--market-hint", type=int, default=None)

    e = sub.add_parser("etf", help="query ETF panel via 7c2c+c920+7d2c")
    e.add_argument("--panel-path", default="bi_diy/list/gxjty_etfjj101.jsn")
    e.add_argument("--warmup-market", type=int, default=0)
    e.add_argument("--warmup-code", default="159919")
    e.add_argument("--focus-codes", default="513350,159518,515220")
    e.add_argument("--chunk-size", type=int, default=30000)
    e.add_argument("--max-chunks", type=int, default=12)
    e.add_argument("--export-csv", default=None)

    args = parser.parse_args()
    if args.mode == "quotes":
        stocks = _parse_stocks(args.stocks)
        codes = [x.strip() for x in (args.codes or "").split(",") if x.strip()]
        snap = get_market_quotes_snapshot_socket(
            host=args.host,
            port=args.port,
            stocks=stocks or None,
            codes=codes or None,
            market_hint=args.market_hint,
            timeout=args.timeout,
        )
        print("errors:", snap.errors)
        print("rows:", len(snap.rows))
        for r in snap.rows[:20]:
            print(r)
        return

    focus = [x.strip() for x in (args.focus_codes or "").split(",") if x.strip()]
    table = get_etf_panel_table_socket(
        host=args.host,
        port=args.port,
        panel_path=args.panel_path,
        warmup=(args.warmup_market, args.warmup_code),
        chunk_size=args.chunk_size,
        max_chunks=args.max_chunks,
        focus_codes=focus or None,
        timeout=args.timeout,
    )
    print("errors:", table.errors)
    print("incomplete:", table.incomplete)
    print("rows:", len(table.rows), "cols:", len(table.columns))
    print("offsets:", table.packet_refs)
    print("focus:", table.focus_rows)
    if args.export_csv:
        export_etf_panel_table_csv(table, args.export_csv)
        print("exported:", args.export_csv)


if __name__ == "__main__":
    main()
