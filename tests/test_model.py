import dataclasses
from datetime import UTC, datetime

import pytest

from talax import (
    Analysis,
    Context,
    Declaration,
    Metadata,
    Result,
    State,
)
from talax.i18n import Message
from tests.conftest import OK


def test_result_requires_a_message() -> None:
    with pytest.raises(TypeError, match="no message"):
        Result("gps", State.CONSISTENT, "plain text")  # type: ignore[arg-type]


def test_unknown_message_key_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown message key"):
        Message("gps.does_not_exist")


def test_message_missing_a_value_is_refused() -> None:
    with pytest.raises(ValueError, match="lacks"):
        Message("real_format.consistent")


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_result_confidence_must_be_a_probability(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        Result("gps", State.CONSISTENT, OK, confidence=confidence)


def test_deterministic_result_has_no_confidence() -> None:
    assert Result("gps", State.CONSISTENT, OK).confidence is None


def test_entities_are_immutable(ctx: Context) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.file.size = 0  # type: ignore[misc]


def test_mappings_are_read_only_and_copied() -> None:
    source = {"EXIF:Make": "Apple"}
    metadata = Metadata(source)
    source["EXIF:Make"] = "Forged"

    assert metadata.get("EXIF:Make") == "Apple"
    with pytest.raises(TypeError):
        metadata.tags["EXIF:Make"] = "Forged"  # type: ignore[index]

    result = Result("gps", State.CONSISTENT, OK, evidence={"lat": 1.0})
    with pytest.raises(TypeError):
        result.evidence["lat"] = 2.0  # type: ignore[index]


def test_explanations_exist_in_both_languages(ctx: Context) -> None:
    from talax.i18n import Language

    assert "JPEG" in Result("gps", State.CONSISTENT, OK).explain(Language.FR)
    assert ctx.integrity.explain(Language.FR) != ctx.integrity.explanation


@pytest.mark.parametrize(("lat", "lon"), [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_declaration_rejects_impossible_coordinates(lat: float, lon: float) -> None:
    with pytest.raises(ValueError):
        Declaration(latitude=lat, longitude=lon, taken_at=datetime(2026, 1, 1))


def test_analysis_timestamp_must_be_timezone_aware(ctx: Context) -> None:
    with pytest.raises(ValueError, match="timezone"):
        Analysis(ctx.file, ctx.integrity, results=(), created_at=datetime.now())

    Analysis(ctx.file, ctx.integrity, results=(), created_at=datetime.now(UTC))


def test_public_api() -> None:
    import talax

    assert callable(talax.analyze)
    assert talax.__version__.count(".") == 2
    assert set(talax.__all__) >= {"analyze", "Analysis", "State", "Observation"}
