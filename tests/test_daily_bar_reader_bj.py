# coding: utf-8

import struct

from pytdx.reader.daily_bar_reader import TdxDailyBarReader


def test_daily_bar_reader_supports_bj_security_type_and_convert():
    reader = TdxDailyBarReader()
    fname = "/tmp/vipdoc/bj/lday/bj430001.day"

    security_type = reader.get_security_type(fname)
    assert security_type == "BJ_STOCK"

    coefficient = reader.SECURITY_COEFFICIENT[security_type]
    row = (20240102, 1234, 1250, 1200, 1220, 1000.0, 2000, 0)
    converted = reader._df_convert(row, coefficient)

    assert abs(converted[1] - 12.34) < 1e-8
    assert abs(converted[4] - 12.2) < 1e-8
    assert abs(converted[6] - 20.0) < 1e-8


def test_daily_bar_reader_can_read_bj_file_without_error(tmp_path):
    reader = TdxDailyBarReader()
    fname = tmp_path / "bj430001.day"
    data = struct.pack("<IIIIIfII", 20240102, 1234, 1250, 1200, 1220, 1000.0, 2000, 0)
    fname.write_bytes(data)

    df = reader.get_df(str(fname))
    assert len(df) == 1
    assert abs(float(df.iloc[0]["close"]) - 12.2) < 1e-8
