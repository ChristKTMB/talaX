import copy
import datetime as dt
from typing import Any

import pytest

from talax import Metadata
from talax.fingerprints import FingerprintError, builtin_fingerprints, parse_fingerprint
from talax.traits import Traits

VALID: dict[str, Any] = {
    "id": "demo",
    "platform": "Demo",
    "route": {"en": "demo route", "fr": "itinéraire de démo"},
    "summary": {"en": "it does demo things.", "fr": "il fait des choses de démo."},
    "verdict": "reprocessed",
    "match": {
        "formats": ["image/jpeg"],
        "exif": "absent",
        "vendor_data": "absent",
        "progressive": True,
        "segments": ["SOI", "APP0:JFIF", "SOS"],
        "tags": {"JFIF:ResolutionUnit": 0},
    },
    "measured": {
        "date": dt.date(2026, 10, 31),
        "samples": 3,
        "devices": ["phone"],
        "app_versions": ["unknown"],
        "retrieval": "receiver-usb",
    },
    "distinguished_from": [],
}


def traits(**overrides: Any) -> Traits:
    base: dict[str, Any] = {
        "real_format": "image/jpeg",
        "exif_present": False,
        "make": None,
        "model": None,
        "datetime_original": None,
        "vendor_groups": (),
        "software": (),
        "pixel_size": None,
        "recorded_size": None,
        "segments": ("SOI", "APP0:JFIF", "SOS"),
        "progressive": True,
        "tags": Metadata({"JFIF:ResolutionUnit": 0}),
    }
    return Traits(**{**base, **overrides})


def mutated(path: str, value: Any) -> dict[str, Any]:
    raw = copy.deepcopy(VALID)
    *parents, last = path.split(".")
    target = raw
    for key in parents:
        target = target[key]
    if value is KeyError:
        del target[last]
    else:
        target[last] = value
    return raw


def test_builtin_fingerprints_load() -> None:
    assert "whatsapp-gallery" in {f.id for f in builtin_fingerprints()}


def test_valid_fingerprint_matches_its_traits() -> None:
    fingerprint = parse_fingerprint(VALID)
    assert fingerprint.matches(traits())


@pytest.mark.parametrize(
    "override",
    [
        {"real_format": "image/png"},
        {"exif_present": True},
        {"vendor_groups": ("Samsung",)},
        {"progressive": False},
        {"segments": ("SOI", "APP0:JFIF", "DQT", "SOS")},
        {"tags": Metadata({"JFIF:ResolutionUnit": 1})},
        {"tags": Metadata({})},
    ],
)
def test_any_differing_trait_prevents_a_match(override: dict[str, Any]) -> None:
    assert not parse_fingerprint(VALID).matches(traits(**override))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("id", KeyError),
        ("measured", KeyError),
        ("distinguished_from", KeyError),
        ("measured.date", KeyError),
        ("measured.devices", KeyError),
        ("measured.app_versions", KeyError),
        ("measured.devices", []),
        ("measured.samples", 0),
        ("measured.date", "yesterday"),
        ("verdict", "original"),
        ("verdict", "fake"),
        ("platform", " "),
        ("summary", KeyError),
        ("summary", {"en": "only English"}),
        ("route", "not localized"),
        ("summary.fr", " "),
        ("match", {}),
        ("match.exif", "maybe"),
        ("match.progressive", "yes"),
        ("match.segments", []),
        ("match.colour", "red"),
        ("unexpected", 1),
    ],
)
def test_incomplete_or_invalid_fingerprints_are_rejected(path: str, value: Any) -> None:
    with pytest.raises(FingerprintError):
        parse_fingerprint(mutated(path, value))
