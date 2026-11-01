"""Small translatable pieces shared by several signals."""

from __future__ import annotations

from datetime import timedelta

from talax.i18n import Message


def duration(delta: timedelta) -> Message:
    seconds = int(abs(delta.total_seconds()))
    if seconds < 120:
        return Message("duration.seconds", {"n": seconds})
    if seconds < 7200:
        return Message("duration.minutes", {"n": seconds // 60})
    if seconds < 2 * 86400:
        return Message("duration.hours", {"n": seconds // 3600})
    return Message("duration.days", {"n": seconds // 86400})


def hours(delta: timedelta) -> Message:
    """Exact hours, for clock shifts (0.5, 1, 1.5...)."""
    return Message("duration.hours", {"n": abs(delta.total_seconds()) / 3600})


def offset_source(code: str | None, zone: str | None = None) -> Message:
    """Where a UTC offset came from: exif, vendor, declaration or zone."""
    if code == "zone":
        return Message("offset_source.zone", {"zone": zone or "?"})
    return Message(f"offset_source.{code}")


def compass(code: str) -> Message:
    return Message(f"compass.{code}")
