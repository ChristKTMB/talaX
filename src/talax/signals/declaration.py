"""Does the file agree with the place and time the caption claims?

Runs only when the user typed in a declaration: without one there is no claim
to compare, and the check is not a missing datum but a question nobody asked.

A GPS position does not drift like a clock, so a far-off position can be
suspicious. A date gap is never more than "to check": wrongly set clocks are
common (section 9 of the project rules).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, tzinfo

from talax.clock import local, recorded_offset
from talax.i18n import Message
from talax.model import Context, Declaration, Result, State
from talax.phrases import duration
from talax.solar import zone_at

# Covers a position by cell tower and a click on a town on the map.
_SAME_PLACE_KM = 25.0
# Beyond this, an old cached position is no longer an ordinary explanation.
_FAR_KM = 100.0
# The tolerance of the solar check for a wrong clock or time zone.
_SAME_TIME = timedelta(hours=3)
_EARTH_RADIUS_KM = 6371.0

_ORDER = [State.CONSISTENT, State.UNVERIFIABLE, State.TO_CHECK, State.SUSPICIOUS]


class DeclarationCheck:
    id = "declaration"
    name = "Declared place and time"

    def is_relevant(self, ctx: Context) -> bool:
        return ctx.declaration is not None

    def evaluate(self, ctx: Context) -> Result:
        declared = ctx.declaration
        assert declared is not None
        evidence: dict[str, object] = {
            "declared_latitude": declared.latitude,
            "declared_longitude": declared.longitude,
            "declared_time": declared.taken_at.isoformat(),
        }
        place_state, place = _compare_place(ctx, declared, evidence)
        time_state, when = _compare_time(ctx, declared, evidence)

        if place_state is State.UNVERIFIABLE and time_state is State.UNVERIFIABLE:
            return Result(
                self.id, State.UNVERIFIABLE, Message("declaration.nothing"), evidence
            )
        compared = [s for s in (place_state, time_state) if s is not State.UNVERIFIABLE]
        state = max(compared, key=_ORDER.index)
        return Result(
            self.id,
            state,
            Message("declaration.summary", {"place": place, "time": when}),
            evidence,
        )


def _compare_place(
    ctx: Context, declared: Declaration, evidence: dict[str, object]
) -> tuple[State, Message]:
    position = _file_position(ctx)
    if position is None:
        return State.UNVERIFIABLE, Message("declaration.place.none")
    km = distance_km(declared.latitude, declared.longitude, *position)
    evidence["file_latitude"], evidence["file_longitude"] = position
    evidence["distance_km"] = round(km, 1)
    if km <= _SAME_PLACE_KM:
        return State.CONSISTENT, Message("declaration.place.close", {"km": km})
    if km <= _FAR_KM:
        return State.TO_CHECK, Message("declaration.place.near", {"km": km})
    return State.SUSPICIOUS, Message("declaration.place.far", {"km": km})


def _compare_time(
    ctx: Context, declared: Declaration, evidence: dict[str, object]
) -> tuple[State, Message]:
    tags = ctx.metadata
    recorded = local(tags, "ExifIFD:DateTimeOriginal", "ExifIFD:SubSecTimeOriginal")
    declared_zone = zone_at(declared.latitude, declared.longitude)
    claimed = _aware(declared.taken_at, declared_zone)
    if recorded is None or claimed is None:
        return State.UNVERIFIABLE, Message("declaration.time.none")

    offset, _ = recorded_offset(tags)
    position = _file_position(ctx)
    zone = offset or (zone_at(*position) if position else None) or declared_zone
    if zone is None:
        return State.UNVERIFIABLE, Message("declaration.time.none")
    in_file = recorded.replace(tzinfo=zone)
    gap = in_file - claimed
    evidence["file_time"] = in_file.isoformat()
    evidence["time_gap_hours"] = round(gap.total_seconds() / 3600, 2)

    if abs(gap) <= _SAME_TIME:
        return State.CONSISTENT, Message(
            "declaration.time.close", {"gap": duration(gap)}
        )
    direction = "before" if gap < timedelta(0) else "after"
    return State.TO_CHECK, Message(
        f"declaration.time.{direction}",
        {"when": recorded.strftime("%Y-%m-%d %H:%M"), "gap": duration(gap)},
    )


def _aware(moment: datetime, zone: tzinfo | None) -> datetime | None:
    if moment.tzinfo is not None:
        return moment
    return moment.replace(tzinfo=zone) if zone is not None else None


def _file_position(ctx: Context) -> tuple[float, float] | None:
    """The file's GPS position, when the GPS check would call it consistent."""
    lat = ctx.metadata.get("Composite:GPSLatitude")
    lon = ctx.metadata.get("Composite:GPSLongitude")
    if not _is_number(lat) or not _is_number(lon):
        return None
    assert isinstance(lat, int | float) and isinstance(lon, int | float)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None
    return float(lat), float(lon)


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (haversine): well under 1 % off at these scales."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
