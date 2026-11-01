"""Does the time zone the device recorded match the place it recorded?"""

from __future__ import annotations

from talax.clock import format_offset, local, recorded_offset
from talax.i18n import Message
from talax.model import Context, Result, State
from talax.phrases import offset_source
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
                Message("time_zone.no_position"),
            )
        if when is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("time_zone.no_time"),
            )
        zone = zone_at(lat, lon)
        if zone is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("time_zone.no_zone"),
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
                Message(
                    "time_zone.not_recorded", {"zone": zone.key, "expected": expected}
                ),
                evidence,
            )
        if format_offset(recorded) == expected:
            return Result(
                self.id,
                State.CONSISTENT,
                Message(
                    "time_zone.consistent",
                    {
                        "zone": zone.key,
                        "expected": expected,
                        "source": offset_source(source),
                    },
                ),
                evidence,
            )
        dst = zone.dst(when.replace(tzinfo=zone))
        recorded_delta = recorded.utcoffset(None)
        if dst and recorded_delta == utc_offset(zone, when).utcoffset(None) - dst:
            return Result(
                self.id,
                State.TO_CHECK,
                Message(
                    "time_zone.ignored_dst",
                    {
                        "recorded": format_offset(recorded),
                        "source": offset_source(source),
                        "zone": zone.key,
                        "expected": expected,
                    },
                ),
                evidence,
            )
        return Result(
            self.id,
            State.TO_CHECK,
            Message(
                "time_zone.mismatch",
                {
                    "recorded": format_offset(recorded),
                    "source": offset_source(source),
                    "zone": zone.key,
                    "expected": expected,
                },
            ),
            evidence,
        )
