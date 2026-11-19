import dataclasses
import io
import json
import shutil
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from talax import Conditions, Context, Declaration, Observation, State, analyze
from talax.i18n import Language
from talax.model import WeatherHour, WeatherRecord
from talax.signals import DEFAULT_SIGNALS, WeatherCheck, run_signals
from talax.weather import fetch_weather, parse_hours

NOON = datetime(2026, 6, 14, 12, 0, tzinfo=UTC)


def answer(rain: list[float], snow: list[float], cloud: list[float]) -> dict[str, Any]:
    """An Open-Meteo answer for 2026-06-14, hours 10:00 to 10+n (UTC)."""
    times = [f"2026-06-14T{10 + i:02d}:00" for i in range(len(rain))]
    return {
        "hourly": {
            "time": times,
            "precipitation": rain,
            "snowfall": snow,
            "cloud_cover": cloud,
        }
    }


class FakeOpen:
    """Stands in for urlopen: records the URL, answers or fails."""

    def __init__(self, body: object = None, error: Exception | None = None) -> None:
        self.body, self.error = body, error
        self.urls: list[str] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> io.BytesIO:
        self.urls.append(request.full_url)
        assert timeout <= 5
        if self.error:
            raise self.error
        return io.BytesIO(json.dumps(self.body).encode())


@pytest.fixture
def jpeg_path(tmp_path: Path) -> Path:
    if shutil.which("exiftool") is None:
        pytest.skip("ExifTool needed")
    path = tmp_path / "photo.jpg"
    Image.new("RGB", (32, 24), (90, 130, 170)).save(path)
    return path


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> FakeOpen:
    fake = FakeOpen(error=AssertionError("no network call expected"))
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return fake


def record(rain: float, snow: float = 0, cloud: float | None = 50) -> WeatherRecord:
    hours = tuple(
        WeatherHour(NOON + timedelta(hours=i), rain / 3, snow / 3, cloud)
        for i in range(3)
    )
    return WeatherRecord(hours=hours, latitude=-4.3, longitude=15.3)


def check(ctx: Context, weather: WeatherRecord, seen: Conditions | None) -> Any:
    return WeatherCheck().evaluate(
        dataclasses.replace(
            ctx,
            weather=weather,
            observation=Observation(conditions=seen) if seen else None,
        )
    )


# --- fetching ----------------------------------------------------------------


def test_sends_a_rounded_position_and_dates_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeOpen(answer([0, 0.4, 0, 0, 0], [0] * 5, [80] * 5))
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    result = fetch_weather(-4.32171, 15.31254, NOON)

    query = urllib.parse.parse_qs(urllib.parse.urlsplit(fake.urls[0]).query)
    assert query["latitude"] == ["-4.3"] and query["longitude"] == ["15.3"]
    assert query["start_date"] == ["2026-06-14"] and query["end_date"] == ["2026-06-14"]
    assert "12:00" not in fake.urls[0]  # never the time itself
    # Kept: the hour of the photo and one on each side (11:00 to 14:00).
    assert [h.time.hour for h in result.hours] == [11, 12, 13, 14]
    assert result.error is None


