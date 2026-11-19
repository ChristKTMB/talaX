"""The weather around the place and time of a photo, from Open-Meteo.

The only network call of the library, made only when asked for
(`analyze(..., weather=True)`). It sends a position rounded to 0.1 degree
(about 11 km, finer than the model's cells) and two dates: never the file,
never the exact time. Open-Meteo may keep these in its logs for 90 days; the
user is told before opting in.

Data: Open-Meteo.com, CC BY 4.0, from ECMWF IFS and ERA5 (Copernicus).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

from talax.model import WeatherHour, WeatherRecord

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT_SECONDS = 5.0
# Hours kept around the moment: the hour it falls in, and one on each side.
WINDOW = timedelta(hours=1)
_VARIABLES = "precipitation,snowfall,cloud_cover"


def fetch_weather(latitude: float, longitude: float, moment: datetime) -> WeatherRecord:
    """Hourly weather around `moment` (aware). Never raises."""
    from talax import __version__

    lat, lon = round(latitude, 1), round(longitude, 1)
    utc = moment.astimezone(UTC)
    first, last = utc - WINDOW, utc + 2 * WINDOW
    query = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": first.date().isoformat(),
            "end_date": last.date().isoformat(),
            "hourly": _VARIABLES,
            "timezone": "GMT",
        }
    )
    request = urllib.request.Request(
        f"{ARCHIVE_URL}?{query}",
        headers={
            "User-Agent": f"talax/{__version__} (+https://github.com/ChristKTMB/talaX)"
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        # Open-Meteo refuses dates it has no data for (future, too recent) with 400.
        error = "no_data" if exc.code == 400 else "unavailable"
        return WeatherRecord(latitude=lat, longitude=lon, error=error)
    except (OSError, ValueError):
        return WeatherRecord(latitude=lat, longitude=lon, error="unavailable")
    hours = tuple(h for h in parse_hours(data) if first <= h.time <= last)
    if not any(h.precipitation_mm is not None for h in hours):
        return WeatherRecord(latitude=lat, longitude=lon, error="no_data")
    return WeatherRecord(hours=hours, latitude=lat, longitude=lon)


def parse_hours(data: object) -> list[WeatherHour]:
    """The hourly series of an Open-Meteo answer; nothing if it looks wrong."""
    try:
        assert isinstance(data, dict)
        hourly = data["hourly"]
        series = zip(
            hourly["time"],
            hourly["precipitation"],
            hourly["snowfall"],
            hourly["cloud_cover"],
            strict=True,
        )
        return [
            WeatherHour(
                time=datetime.fromisoformat(time).replace(tzinfo=UTC),
                precipitation_mm=_number(rain),
                snowfall_cm=_number(snow),
                cloud_cover_pct=_number(cloud),
            )
            for time, rain, snow, cloud in series
        ]
    except (AssertionError, KeyError, TypeError, ValueError):
        return []


def _number(value: object) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None
