# coding: utf-8

import struct

from pytdx.parser.get_security_list import GetSecurityList


def test_parse_security_list_tolerates_invalid_gbk_name_bytes():
    parser = GetSecurityList(client=None)
    # invalid leading gbk byte sequence in 8-byte name field
    name_bytes = b"\xbbABC\x00\x00\x00\x00"
    one = struct.pack("<6sH8s4sBI4s", b"920088", 100, name_bytes, b"\x00" * 4, 2, 0, b"\x00" * 4)
    body = struct.pack("<H", 1) + one

    rows = parser.parseResponse(body)

    assert len(rows) == 1
    assert rows[0]["code"] == "920088"
