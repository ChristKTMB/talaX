"""When the photo was taken, and whether the device's clocks agree.

A camera writes the capture time in several places at the same moment. When
they disagree, either a clock was wrong or a date was changed afterwards.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone

from talax.model import Context, Metadata, Result, State

# Same-device clocks written at the same instant; measured gap in the corpus
# is under 2 s (Samsung TimeStamp vs DateTimeOriginal).
_SAME_INSTANT = timedelta(seconds=10)
# Re-saving tolerance for CreateDate / ModifyDate.
_RESAVE = timedelta(seconds=60)
# A GPS fix can be older than the photo (cached position).
_GPS_TOLERANCE = timedelta(minutes=5)

_STAMP = re.compile(
    r"^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})(\.\d+)?"
    r"(Z|[+-]\d{2}:\d{2})?$"
)


class CaptureTime:
    id = "capture_time"
    name = "Date and time"

    def is_relevant(self, ctx: Context) -> bool:
        return True

    def evaluate(self, ctx: Context) -> Result:
        tags = ctx.metadata
        original = _local(
            tags, "ExifIFD:DateTimeOriginal", "ExifIFD:SubSecTimeOriginal"
        )
        if original is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                "No capture time is recorded, or it is unreadable: the "
                "metadata was removed or never written.",
                {"date_time_original": tags.get("ExifIFD:DateTimeOriginal")},
            )

        vendor = _parse(tags.get("Samsung:TimeStamp"))
        offset, offset_source = _offset(tags, vendor)
        evidence: dict[str, object] = {
            "date_time_original": original.isoformat(),
            "offset": _fmt_offset(offset),
            "offset_source": offset_source,
            "create_date": _iso(_local(tags, "ExifIFD:CreateDate")),
            "modify_date": _iso(_local(tags, "IFD0:ModifyDate")),
            "vendor_clock": _iso(vendor),
            "gps_utc": _iso(_parse(tags.get("Composite:GPSDateTime"))),
        }
        when = original.strftime("%Y-%m-%d %H:%M:%S")
        if offset is not None:
            when += f" (UTC{_fmt_offset(offset)}, from {offset_source})"
        else:
            when += " local time (time zone not recorded)"

        if vendor is not None:
            gap = abs(original - vendor.replace(tzinfo=None))
            if gap > _SAME_INSTANT:
                return Result(
                    self.id,
                    State.SUSPICIOUS,
                    f"The capture time says {when}, but the manufacturer's own "
                    f"clock, written at the same instant, says "
                    f"{vendor.strftime('%Y-%m-%d %H:%M:%S')} ({_human(gap)} "
                    "apart). The device writes both together, so one of them "
                    "was most likely changed after the photo was taken.",
                    evidence,
                )

        notes: list[str] = []
        for tag, label in (
            ("ExifIFD:CreateDate", "creation"),
            ("IFD0:ModifyDate", "modification"),
        ):
            other = _local(tags, tag)
            if other is not None and abs(other - original) > _RESAVE:
                notes.append(
                    f"the {label} time ({other.strftime('%Y-%m-%d %H:%M:%S')}) "
                    f"is {_human(abs(other - original))} away from the capture "
                    "time, so the file was probably saved again later"
                )

        gps = _parse(tags.get("Composite:GPSDateTime"))
        if gps is not None:
            if offset is not None:
                gap = abs(original.replace(tzinfo=offset) - gps)
                if gap > _GPS_TOLERANCE:
                    notes.append(
                        f"the GPS clock is {_human(gap)} away from the capture "
                        "time; the device clock may have been wrong, or the "
                        "position fix was old"
                    )
            else:
                implied = original - gps.replace(tzinfo=None)
                if not _plausible_offset(implied):
                    notes.append(
                        "the capture time and the GPS clock do not differ by a "
                        "whole time zone; the device clock may have been wrong"
                    )

        if notes:
            return Result(
                self.id,
                State.TO_CHECK,
                f"Captured {when}, but " + "; ".join(notes) + ".",
                evidence,
            )
        checked = sum(
            v is not None
            for v in (evidence["create_date"], evidence["modify_date"], vendor, gps)
        )
        agree = (
            f" The {checked + 1} clocks recorded in the file agree."
            if checked
            else " No other clock is recorded to compare with."
        )
        return Result(self.id, State.CONSISTENT, f"Captured {when}.{agree}", evidence)


def _parse(value: object) -> datetime | None:
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
        return dt.replace(tzinfo=_tz(tz))
    return dt


def _local(tags: Metadata, key: str, subsec_key: str | None = None) -> datetime | None:
    dt = _parse(tags.get(key))
    if dt is None:
        return None
    dt = dt.replace(tzinfo=None)
    subsec = tags.get(subsec_key) if subsec_key else None
    if isinstance(subsec, int | str) and str(subsec).isdigit():
        dt += timedelta(seconds=float(f"0.{subsec}"))
    return dt


def _offset(
    tags: Metadata, vendor: datetime | None
) -> tuple[timezone | None, str | None]:
    raw = tags.get("ExifIFD:OffsetTimeOriginal")
    if isinstance(raw, str) and re.fullmatch(r"[+-]\d{2}:\d{2}", raw.strip()):
        return _tz(raw.strip()), "the EXIF offset"
    if vendor is not None and isinstance(vendor.tzinfo, timezone):
        return vendor.tzinfo, "the manufacturer's clock"
    return None, None


def _tz(text: str) -> timezone:
    sign = -1 if text[0] == "-" else 1
    hours, minutes = int(text[1:3]), int(text[4:6])
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def _plausible_offset(delta: timedelta) -> bool:
    minutes = delta.total_seconds() / 60
    if not -12 * 60 - 5 <= minutes <= 14 * 60 + 5:
        return False
    nearest = round(minutes / 15) * 15
    return abs(minutes - nearest) * 60 <= _GPS_TOLERANCE.total_seconds()


def _fmt_offset(tz: timezone | None) -> str | None:
    if tz is None:
        return None
    total = int(tz.utcoffset(None).total_seconds() // 60)
    sign = "-" if total < 0 else "+"
    return f"{sign}{abs(total) // 60:02d}:{abs(total) % 60:02d}"


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _human(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    if seconds < 120:
        return f"{seconds} s"
    if seconds < 7200:
        return f"{seconds // 60} min"
    if seconds < 2 * 86400:
        return f"{seconds // 3600} h"
    return f"{seconds // 86400} days"
