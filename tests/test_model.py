import dataclasses
from datetime import UTC, datetime

import pytest

from talax import (
    Analysis,
    Context,
    Declaration,
    IntegrityAssessment,
    IntegrityVerdict,
    Metadata,
    Result,
    State,
)


def test_result_requires_an_explanation() -> None:
    with pytest.raises(ValueError, match="no explanation"):
        Result(signal_id="gps", state=State.CONSISTENT, explanation="  ")


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_result_confidence_must_be_a_probability(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        Result("gps", State.CONSISTENT, "ok", confidence=confidence)


def test_deterministic_result_has_no_confidence() -> None:
    assert Result("gps", State.CONSISTENT, "ok").confidence is None


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

    result = Result("gps", State.CONSISTENT, "ok", evidence={"lat": 1.0})
    with pytest.raises(TypeError):
        result.evidence["lat"] = 2.0  # type: ignore[index]


def test_integrity_assessment_requires_an_explanation() -> None:
    with pytest.raises(ValueError):
        IntegrityAssessment(IntegrityVerdict.UNDETERMINED, explanation="")


@pytest.mark.parametrize(("lat", "lon"), [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_declaration_rejects_impossible_coordinates(lat: float, lon: float) -> None:
    with pytest.raises(ValueError):
        Declaration(latitude=lat, longitude=lon, taken_at=datetime(2026, 1, 1))


def test_analysis_timestamp_must_be_timezone_aware(ctx: Context) -> None:
    with pytest.raises(ValueError, match="timezone"):
        Analysis(ctx.file, ctx.integrity, results=(), created_at=datetime.now())

    Analysis(ctx.file, ctx.integrity, results=(), created_at=datetime.now(UTC))
