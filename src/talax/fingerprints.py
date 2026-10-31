"""Platform fingerprints: loading, validation and matching.

A fingerprint describes what a platform's output looks like, measured on the
reference corpus. Fingerprints live in YAML files so they can be contributed
without touching the code. An incomplete fingerprint is rejected at load time.
"""

from __future__ import annotations

import datetime as dt
import functools
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from talax.model import IntegrityVerdict
from talax.traits import Traits

_FIELDS = {
    "id",
    "platform",
    "route",
    "summary",
    "verdict",
    "match",
    "measured",
    "distinguished_from",
}
_MATCH_KEYS = {"formats", "exif", "vendor_data", "progressive", "segments", "tags"}
_MEASURED_KEYS = {"date", "samples", "devices", "app_versions", "retrieval"}
_PRESENCE = {"present", "absent"}


class FingerprintError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Fingerprint:
    id: str
    platform: str
    route: str
    summary: str
    """One plain-language sentence on what this app or platform does."""
    verdict: IntegrityVerdict
    match: Mapping[str, Any]
    measured_on: dt.date
    samples: int
    devices: tuple[str, ...]
    distinguished_from: tuple[str, ...]

    def matches(self, traits: Traits) -> bool:
        m = self.match
        if "formats" in m and traits.real_format not in m["formats"]:
            return False
        if "exif" in m and traits.exif_present != (m["exif"] == "present"):
            return False
        if "vendor_data" in m and bool(traits.vendor_groups) != (
            m["vendor_data"] == "present"
        ):
            return False
        if "progressive" in m and traits.progressive is not m["progressive"]:
            return False
        if "segments" in m and traits.segments != tuple(m["segments"]):
            return False
        return all(traits.tags.get(k) == v for k, v in m.get("tags", {}).items())


@functools.cache
def builtin_fingerprints() -> tuple[Fingerprint, ...]:
    folder = files("talax") / "data" / "fingerprints"
    return load_fingerprints(
        Path(str(p)) for p in folder.iterdir() if p.name.endswith(".yaml")
    )


def load_fingerprints(paths: Iterable[Path]) -> tuple[Fingerprint, ...]:
    loaded = sorted(
        (parse_fingerprint(yaml.safe_load(p.read_text()), p.name) for p in paths),
        key=lambda f: f.id,
    )
    ids = [f.id for f in loaded]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise FingerprintError(f"duplicate fingerprint ids: {duplicates}")
    return tuple(loaded)


def parse_fingerprint(raw: object, source: str = "<fingerprint>") -> Fingerprint:
    def fail(message: str) -> FingerprintError:
        return FingerprintError(f"{source}: {message}")

    if not isinstance(raw, dict):
        raise fail("must be a mapping")
    _check_keys(raw, _FIELDS, _FIELDS, fail)

    for name in ("id", "platform", "route", "summary"):
        if not isinstance(raw[name], str) or not raw[name].strip():
            raise fail(f"`{name}` must be a non-empty string")
    try:
        verdict = IntegrityVerdict(raw["verdict"])
    except ValueError:
        raise fail(f"unknown verdict {raw['verdict']!r}") from None
    if verdict is IntegrityVerdict.ORIGINAL:
        raise fail("a fingerprint describes a copy or an edit, never an original")

    match = raw["match"]
    if not isinstance(match, dict) or not match:
        raise fail("`match` must be a non-empty mapping")
    _check_keys(match, set(), _MATCH_KEYS, fail, "match")
    for key in ("exif", "vendor_data"):
        if key in match and match[key] not in _PRESENCE:
            raise fail(f"`match.{key}` must be `present` or `absent`")
    if "progressive" in match and not isinstance(match["progressive"], bool):
        raise fail("`match.progressive` must be true or false")
    for key in ("formats", "segments"):
        if key in match and not _is_str_list(match[key]):
            raise fail(f"`match.{key}` must be a non-empty list of strings")
    if "tags" in match and not isinstance(match["tags"], dict):
        raise fail("`match.tags` must be a mapping")

    measured = raw["measured"]
    if not isinstance(measured, dict):
        raise fail("`measured` must be a mapping")
    _check_keys(measured, _MEASURED_KEYS, None, fail, "measured")
    if not isinstance(measured["date"], dt.date):
        raise fail("`measured.date` must be a date (YYYY-MM-DD)")
    if not isinstance(measured["samples"], int) or measured["samples"] < 1:
        raise fail("`measured.samples` must be a positive integer")
    for key in ("devices", "app_versions"):
        if not _is_str_list(measured[key]):
            raise fail(f"`measured.{key}` must be a non-empty list of strings")

    distinguished = raw["distinguished_from"]
    if not isinstance(distinguished, list) or not all(
        isinstance(d, str) for d in distinguished
    ):
        raise fail("`distinguished_from` must be a list of fingerprint ids")

    return Fingerprint(
        id=raw["id"],
        platform=raw["platform"],
        route=raw["route"],
        summary=raw["summary"].strip(),
        verdict=verdict,
        match=match,
        measured_on=measured["date"],
        samples=measured["samples"],
        devices=tuple(measured["devices"]),
        distinguished_from=tuple(distinguished),
    )


def _check_keys(
    mapping: dict[str, Any],
    required: set[str],
    allowed: set[str] | None,
    fail: Any,
    where: str = "",
) -> None:
    prefix = f"`{where}`: " if where else ""
    missing = required - mapping.keys()
    if missing:
        raise fail(f"{prefix}missing {sorted(missing)}")
    if allowed is not None:
        unknown = mapping.keys() - allowed
        if unknown:
            raise fail(f"{prefix}unknown {sorted(unknown)}")


def _is_str_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(v, str) and v for v in value)
    )
