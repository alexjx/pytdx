from pytdx.parser.get_security_quotes import GetSecurityQuotesCmd


def test_format_time_handles_zero_timestamp():
    cmd = object.__new__(GetSecurityQuotesCmd)
    assert cmd._format_time("0") == "0:00:00.000"


def test_placeholder_quote_payload_is_detected():
    cmd = object.__new__(GetSecurityQuotesCmd)
    row = {
        "code": "600839",
        "active1": 0,
        "active2": 0,
        "price": 0.0,
        "last_close": 0.0,
        "open": 0.0,
        "high": 0.0,
        "low": 0.0,
        "vol": 0,
        "cur_vol": 0,
        "amount": 0.0,
        "s_vol": 0,
        "b_vol": 0,
    }
    assert cmd._is_placeholder_quote_payload(row) is True


def test_non_placeholder_quote_payload_not_detected():
    cmd = object.__new__(GetSecurityQuotesCmd)
    row = {
        "code": "000001",
        "active1": 3500,
        "active2": 3500,
        "price": 10.9,
        "last_close": 10.96,
        "open": 10.92,
        "high": 10.97,
        "low": 10.88,
        "vol": 500000,
        "cur_vol": 300,
        "amount": 546000000.0,
        "s_vol": 260000,
        "b_vol": 240000,
    }
    assert cmd._is_placeholder_quote_payload(row) is False


def test_placeholder_quote_payload_with_tiny_amount_is_detected():
    cmd = object.__new__(GetSecurityQuotesCmd)
    row = {
        "code": "600839",
        "active1": 0,
        "active2": 0,
        "price": 0.0,
        "last_close": 0.0,
        "open": 0.0,
        "high": 0.0,
        "low": 0.0,
        "vol": 0,
        "cur_vol": 0,
        "amount": 5.877471754111438e-39,
        "s_vol": 0,
        "b_vol": 0,
    }
    assert cmd._is_placeholder_quote_payload(row) is True
