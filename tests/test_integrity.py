from typing import Any

from talax import IntegrityVerdict, Metadata
from talax.fingerprints import parse_fingerprint
from talax.integrity import assess_integrity
from talax.traits import Traits
from tests.test_fingerprints import VALID, traits

ORIGINAL_TRAITS: dict[str, Any] = {
    "exif_present": True,
    "make": "samsung",
    "model": "Galaxy A34 5G",
    "datetime_original": "2026:10:31 09:58:41",
    "vendor_groups": ("Samsung",),
    "segments": ("SOI", "APP1:Exif", "DQT", "SOF0", "SOS"),
    "progressive": False,
    "tags": Metadata({}),
}


def camera(**overrides: Any) -> Traits:
    return traits(**{**ORIGINAL_TRAITS, **overrides})


def test_all_camera_marks_give_original_with_the_forgery_caveat() -> None:
    result = assess_integrity(camera(), fingerprints=[])
    assert result.verdict is IntegrityVerdict.ORIGINAL
    assert "forged" in result.explanation
    assert result.evidence["basis"] == "generic"
    assert result.pipeline is None


def test_one_missing_mark_is_enough_to_withhold_original() -> None:
    for missing in (
        {"make": None},
        {"datetime_original": None},
        {"vendor_groups": ()},
    ):
        result = assess_integrity(camera(**missing), fingerprints=[])
        assert result.verdict is IntegrityVerdict.UNDETERMINED


def test_editor_gives_undetermined_and_names_it() -> None:
    result = assess_integrity(
        camera(software=("Adobe Photoshop Lightroom Classic 13.0",)), fingerprints=[]
    )
    assert result.verdict is IntegrityVerdict.UNDETERMINED
    assert "Lightroom" in result.explanation


def test_firmware_in_software_tag_is_not_an_editor() -> None:
    result = assess_integrity(camera(software=("A346BXXSHFZJ4",)), fingerprints=[])
    assert result.verdict is IntegrityVerdict.ORIGINAL


def test_jpeg_without_any_metadata_is_reprocessed_by_an_unknown_platform() -> None:
    result = assess_integrity(traits(), fingerprints=[])
    assert result.verdict is IntegrityVerdict.REPROCESSED
    assert result.pipeline is None
    assert "unknown" in result.explanation


def test_non_jpeg_without_metadata_is_undetermined() -> None:
    result = assess_integrity(traits(real_format="image/png"), fingerprints=[])
    assert result.verdict is IntegrityVerdict.UNDETERMINED


def test_fingerprint_match_names_the_platform_and_its_limits() -> None:
    result = assess_integrity(traits(), fingerprints=[parse_fingerprint(VALID)])
    assert result.verdict is IntegrityVerdict.REPROCESSED
    assert result.pipeline == "demo"
    assert result.evidence["basis"] == "fingerprint"
    assert "cannot be ruled out" in result.explanation


def test_distinguished_fingerprint_drops_the_caveat() -> None:
    fingerprint = parse_fingerprint({**VALID, "distinguished_from": ["other"]})
    result = assess_integrity(traits(), fingerprints=[fingerprint])
    assert "cannot be ruled out" not in result.explanation


def test_two_platforms_matching_is_reported_without_choosing() -> None:
    a = parse_fingerprint(VALID)
    b = parse_fingerprint({**VALID, "id": "other", "platform": "Other"})
    result = assess_integrity(traits(), fingerprints=[a, b])
    assert result.verdict is IntegrityVerdict.REPROCESSED
    assert result.pipeline is None
    assert "Demo" in result.explanation and "Other" in result.explanation
