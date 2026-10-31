"""Reads the internal structure of a JPEG file, up to the image data.

ExifTool does not expose everything the integrity test needs. The quantisation
tables are the encoder's signature: they tell a camera's encoder from a
platform's re-encoder. The order of segments is another trace of who wrote
the file.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

# Markers without a length field.
_STANDALONE = {0x01, *range(0xD0, 0xD8)}
_SOF_PROGRESSIVE = {0xC2, 0xC6, 0xCA, 0xCE}
_SOF = {*range(0xC0, 0xD0)} - {0xC4, 0xC8, 0xCC}

_MARKER_NAMES = {
    0xC4: "DHT",
    0xCC: "DAC",
    0xDA: "SOS",
    0xDB: "DQT",
    0xDD: "DRI",
    0xFE: "COM",
}


_APP_LABELS = {
    "http://ns.adobe.com/xap/1.0/": "XMP",
    "http://ns.adobe.com/xmp/extension/": "XMP-extension",
}


class JpegError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QuantTable:
    table_id: int
    precision: int
    """0 for 8-bit values, 1 for 16-bit values."""
    values: tuple[int, ...]
    """64 coefficients in the zigzag order stored in the file."""


@dataclass(frozen=True, slots=True)
class JpegStructure:
    segments: tuple[str, ...]
    """Segment names in file order, e.g. `APP1:Exif`, `DQT`, `SOF0`."""
    quant_tables: tuple[QuantTable, ...]
    progressive: bool


def read_jpeg_structure(path: Path) -> JpegStructure:
    with path.open("rb") as f:
        return parse_jpeg_structure(f.read())


def parse_jpeg_structure(data: bytes) -> JpegStructure:
    if not data.startswith(b"\xff\xd8"):
        raise JpegError("not a JPEG file (missing SOI marker)")

    segments: list[str] = ["SOI"]
    tables: list[QuantTable] = []
    progressive = False
    pos = 2

    while True:
        marker, pos = _next_marker(data, pos)
        if marker in _STANDALONE:
            segments.append(f"RST{marker - 0xD0}" if marker >= 0xD0 else "TEM")
            continue
        if marker == 0xD9:
            raise JpegError("end of image reached before any image data")
        if pos + 2 > len(data):
            raise JpegError("truncated segment length")
        (length,) = struct.unpack(">H", data[pos : pos + 2])
        if length < 2 or pos + length > len(data):
            raise JpegError(f"invalid segment length {length} at offset {pos}")
        payload = data[pos + 2 : pos + length]
        pos += length

        segments.append(_segment_name(marker, payload))
        if marker == 0xDB:
            tables.extend(_parse_dqt(payload))
        elif marker in _SOF_PROGRESSIVE:
            progressive = True
        elif marker == 0xDA:
            # Entropy-coded image data follows; nothing more we need.
            break

    return JpegStructure(tuple(segments), tuple(tables), progressive)


def _next_marker(data: bytes, pos: int) -> tuple[int, int]:
    if pos >= len(data) or data[pos] != 0xFF:
        raise JpegError(f"expected a marker at offset {pos}")
    while pos < len(data) and data[pos] == 0xFF:  # fill bytes are allowed
        pos += 1
    if pos >= len(data):
        raise JpegError("truncated marker")
    return data[pos], pos + 1


def _segment_name(marker: int, payload: bytes) -> str:
    if 0xE0 <= marker <= 0xEF:
        # APPn segments carry an identifier string: Exif, JFIF, ICC_PROFILE...
        ident = payload[:40].split(b"\x00", 1)[0]
        printable = ident and all(0x20 < b < 0x7F for b in ident)
        label = ident.decode("ascii") if printable else ""
        label = _APP_LABELS.get(label, label)
        name = f"APP{marker - 0xE0}"
        return f"{name}:{label}" if label else name
    if marker in _SOF:
        return f"SOF{marker - 0xC0}"
    return _MARKER_NAMES.get(marker, f"0x{marker:02X}")


def _parse_dqt(payload: bytes) -> list[QuantTable]:
    tables = []
    pos = 0
    while pos < len(payload):
        precision, table_id = payload[pos] >> 4, payload[pos] & 0x0F
        pos += 1
        if precision not in (0, 1):
            raise JpegError(f"invalid quantisation table precision {precision}")
        size = 64 * (precision + 1)
        raw = payload[pos : pos + size]
        if len(raw) != size:
            raise JpegError("truncated quantisation table")
        fmt = ">64B" if precision == 0 else ">64H"
        tables.append(QuantTable(table_id, precision, struct.unpack(fmt, raw)))
        pos += size
    return tables
