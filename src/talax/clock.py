"""Reading the date and time fields ExifTool returns."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone

from talax.model import Metadata

_STAMP = re.compile(
    r"^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})(\.\d+)?"
    r"(Z|[+-]\d{2}:\d{2})?$"
)


def parse(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    m = _STAMP.match(value.strip())
    if not m:
        return None
    y, mo, d, h, mi, s, frac, tz = m.groups()
    try:
        dt = datetime(int(y), int(mo), int(d), int(h), int(mi), int(s))
    except ValueError:
        return None
    if frac:
        dt += timedelta(seconds=float(frac))
    if tz == "Z":
        return dt.replace(tzinfo=UTC)
    if tz:
        return dt.replace(tzinfo=offset_from_text(tz))
    return dt


def local(tags: Metadata, key: str, subsec_key: str | None = None) -> datetime | None:
    dt = parse(tags.get(key))
    if dt is None:
        return None
    dt = dt.replace(tzinfo=None)
    subsec = tags.get(subsec_key) if subsec_key else None
    if isinstance(subsec, int | str) and str(subsec).isdigit():
        dt += timedelta(seconds=float(f"0.{subsec}"))
    return dt


def recorded_offset(
    tags: Metadata, vendor: datetime | None = None
) -> tuple[timezone | None, str | None]:
    """UTC offset recorded by the device, and where it was found."""
    if vendor is None:
        vendor = parse(tags.get("Samsung:TimeStamp"))
    raw = tags.get("ExifIFD:OffsetTimeOriginal")
    if isinstance(raw, str) and re.fullmatch(r"[+-]\d{2}:\d{2}", raw.strip()):
        return offset_from_text(raw.strip()), "the EXIF offset"
    if vendor is not None and isinstance(vendor.tzinfo, timezone):
        return vendor.tzinfo, "the manufacturer's clock"
    return None, None


def offset_from_text(text: str) -> timezone:
    sign = -1 if text[0] == "-" else 1
    hours, minutes = int(text[1:3]), int(text[4:6])
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def format_offset(tz: timezone | None) -> str | None:
    if tz is None:
        return None
    total = int(tz.utcoffset(None).total_seconds() // 60)
    sign = "-" if total < 0 else "+"
    return f"{sign}{abs(total) // 60:02d}:{abs(total) % 60:02d}"
