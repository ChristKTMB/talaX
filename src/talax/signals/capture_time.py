"""When the photo was taken, and whether the device's clocks agree.

A camera writes the capture time in several places at the same moment. When
they disagree, either a clock was wrong or a date was changed afterwards.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from talax.clock import format_offset, local, parse, recorded_offset
from talax.i18n import Message
from talax.model import Context, Result, State
from talax.phrases import duration, offset_source

# Same-device clocks written at the same instant; measured gap in the corpus
# is under 2 s (Samsung TimeStamp vs DateTimeOriginal).
_SAME_INSTANT = timedelta(seconds=10)
# Re-saving tolerance for CreateDate / ModifyDate.
_RESAVE = timedelta(seconds=60)
# A GPS fix can be older than the photo (cached position).
_GPS_TOLERANCE = timedelta(minutes=5)

_FMT = "%Y-%m-%d %H:%M:%S"


class CaptureTime:
    id = "capture_time"
    name = "Date and time"

    def is_relevant(self, ctx: Context) -> bool:
        return True

    def evaluate(self, ctx: Context) -> Result:
        tags = ctx.metadata
        original = local(tags, "ExifIFD:DateTimeOriginal", "ExifIFD:SubSecTimeOriginal")
        if original is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("capture_time.absent"),
                {"date_time_original": tags.get("ExifIFD:DateTimeOriginal")},
            )

        vendor = parse(tags.get("Samsung:TimeStamp"))
        offset, offset_source = recorded_offset(tags, vendor)
        evidence: dict[str, object] = {
            "date_time_original": original.isoformat(),
            "offset": format_offset(offset),
            "offset_source": offset_source,
            "create_date": _iso(local(tags, "ExifIFD:CreateDate")),
            "modify_date": _iso(local(tags, "IFD0:ModifyDate")),
            "vendor_clock": _iso(vendor),
            "gps_utc": _iso(parse(tags.get("Composite:GPSDateTime"))),
        }
        when = _when(original, offset, offset_source)

        if vendor is not None:
            gap = abs(original - vendor.replace(tzinfo=None))
            if gap > _SAME_INSTANT:
                return Result(
                    self.id,
                    State.SUSPICIOUS,
                    Message(
                        "capture_time.vendor_mismatch",
                        {
                            "when": when,
                            "vendor": vendor.strftime(_FMT),
                            "gap": duration(gap),
                        },
                    ),
                    evidence,
                )

        notes: list[Message] = []
        for tag, key in (
            ("ExifIFD:CreateDate", "capture_time.note.created_later"),
            ("IFD0:ModifyDate", "capture_time.note.modified_later"),
        ):
            other = local(tags, tag)
            if other is not None and abs(other - original) > _RESAVE:
                notes.append(
                    Message(
                        key,
                        {
                            "time": other.strftime(_FMT),
                            "gap": duration(other - original),
                        },
                    )
                )

        gps = parse(tags.get("Composite:GPSDateTime"))
        if gps is not None:
            if offset is not None:
                gap = abs(original.replace(tzinfo=offset) - gps)
                if gap > _GPS_TOLERANCE:
                    notes.append(
                        Message("capture_time.note.gps_gap", {"gap": duration(gap)})
                    )
            else:
                implied = original - gps.replace(tzinfo=None)
                if not _plausible_offset(implied):
                    notes.append(Message("capture_time.note.gps_not_whole_zone"))

        if notes:
            return Result(
                self.id,
                State.TO_CHECK,
                Message("capture_time.to_check", {"when": when, "notes": notes}),
                evidence,
            )
        checked = sum(
            v is not None
            for v in (evidence["create_date"], evidence["modify_date"], vendor, gps)
        )
        if checked:
            message = Message(
                "capture_time.clocks_agree", {"when": when, "count": checked + 1}
            )
        else:
            message = Message("capture_time.single_clock", {"when": when})
        return Result(self.id, State.CONSISTENT, message, evidence)


def _when(original: datetime, offset: object, source: str | None) -> Message:
    if offset is None:
        return Message("capture_time.when_local", {"time": original.strftime(_FMT)})
    return Message(
        "capture_time.when_offset",
        {
            "time": original.strftime(_FMT),
            "offset": format_offset(offset),  # type: ignore[arg-type]
            "source": offset_source(source),
        },
    )


def _plausible_offset(delta: timedelta) -> bool:
    minutes = delta.total_seconds() / 60
    if not -12 * 60 - 5 <= minutes <= 14 * 60 + 5:
        return False
    nearest = round(minutes / 15) * 15
    return abs(minutes - nearest) * 60 <= _GPS_TOLERANCE.total_seconds()


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None
