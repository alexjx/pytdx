# coding: utf-8

from pytdx.hq import _select_market_code


def test_select_market_code_supports_bj_prefix():
    assert _select_market_code("920088") == 2
    assert _select_market_code("830001") == 2
    assert _select_market_code("430001") == 2


def test_select_market_code_keeps_existing_rules():
    assert _select_market_code("000001") == 0
    assert _select_market_code("600000") == 1
    assert _select_market_code("900901") == 1

