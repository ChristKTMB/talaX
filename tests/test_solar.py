import dataclasses
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from talax import Context, Declaration, Metadata, Observation, Sky, State
from talax.signals import SolarConsistency, TimeZoneConsistency
from talax.solar import compass, sun_position, zone_at

KINSHASA = (-4.39, 15.38)
WAT = timezone(timedelta(hours=1))


# --- engine -----------------------------------------------------------------


def test_sun_at_paris_on_the_summer_solstice_noon() -> None:
    # Theoretical maximum: 90 - 48.857 + 23.44 = 64.58 degrees, due south.
    sun = sun_position(
        48.8566, 2.3522, datetime(2026, 6, 21, 13, 50, tzinfo=ZoneInfo("Europe/Paris"))
    )
    assert sun.elevation == pytest.approx(64.58, abs=0.1)
    assert sun.azimuth == pytest.approx(180, abs=3)
    assert sun.shadow_direction == "N"


def test_sun_is_below_the_horizon_at_midnight() -> None:
    sun = sun_position(*KINSHASA, datetime(2026, 10, 31, 0, 0, tzinfo=WAT))
    assert sun.elevation < -30
    assert sun.phase == "night"
    assert sun.shadow_direction is None and sun.shadow_ratio is None


def test_naive_moment_is_refused() -> None:
    with pytest.raises(ValueError):
        sun_position(*KINSHASA, datetime(2026, 10, 31, 10, 0))


def test_zone_lookup() -> None:
    zone = zone_at(*KINSHASA)
    assert zone is not None and zone.key == "Africa/Kinshasa"
    assert zone_at(0.0, -30.0) is None  # Atlantic Ocean


@pytest.mark.parametrize(
    ("degrees", "name"),
    [(0, "N"), (44, "NE"), (180, "S"), (350, "N")],
)
def test_compass(degrees: float, name: str) -> None:
    assert compass(degrees) == name


# --- solar signal -----------------------------------------------------------


def manual(
    ctx: Context, when: datetime, sky: Sky | None, where: tuple[float, float] = KINSHASA
) -> Any:
    declared = dataclasses.replace(
        ctx,
        metadata=Metadata({}),
        declaration=Declaration(latitude=where[0], longitude=where[1], taken_at=when),
        observation=Observation(sky) if sky else None,
    )
    return SolarConsistency().evaluate(declared)


MORNING = datetime(2026, 10, 31, 10, 0, tzinfo=WAT)  # sun about 63 degrees up


def test_without_observation_describes_the_expected_scene(ctx: Context) -> None:
    result = manual(ctx, MORNING, None)
    assert result.state is State.UNVERIFIABLE
    assert "shadows should point" in result.explanation
    assert result.evidence["sun_elevation"] > 50


def test_matching_observation_is_consistent(ctx: Context) -> None:
    assert manual(ctx, MORNING, Sky.DAY).state is State.CONSISTENT


@pytest.mark.parametrize("sky", [Sky.NIGHT, Sky.TWILIGHT])
def test_impossible_observation_is_suspicious(ctx: Context, sky: Sky) -> None:
    result = manual(ctx, MORNING, sky)
    assert result.state is State.SUSPICIOUS
    assert "physically impossible" in result.explanation


def test_mismatch_explained_by_a_wrong_clock_is_to_check(ctx: Context) -> None:
    # Sun has just set in Kinshasa; "day" fits if the clock were 1 h ahead.
    evening = datetime(2026, 10, 31, 18, 45, tzinfo=WAT)
    result = manual(ctx, evening, Sky.DAY)
    assert result.state is State.TO_CHECK
    assert result.evidence["fitting_clock_shift_hours"] < 0


def test_twilight_is_tolerant_around_sunset(ctx: Context) -> None:
    sunset = datetime(2026, 10, 31, 17, 52, tzinfo=WAT)  # sun about -1 degree
    for sky in Sky:
        assert manual(ctx, sunset, sky).state is State.CONSISTENT


