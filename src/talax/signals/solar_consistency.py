"""Was the sun where the photo says it was? The signature signal of Tala X.

The engine computes, the human observes: Tala X never decides from the pixels
whether a photo shows day or night. The user says what the photo shows; the
verdict comes from confronting that with the computed sun.
"""

from __future__ import annotations

from datetime import timedelta

from talax.i18n import Message
from talax.model import Context, Result, Sky, State
from talax.phrases import compass as compass_name
from talax.phrases import hours, offset_source
from talax.solar import PlaceAndTime, SunPosition, compass, place_and_time, sun_position

# Sun elevations (degrees) compatible with what the user reports. Deliberately
# wide: a false "suspicious" on a real photo is worse than a missed one.
_COMPATIBLE = {
    Sky.DAY: lambda e: e > -3,
    Sky.TWILIGHT: lambda e: -15 < e < 15,
    Sky.NIGHT: lambda e: e < 3,
}
# A wrong clock or time zone of up to this much can explain a mismatch.
_CLOCK_ERROR = timedelta(hours=3)
_STEP = timedelta(minutes=30)


class SolarConsistency:
    id = "solar"
    name = "Solar consistency"

    def is_relevant(self, ctx: Context) -> bool:
        return True

    def evaluate(self, ctx: Context) -> Result:
        pt = place_and_time(ctx)
        if pt is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("solar.missing_input"),
            )

        sun = sun_position(pt.latitude, pt.longitude, pt.moment)
        evidence = _evidence(pt, sun)
        description = _describe(pt, sun)
        observation = ctx.observation

        if observation is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("solar.no_observation", {"description": description}),
                evidence,
            )

        seen = observation.sky
        evidence["observed_sky"] = str(seen)
        seen_text = Message(f"sky.{seen}")
        if _COMPATIBLE[seen](sun.elevation):
            return Result(
                self.id,
                State.CONSISTENT,
                Message(
                    "solar.consistent", {"description": description, "seen": seen_text}
                ),
                evidence,
            )

        shift = _smallest_fitting_shift(pt, seen)
        if shift is not None:
            evidence["fitting_clock_shift_hours"] = shift.total_seconds() / 3600
            return Result(
                self.id,
                State.TO_CHECK,
                Message(
                    "solar.clock_shift",
                    {
                        "description": description,
                        "seen": seen_text,
                        "shift": hours(shift),
                    },
                ),
                evidence,
            )
        return Result(
            self.id,
            State.SUSPICIOUS,
            Message(
                "solar.impossible",
                {
                    "description": description,
                    "seen": seen_text,
                    "max": hours(_CLOCK_ERROR),
                },
            ),
            evidence,
        )


def _smallest_fitting_shift(pt: PlaceAndTime, seen: Sky) -> timedelta | None:
    steps = int(_CLOCK_ERROR / _STEP)
    for n in range(1, steps + 1):
        for sign in (1, -1):
            shift = sign * n * _STEP
            sun = sun_position(pt.latitude, pt.longitude, pt.moment + shift)
            if _COMPATIBLE[seen](sun.elevation):
                return shift
    return None


def _describe(pt: PlaceAndTime, sun: SunPosition) -> Message:
    params = {
        "origin": Message(f"solar.origin.{pt.source}"),
        "when": pt.moment.strftime("%Y-%m-%d %H:%M"),
        "source": offset_source(pt.offset_source, pt.zone),
        "elevation": abs(sun.elevation),
        "side": Message("solar.above" if sun.elevation >= 0 else "solar.below"),
        "direction": compass_name(compass(sun.azimuth)),
        "azimuth": sun.azimuth,
        "phase": Message(f"sun.phase.{sun.phase}"),
    }
    if sun.shadow_direction and sun.shadow_ratio is not None:
        return Message(
            "solar.description_with_shadows",
            {
                **params,
                "shadow_direction": compass_name(sun.shadow_direction),
                "shadow_ratio": sun.shadow_ratio,
            },
        )
    return Message("solar.description", params)


def _evidence(pt: PlaceAndTime, sun: SunPosition) -> dict[str, object]:
    return {
        "latitude": pt.latitude,
        "longitude": pt.longitude,
        "moment": pt.moment.isoformat(),
        "source": pt.source,
        "offset_source": pt.offset_source,
        "zone": pt.zone,
        "sun_elevation": round(sun.elevation, 2),
        "sun_azimuth": round(sun.azimuth, 2),
        "shadow_direction": sun.shadow_direction,
        "shadow_ratio": round(sun.shadow_ratio, 2) if sun.shadow_ratio else None,
    }
