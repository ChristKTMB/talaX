"""Does the time zone the device recorded match the place it recorded?"""

from __future__ import annotations

from talax.clock import format_offset, local, recorded_offset
from talax.model import Context, Result, State
from talax.solar import utc_offset, zone_at


class TimeZoneConsistency:
    id = "time_zone"
    name = "Time zone"

    def is_relevant(self, ctx: Context) -> bool:
        return True

    def evaluate(self, ctx: Context) -> Result:
        tags = ctx.metadata
        lat, lon = tags.get("Composite:GPSLatitude"), tags.get("Composite:GPSLongitude")
        when = local(tags, "ExifIFD:DateTimeOriginal")
        if not isinstance(lat, int | float) or not isinstance(lon, int | float):
            return Result(
                self.id,
                State.UNVERIFIABLE,
                "No GPS position is recorded, so the time zone of the place "
                "cannot be compared with the one the device used.",
            )
        if when is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                "No capture time is recorded, so the time zone cannot be checked.",
            )
        zone = zone_at(lat, lon)
        if zone is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                "The GPS position is not inside a known time zone (at sea, or "
                "invalid), so the device's time zone cannot be checked.",
            )
        expected = format_offset(utc_offset(zone, when))
        recorded, source = recorded_offset(tags)
        evidence: dict[str, object] = {
            "zone": zone.key,
            "zone_offset": expected,
            "recorded_offset": format_offset(recorded),
            "recorded_offset_source": source,
        }
        if recorded is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                f"The device recorded no time zone. The GPS position is in "
                f"{zone.key} (UTC{expected} on that date), which Tala X uses to "
                "place the photo in time.",
                evidence,
            )
        if format_offset(recorded) == expected:
            return Result(
                self.id,
                State.CONSISTENT,
                f"The device's time zone (UTC{expected}, from {source}) matches "
                f"the GPS position, in {zone.key}.",
                evidence,
            )
        dst = zone.dst(when.replace(tzinfo=zone))
        recorded_delta = recorded.utcoffset(None)
        if dst and recorded_delta == utc_offset(zone, when).utcoffset(None) - dst:
            return Result(
                self.id,
                State.TO_CHECK,
                f"The device recorded UTC{format_offset(recorded)} (from "
                f"{source}), but {zone.key} was on daylight saving time, "
                f"UTC{expected}, on that date. The device clock ignored daylight "
                "saving time, which is common on cameras; the times in the file "
                "are then one hour off.",
                evidence,
            )
        return Result(
            self.id,
            State.TO_CHECK,
            f"The device recorded UTC{format_offset(recorded)} (from {source}), "
            f"but the GPS position is in {zone.key}, which was UTC{expected} on "
            "that date. A phone set to a fixed time zone while travelling does "
            "this; so does an edited time or position.",
            evidence,
        )