def test_naive_declared_time_uses_the_zone_of_the_place(ctx: Context) -> None:
    result = manual(ctx, datetime(2026, 10, 31, 10, 0), Sky.DAY)
    assert result.state is State.CONSISTENT
    assert "Africa/Kinshasa" in result.explanation


def test_missing_position_or_time_is_unverifiable(ctx: Context) -> None:
    only_time = dataclasses.replace(
        ctx, metadata=Metadata({"ExifIFD:DateTimeOriginal": "2026:10:31 10:00:00"})
    )
    assert SolarConsistency().evaluate(only_time).state is State.UNVERIFIABLE


def test_file_metadata_is_used_when_there_is_no_declaration(ctx: Context) -> None:
    tags = {
        "Composite:GPSLatitude": KINSHASA[0],
        "Composite:GPSLongitude": KINSHASA[1],
        "ExifIFD:DateTimeOriginal": "2026:10:31 10:00:00",
        "ExifIFD:OffsetTimeOriginal": "+01:00",
    }
    result = SolarConsistency().evaluate(
        dataclasses.replace(
            ctx, metadata=Metadata(tags), observation=Observation(Sky.NIGHT)
        )
    )
    assert result.state is State.SUSPICIOUS
    assert result.evidence["source"] == "file"


# --- time zone signal -------------------------------------------------------


def tz_result(ctx: Context, **tags: Any) -> Any:
    base = {
        "Composite:GPSLatitude": KINSHASA[0],
        "Composite:GPSLongitude": KINSHASA[1],
        "ExifIFD:DateTimeOriginal": "2026:10:31 10:00:00",
    }
    return TimeZoneConsistency().evaluate(
        dataclasses.replace(ctx, metadata=Metadata({**base, **tags}))
    )


def test_matching_time_zone(ctx: Context) -> None:
    assert (
        tz_result(ctx, **{"ExifIFD:OffsetTimeOriginal": "+01:00"}).state
        is State.CONSISTENT
    )


def test_offset_from_the_manufacturer_clock(ctx: Context) -> None:
    result = tz_result(ctx, **{"Samsung:TimeStamp": "2026:10:31 10:00:00.1+01:00"})
    assert result.state is State.CONSISTENT
    assert "manufacturer" in result.explanation


def test_mismatching_time_zone_is_to_check(ctx: Context) -> None:
    result = tz_result(ctx, **{"ExifIFD:OffsetTimeOriginal": "+03:00"})
    assert result.state is State.TO_CHECK
    assert "travelling" in result.explanation


def test_daylight_saving_is_taken_into_account(ctx: Context) -> None:
    paris = {"Composite:GPSLatitude": 48.8566, "Composite:GPSLongitude": 2.3522}
    summer = tz_result(
        ctx,
        **paris,
        **{
            "ExifIFD:DateTimeOriginal": "2026:07:01 12:00:00",
            "ExifIFD:OffsetTimeOriginal": "+02:00",
        },
    )
    winter = tz_result(
        ctx,
        **paris,
        **{
            "ExifIFD:DateTimeOriginal": "2026:01:15 12:00:00",
            "ExifIFD:OffsetTimeOriginal": "+01:00",
        },
    )
    assert summer.state is State.CONSISTENT and winter.state is State.CONSISTENT


def test_no_recorded_offset_reports_the_zone_used(ctx: Context) -> None:
    result = tz_result(ctx)
    assert result.state is State.UNVERIFIABLE
    assert "Africa/Kinshasa" in result.explanation


def test_no_position(ctx: Context) -> None:
    result = TimeZoneConsistency().evaluate(
        dataclasses.replace(ctx, metadata=Metadata({}))
    )
    assert result.state is State.UNVERIFIABLE


def test_device_ignoring_daylight_saving_is_named(ctx: Context) -> None:
    new_york = {"Composite:GPSLatitude": 40.75, "Composite:GPSLongitude": -73.99}
    result = tz_result(
        ctx,
        **new_york,
        **{
            "ExifIFD:DateTimeOriginal": "2022:10:25 11:27:32",
            "ExifIFD:OffsetTimeOriginal": "-05:00",
        },
    )
    assert result.state is State.TO_CHECK
    assert "daylight saving" in result.explanation
