import dataclasses
from datetime import datetime, timedelta, timezone

import pytest

from talax import Context, Declaration, Metadata, Result, State
from talax.geo import distance_km
from talax.i18n import Language
from talax.signals import DEFAULT_SIGNALS, DeclarationCheck, run_signals

# Synthetic places, never taken from the corpus.
KINSHASA = (-4.3217, 15.3125)
GOMA = (-1.6792, 29.2228)
MATADI = (-5.8167, 13.4500)  # about 240 km from Kinshasa
KINSHASA_EDGE = (-4.40, 15.50)  # about 23 km from the centre
KASANGULU = (-4.59, 15.17)  # about 34 km


def check(
    ctx: Context,
    tags: dict[str, object],
    where: tuple[float, float] = KINSHASA,
    when: datetime = datetime(2026, 6, 14, 10, 0),
) -> Result:
    declared = dataclasses.replace(
        ctx,
        metadata=Metadata(tags),
        declaration=Declaration(latitude=where[0], longitude=where[1], taken_at=when),
    )
    return DeclarationCheck().evaluate(declared)


def gps(place: tuple[float, float]) -> dict[str, object]:
    return {"Composite:GPSLatitude": place[0], "Composite:GPSLongitude": place[1]}


def taken(stamp: str) -> dict[str, object]:
    return {"ExifIFD:DateTimeOriginal": stamp}


def test_distance() -> None:
    assert distance_km(*KINSHASA, *GOMA) == pytest.approx(1555, rel=0.02)
    assert distance_km(*KINSHASA, *KINSHASA) == 0


def test_no_declaration_no_check(ctx: Context) -> None:
    assert "declaration" not in {r.signal_id for r in run_signals(ctx, DEFAULT_SIGNALS)}


def test_nothing_in_the_file_to_compare(ctx: Context) -> None:
    result = check(ctx, {})
    assert result.state is State.UNVERIFIABLE
    assert "solar check uses the declaration" in result.explanation


@pytest.mark.parametrize(
    ("place", "state"),
    [
        (KINSHASA_EDGE, State.CONSISTENT),
        (KASANGULU, State.TO_CHECK),
        (MATADI, State.SUSPICIOUS),
        (GOMA, State.SUSPICIOUS),
    ],
)
def test_position_gap(ctx: Context, place: tuple[float, float], state: State) -> None:
    result = check(ctx, gps(place))
    assert result.state is state
    assert "no capture time" in result.explanation


def test_a_masked_or_null_position_is_not_compared(ctx: Context) -> None:
    assert check(ctx, gps((0.0, 0.0))).state is State.UNVERIFIABLE


def test_close_time_is_consistent(ctx: Context) -> None:
    result = check(ctx, taken("2026:06:14 12:30:00"))
    assert result.state is State.CONSISTENT
    assert result.evidence["time_gap_hours"] == 2.5


def test_an_old_photo_is_to_check_never_suspicious(ctx: Context) -> None:
    result = check(ctx, taken("2019:03:12 08:00:00"))
    assert result.state is State.TO_CHECK
    assert "2019-03-12 08:00" in result.explanation
    assert "about 7 years before" in result.explanation
    fr = result.explain(Language.FR)
    assert "environ 7 ans avant" in fr


def test_file_time_is_read_in_its_own_offset(ctx: Context) -> None:
    # 10:00 at UTC+1 in Kinshasa is 06:00 at UTC-3: four hours apart, not zero.
    result = check(
        ctx, {**taken("2026:06:14 10:00:00"), "ExifIFD:OffsetTimeOriginal": "-03:00"}
    )
    assert result.evidence["time_gap_hours"] == 4.0
    assert result.state is State.TO_CHECK


def test_the_worst_comparison_wins(ctx: Context) -> None:
    result = check(ctx, {**gps(GOMA), **taken("2026:06:14 10:05:00")})
    assert result.state is State.SUSPICIOUS
    assert "km from the position" in result.explanation
    assert "5 min away" in result.explanation


def test_an_aware_declared_time_is_kept(ctx: Context) -> None:
    utc = datetime(2026, 6, 14, 9, 0, tzinfo=timezone(timedelta(0)))
    result = check(ctx, taken("2026:06:14 10:00:00"), when=utc)
    assert result.state is State.CONSISTENT
    assert result.evidence["time_gap_hours"] == 0
