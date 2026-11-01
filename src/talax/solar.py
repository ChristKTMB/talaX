"""Solar engine: where the sun was, for a place and a moment.

Written once for both branches: the inputs come either from the file's
metadata or from a place and time typed in by the user (manual mode).
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from zoneinfo import ZoneInfo

from astral import Observer, sun
from timezonefinder import TimezoneFinder

from talax.clock import local, recorded_offset
from talax.model import Context

_COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


@dataclass(frozen=True, slots=True)
class SunPosition:
    elevation: float
    """Degrees above (positive) or below (negative) the horizon."""
    azimuth: float
    """Degrees clockwise from north."""

    @property
    def phase(self) -> str:
        """Code of the light phase: day, low, civil, dusk or night."""
        e = self.elevation
        if e >= 6:
            return "day"
        if e >= 0:
            return "low"
        if e >= -6:
            return "civil"
        if e >= -12:
            return "dusk"
        return "night"

    @property
    def shadow_direction(self) -> str | None:
        """Compass code (N, NE, ...) the shadows point to."""
        if self.elevation <= 0:
            return None
        return compass((self.azimuth + 180) % 360)

    @property
    def shadow_ratio(self) -> float | None:
        """Shadow length divided by the height of the object casting it."""
        if self.elevation <= 0.5:
            return None
        return 1 / math.tan(math.radians(self.elevation))


@dataclass(frozen=True, slots=True)
class PlaceAndTime:
    latitude: float
    longitude: float
    moment: datetime
    """Timezone-aware."""
    source: str
    """`file` or `declaration`."""
    offset_source: str
    """`exif`, `vendor`, `declaration` or `zone` (legal time zone of the place)."""
    zone: str | None = None
    """Time zone name when the offset comes from the place."""


def sun_position(latitude: float, longitude: float, moment: datetime) -> SunPosition:
    if moment.tzinfo is None:
        raise ValueError("moment must be timezone-aware")
    observer = Observer(latitude=latitude, longitude=longitude)
    return SunPosition(
        elevation=sun.elevation(observer, moment),
        azimuth=sun.azimuth(observer, moment),
    )


@functools.cache
def _finder() -> TimezoneFinder:
    return TimezoneFinder()


def zone_at(latitude: float, longitude: float) -> ZoneInfo | None:
    """Legal time zone at a position, None at sea or if unknown."""
    name = _finder().timezone_at(lat=latitude, lng=longitude)
    if name is None or name.startswith("Etc/"):
        return None
    return ZoneInfo(name)


def compass(degrees: float) -> str:
    return _COMPASS[round(degrees / 45) % 8]


def place_and_time(ctx: Context) -> PlaceAndTime | None:
    """Position and aware capture moment, from the declaration or the file.

    A declaration wins: in manual mode the user checks a claimed place and
    time. Returns None when the position or the time is missing.
    """
    d = ctx.declaration
    if d is not None:
        if d.taken_at.tzinfo is not None:
            return PlaceAndTime(
                d.latitude, d.longitude, d.taken_at, "declaration", "declaration"
            )
        zone = zone_at(d.latitude, d.longitude)
        if zone is None:
            return None
        return PlaceAndTime(
            d.latitude,
            d.longitude,
            d.taken_at.replace(tzinfo=zone),
            "declaration",
            "zone",
            zone.key,
        )

    tags = ctx.metadata
    lat, lon = tags.get("Composite:GPSLatitude"), tags.get("Composite:GPSLongitude")
    when = local(tags, "ExifIFD:DateTimeOriginal", "ExifIFD:SubSecTimeOriginal")
    if not _is_number(lat) or not _is_number(lon) or when is None:
        return None
    assert isinstance(lat, int | float) and isinstance(lon, int | float)
    offset, offset_source = recorded_offset(tags)
    if offset is not None:
        return PlaceAndTime(
            lat, lon, when.replace(tzinfo=offset), "file", str(offset_source)
        )
    zone = zone_at(lat, lon)
    if zone is None:
        return None
    return PlaceAndTime(lat, lon, when.replace(tzinfo=zone), "file", "zone", zone.key)


def utc_offset(zone: tzinfo, naive_local: datetime) -> timezone:
    """Fixed UTC offset of a zone at a given local time (daylight saving aware)."""
    offset = naive_local.replace(tzinfo=zone).utcoffset()
    assert offset is not None
    return timezone(offset)


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