def test_an_aware_local_moment_is_read_in_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeOpen(answer([0] * 5, [0] * 5, [0] * 5))
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    kinshasa_1am = datetime(2026, 6, 14, 0, 30, tzinfo=timezone(timedelta(hours=1)))
    fetch_weather(-4.3, 15.3, kinshasa_1am)  # 23:30 UTC the day before
    assert "start_date=2026-06-13" in fake.urls[0]
    assert "end_date=2026-06-14" in fake.urls[0]


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (TimeoutError(), "unavailable"),
        (urllib.error.URLError("down"), "unavailable"),
        (urllib.error.HTTPError("u", 400, "out of range", None, None), "no_data"),  # type: ignore[arg-type]
        (urllib.error.HTTPError("u", 429, "too many", None, None), "unavailable"),  # type: ignore[arg-type]
    ],
)
def test_failures_never_raise(
    monkeypatch: pytest.MonkeyPatch, error: Exception, code: str
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", FakeOpen(error=error))
    assert fetch_weather(0.5, 0.5, NOON).error == code


@pytest.mark.parametrize("body", [{}, {"hourly": {"time": ["x"]}}, [], "nonsense"])
def test_odd_answers_give_no_hours(body: object) -> None:
    assert parse_hours(body) == []


def test_null_values_are_no_data(monkeypatch: pytest.MonkeyPatch) -> None:
    body = answer([None] * 5, [None] * 5, [None] * 5)  # type: ignore[list-item]
    monkeypatch.setattr(urllib.request, "urlopen", FakeOpen(body))
    assert fetch_weather(0.5, 0.5, NOON).error == "no_data"


# --- analysis ------------------------------------------------------------------


def test_the_library_never_calls_the_network_unless_asked(
    jpeg_path: Path, no_network: FakeOpen
) -> None:
    analysis = analyze(
        jpeg_path, declaration=Declaration(-4.32, 15.31, datetime(2026, 6, 14, 10, 0))
    )
    assert no_network.urls == []
    assert "weather" not in {r.signal_id for r in analysis.results}


def test_asked_without_place_or_time_calls_nothing(
    jpeg_path: Path, no_network: FakeOpen
) -> None:
    analysis = analyze(jpeg_path, weather=True)
    weather = next(r for r in analysis.results if r.signal_id == "weather")
    assert weather.state is State.UNVERIFIABLE
    assert weather.message.key == "weather.missing_input"
    assert no_network.urls == []


def test_asked_with_a_declaration(
    jpeg_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        urllib.request, "urlopen", FakeOpen(answer([0] * 5, [0] * 5, [5] * 5))
    )
    analysis = analyze(
        jpeg_path,
        declaration=Declaration(-4.32, 15.31, datetime(2026, 6, 14, 12, 0)),
        observation=Observation(conditions=Conditions.RAIN),
        weather=True,
    )
    weather = next(r for r in analysis.results if r.signal_id == "weather")
    assert weather.state is State.TO_CHECK


# --- the check -------------------------------------------------------------------


def test_no_lookup_no_check(ctx: Context) -> None:
    assert "weather" not in {r.signal_id for r in run_signals(ctx, DEFAULT_SIGNALS)}


def test_without_observation_describes_the_model(ctx: Context) -> None:
    result = check(ctx, record(rain=2.4, cloud=95), None)
    assert result.state is State.UNVERIFIABLE
    assert "2.4 mm of precipitation" in result.explanation
    assert "95 % covered" in result.explanation
    assert "2,4 mm de précipitations" in result.explain(Language.FR)


@pytest.mark.parametrize(
    ("seen", "rain", "snow", "cloud", "state"),
    [
        (Conditions.RAIN, 2.0, 0, 90, State.CONSISTENT),
        (Conditions.RAIN, 0.0, 0, 90, State.TO_CHECK),
        (Conditions.SNOW, 1.0, 3.0, 100, State.CONSISTENT),
        (Conditions.SNOW, 1.0, 0.0, 100, State.TO_CHECK),
        (Conditions.OVERCAST, 0.0, 0, 60, State.CONSISTENT),
        (Conditions.OVERCAST, 0.0, 0, 5, State.TO_CHECK),
        (Conditions.CLEAR, 0.0, 0, 20, State.CONSISTENT),
        (Conditions.CLEAR, 0.0, 0, 95, State.TO_CHECK),
        (Conditions.CLEAR, 3.0, 0, 50, State.TO_CHECK),
    ],
)
def test_never_more_than_to_check(
    ctx: Context, seen: Conditions, rain: float, snow: float, cloud: float, state: State
) -> None:
    result = check(ctx, record(rain, snow, cloud), seen)
    assert result.state is state
    assert result.evidence["observed_conditions"] == str(seen)


def test_the_lack_of_rain_is_explained_without_accusing(ctx: Context) -> None:
    result = check(ctx, record(rain=0.0), Conditions.RAIN)
    assert "local shower" in result.explanation
    assert "other sources" in result.explanation


@pytest.mark.parametrize("error", ["missing_input", "unavailable", "no_data"])
def test_failures_are_unverifiable(ctx: Context, error: str) -> None:
    result = check(ctx, WeatherRecord(error=error), Conditions.RAIN)
    assert result.state is State.UNVERIFIABLE
    assert result.message.key == f"weather.{error}"


def test_unknown_cloud_cover_is_said(ctx: Context) -> None:
    result = check(ctx, record(rain=0.0, cloud=None), Conditions.OVERCAST)
    assert result.state is State.CONSISTENT
    assert "cloud cover unknown" in result.explanation
