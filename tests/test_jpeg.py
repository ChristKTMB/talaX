import struct

import pytest

from talax.jpeg import JpegError, parse_jpeg_structure


def segment(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


def dqt(table_id: int, values: list[int], precision: int = 0) -> bytes:
    fmt = ">64B" if precision == 0 else ">64H"
    return bytes([(precision << 4) | table_id]) + struct.pack(fmt, *values)


SOI = b"\xff\xd8"
SOF0 = segment(0xC0, b"\x08\x00\x10\x00\x10\x01\x01\x11\x00")
SOF2 = segment(0xC2, b"\x08\x00\x10\x00\x10\x01\x01\x11\x00")
SOS = segment(0xDA, b"\x01\x01\x00\x00\x3f\x00") + b"\x12\x34 image data \xff\x00"


def test_reads_segments_and_tables() -> None:
    data = (
        SOI
        + segment(0xE1, b"Exif\x00\x00II*\x00")
        + segment(0xE1, b"http://ns.adobe.com/xap/1.0/\x00<x/>")
        + segment(0xE8, b"\x01\x02binary")
        + segment(0xDB, dqt(0, list(range(64))) + dqt(1, [2] * 64))
        + SOF0
        + SOS
    )
    jpeg = parse_jpeg_structure(data)

    assert jpeg.segments == (
        "SOI",
        "APP1:Exif",
        "APP1:XMP",
        "APP8",
        "DQT",
        "SOF0",
        "SOS",
    )
    assert [t.table_id for t in jpeg.quant_tables] == [0, 1]
    assert jpeg.quant_tables[0].values == tuple(range(64))
    assert jpeg.quant_tables[1].values == (2,) * 64
    assert jpeg.progressive is False


def test_progressive_and_16_bit_tables() -> None:
    data = SOI + segment(0xDB, dqt(0, [300] * 64, precision=1)) + SOF2 + SOS
    jpeg = parse_jpeg_structure(data)
    assert jpeg.progressive is True
    assert jpeg.quant_tables[0].precision == 1
    assert jpeg.quant_tables[0].values == (300,) * 64


def test_fill_bytes_before_a_marker_are_accepted() -> None:
    data = SOI + b"\xff\xff" + SOF0 + SOS
    assert parse_jpeg_structure(data).segments == ("SOI", "SOF0", "SOS")


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\x89PNG\r\n\x1a\n",
        SOI,
        SOI + b"\xff\xd9",
        SOI + b"\x00\x00",
        SOI + b"\xff\xdb\x00\xff" + b"\x00" * 10,  # length beyond the data
        SOI + segment(0xDB, b"\x00" + b"\x01" * 10),  # truncated table
        SOI + segment(0xDB, b"\x20" + b"\x01" * 64),  # invalid precision
    ],
)
def test_malformed_files_raise_jpeg_error(data: bytes) -> None:
    with pytest.raises(JpegError):
        parse_jpeg_structure(data)
