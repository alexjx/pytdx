# coding: utf-8

import json
import struct

from pytdx.hq import TdxHq_API


def test_get_market_quotes_snapshot_filter(monkeypatch):
    api = TdxHq_API()

    def fake_quotes(_stocks):
        return [
            {"market": 2, "code": "920088", "price": 75.59},
            {"market": 1, "code": "513350", "price": 1.317},
            {"market": 0, "code": "000001", "price": 12.34},
        ]

    monkeypatch.setattr(api, "get_security_quotes", fake_quotes)
    rows = api.get_market_quotes_snapshot(
        code_list=["920088", "513350"],
        market_hint=2,
    )
    assert len(rows) == 1
    assert rows[0]["code"] == "920088"
    assert rows[0]["market"] == 2


def test_get_etf_panel_table_reassemble(monkeypatch):
    api = TdxHq_API()

    table_obj = {
        "colheader": ["$ZQDM", "$SC", "DWJZ"],
        "data": [
            ["513350", "1", "1.2176"],
            ["159518", "0", "1.1608"],
        ],
    }
    blob = json.dumps(table_obj, ensure_ascii=False).encode("utf-8")
    chunk_size = 16
    chunks = [blob[i:i + chunk_size] for i in range(0, len(blob), chunk_size)]

    calls = {"n": 0}

    def fake_send_raw_pkg(_pkg):
        calls["n"] += 1
        if calls["n"] == 1:
            return b"token"
        if calls["n"] == 2:
            return b"ok"
        idx = calls["n"] - 3
        if idx >= len(chunks):
            return struct.pack("<I", 0)
        c = chunks[idx]
        return struct.pack("<I", len(c)) + c

    monkeypatch.setattr(api, "send_raw_pkg", fake_send_raw_pkg)
    res = api.get_etf_panel_table(
        panel_path="bi_diy/list/gxjty_etfjj101.jsn",
        chunk_size=chunk_size,
        max_chunks=32,
        focus_codes=["513350"],
    )

    assert res["errors"] == []
    assert res["incomplete"] is False
    assert res["columns"] == ["$ZQDM", "$SC", "DWJZ"]
    assert len(res["rows"]) == 2
    assert res["focus_rows"]["513350"][2] == "1.2176"
    assert len(res["offsets"]) == len(chunks)


def test_get_etf_panel_table_invalid_blob(monkeypatch):
    api = TdxHq_API()

    calls = {"n": 0}

    def fake_send_raw_pkg(_pkg):
        calls["n"] += 1
        if calls["n"] <= 2:
            return b"x"
        return struct.pack("<I", 4) + b"abcd"

    monkeypatch.setattr(api, "send_raw_pkg", fake_send_raw_pkg)
    res = api.get_etf_panel_table(chunk_size=4, max_chunks=1)

    assert res["incomplete"] is True
    assert "cannot find JSON body" in res["errors"][0]

