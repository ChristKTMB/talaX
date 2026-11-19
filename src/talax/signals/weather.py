"""Does the weather in the photo match the weather model at that place and time?

Present only when the user asked for the lookup. The engine reads the model,
the human says what the photo shows. Never more than "to check": the model's
cells are 9 to 25 km wide and a tropical shower a few km, so "rain in the photo,
none in the model" happens on genuine photos (project decision B, step 7).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta

from talax.i18n import Message
from talax.model import Conditions, Context, Result, State, WeatherHour

_DRY_MM = 0.1  # Below this, the model records no precipitation.
_WET_MM = 1.0  # From this, a clear sky is hard to square with the model.
_CLEAR_PCT = 10.0
_COVERED_PCT = 90.0


class WeatherCheck:
    id = "weather"
    name = "Weather"

    def is_relevant(self, ctx: Context) -> bool:
        return ctx.weather is not None

    def evaluate(self, ctx: Context) -> Result:
        record = ctx.weather
        assert record is not None
        if record.error or not record.hours:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message(f"weather.{record.error or 'no_data'}"),
                {"error": record.error or "no_data"},
            )

        hours = record.hours
        rain = _total(h.precipitation_mm for h in hours)
        snow = _total(h.snowfall_cm for h in hours)
        clouds = [h.cloud_cover_pct for h in hours if h.cloud_cover_pct is not None]
        cloud = sum(clouds) / len(clouds) if clouds else None
        evidence: dict[str, object] = {
            "source": "open-meteo",
            "latitude_sent": record.latitude,
            "longitude_sent": record.longitude,
            "from_utc": (hours[0].time - timedelta(hours=1)).isoformat(),
            "to_utc": hours[-1].time.isoformat(),
            "precipitation_mm": round(rain, 1),
            "snowfall_cm": round(snow, 1),
            "cloud_cover_pct": round(cloud) if cloud is not None else None,
        }
        summary = _summary(hours, rain, snow, cloud, record.latitude, record.longitude)

        seen = ctx.observation.conditions if ctx.observation else None
        if seen is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("weather.no_observation", {"summary": summary}),
                evidence,
            )
        evidence["observed_conditions"] = str(seen)
        reason = _disagreement(seen, rain, snow, cloud)
        seen_text = Message(f"conditions.{seen}")
        if reason is None:
            return Result(
                self.id,
                State.CONSISTENT,
                Message("weather.consistent", {"summary": summary, "seen": seen_text}),
                evidence,
            )
        return Result(
            self.id,
            State.TO_CHECK,
            Message(
                "weather.to_check",
                {"summary": summary, "seen": seen_text, "reason": Message(reason)},
            ),
            evidence,
        )


def _disagreement(
    seen: Conditions, rain: float, snow: float, cloud: float | None
) -> str | None:
    """The message key of what contradicts the observation, or None."""
    if seen is Conditions.RAIN and rain < _DRY_MM:
        return "weather.reason.no_rain"
    if seen is Conditions.SNOW and snow <= 0:
        return "weather.reason.no_snow"
    dry_and_clear = rain < _DRY_MM and cloud is not None and cloud <= _CLEAR_PCT
    if seen is Conditions.OVERCAST and dry_and_clear:
        return "weather.reason.clear_sky"
    if seen is Conditions.CLEAR:
        if rain >= _WET_MM:
            return "weather.reason.raining"
        if cloud is not None and cloud >= _COVERED_PCT:
            return "weather.reason.covered"
    return None


def _summary(
    hours: tuple[WeatherHour, ...],
    rain: float,
    snow: float,
    cloud: float | None,
    latitude: float | None,
    longitude: float | None,
) -> Message:
    start = hours[0].time - timedelta(hours=1)
    params = {
        "start": start.strftime("%Y-%m-%d %H:%M"),
        "end": hours[-1].time.strftime("%H:%M"),
        "lat": f"{latitude:.1f}",
        "lon": f"{longitude:.1f}",
        "rain": rain,
        "snow": snow,
    }
    if cloud is None:
        return Message("weather.summary_no_cloud", params)
    return Message("weather.summary", {**params, "cloud": cloud})


def _total(values: Iterable[float | None]) -> float:
    return sum(v for v in values if v is not None)
