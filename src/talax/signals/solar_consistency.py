"""Was the sun where the photo says it was? The signature signal of Tala X.

The engine computes, the human observes: Tala X never decides from the pixels
whether a photo shows day or night. The user says what the photo shows; the
verdict comes from confronting that with the computed sun.
"""

from __future__ import annotations

from datetime import timedelta

from talax.model import Context, Result, Sky, State
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
                "The position and the time of the photo are both needed to "
                "compute where the sun was, and at least one is missing. For a "
                "file without metadata, enter the claimed place and time by "
                "hand.",
            )

        sun = sun_position(pt.latitude, pt.longitude, pt.moment)
        evidence = _evidence(pt, sun)
        description = _describe(pt, sun)
        observation = ctx.observation

        if observation is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                f"{description} Compare this with the photo: say whether it "
                "shows day, twilight or night, and Tala X will check that it "
                "is physically possible.",
                evidence,
            )

        seen = observation.sky
        evidence["observed_sky"] = str(seen)
        if _COMPATIBLE[seen](sun.elevation):
            return Result(
                self.id,
                State.CONSISTENT,
                f"{description} The photo shows {seen}, which matches.",
                evidence,
            )

        shift = _smallest_fitting_shift(pt, seen)
        if shift is not None:
            evidence["fitting_clock_shift_hours"] = shift.total_seconds() / 3600
            return Result(
                self.id,
                State.TO_CHECK,
                f"{description} The photo shows {seen}, which does not match. "
                f"It would match if the clock or the time zone were off by "
                f"{_hours(shift)}, which happens (a phone set to the wrong time "
                "zone while travelling). Otherwise the time or the place is "
                "false.",
                evidence,
            )
        return Result(
            self.id,
            State.SUSPICIOUS,
            f"{description} The photo shows {seen}: this is physically "
            "impossible at that place and time, and no clock error of up to "
            f"{_hours(_CLOCK_ERROR)} explains it. The recorded or claimed time, "
            "or the place, is false.",
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


def _describe(pt: PlaceAndTime, sun: SunPosition) -> str:
    when = pt.moment.strftime("%Y-%m-%d %H:%M")
    origin = "recorded in the file" if pt.source == "file" else "declared"
    text = (
        f"At the place and time {origin} ({when}, time zone from "
        f"{pt.offset_source}), the sun was {abs(sun.elevation):.0f}° "
        f"{'above' if sun.elevation >= 0 else 'below'} the horizon, toward the "
        f"{compass(sun.azimuth)} ({sun.azimuth:.0f}°): {sun.phase}."
    )
    if sun.shadow_direction and sun.shadow_ratio is not None:
        text += (
            f" Outdoor shadows should point {sun.shadow_direction}, about "
            f"{sun.shadow_ratio:.1f} times as long as the object is tall."
        )
    return text


def _evidence(pt: PlaceAndTime, sun: SunPosition) -> dict[str, object]:
    return {
        "latitude": pt.latitude,
        "longitude": pt.longitude,
        "moment": pt.moment.isoformat(),
        "source": pt.source,
        "offset_source": pt.offset_source,
        "sun_elevation": round(sun.elevation, 2),
        "sun_azimuth": round(sun.azimuth, 2),
        "shadow_direction": sun.shadow_direction,
        "shadow_ratio": round(sun.shadow_ratio, 2) if sun.shadow_ratio else None,
    }


def _hours(delta: timedelta) -> str:
    hours = abs(delta.total_seconds()) / 3600
    return f"{hours:g} hour" + ("" if hours == 1 else "s")
