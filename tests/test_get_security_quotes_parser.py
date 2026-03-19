from pytdx.parser.get_security_quotes import GetSecurityQuotesCmd


def test_format_time_handles_zero_timestamp():
    cmd = object.__new__(GetSecurityQuotesCmd)
    assert cmd._format_time("0") == "0:00:00.000"

