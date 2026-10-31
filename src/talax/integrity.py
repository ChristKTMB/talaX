"""The integrity test: original camera file, platform copy, or undetermined.

Runs before any signal; its result goes into the context. Measured platform
fingerprints are tried first. Without a match, generic rules decide, and the
explanation says the platform could not be identified.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from importlib.resources import files

import yaml

from talax.fingerprints import Fingerprint, builtin_fingerprints
from talax.model import IntegrityAssessment, IntegrityVerdict
from talax.traits import Traits

_FORGERY_CAVEAT = (
    " This says where the file comes from, not whether its content is true: "
    "metadata can be forged by anyone who knows how."
)


@functools.cache
def known_editors() -> tuple[str, ...]:
    raw = yaml.safe_load((files("talax") / "data" / "editors.yaml").read_text())
    return tuple(raw["editors"])


def assess_integrity(
    traits: Traits, fingerprints: Sequence[Fingerprint] | None = None
) -> IntegrityAssessment:
    if fingerprints is None:
        fingerprints = builtin_fingerprints()
    evidence = traits.as_evidence()

    matches = [f for f in fingerprints if f.matches(traits)]
    if matches:
        return _from_fingerprints(matches, evidence)
    return _from_generic_rules(traits, evidence)


def _from_fingerprints(
    matches: list[Fingerprint], evidence: dict[str, object]
) -> IntegrityAssessment:
    evidence = {
        **evidence,
        "basis": "fingerprint",
        "fingerprints": [f.id for f in matches],
    }
    platforms = sorted({f.platform for f in matches})
    if len(platforms) > 1:
        return IntegrityAssessment(
            IntegrityVerdict.REPROCESSED,
            "The file matches the measured fingerprints of several platforms ("
            + ", ".join(platforms)
            + "), which cannot be told apart on this file.",
            evidence=evidence,
        )

    f = matches[0]
    explanation = (
        f"The file matches the fingerprint of {f.platform}, {f.route}: the "
        "camera metadata is gone and the image was re-encoded the way this "
        f"platform does it. Fingerprint measured on {f.samples} files from "
        f"{len(f.devices)} device(s), {f.measured_on.isoformat()}."
    )
    if not f.distinguished_from:
        explanation += (
            " No other platform has been measured yet, so another platform "
            "producing the same output cannot be ruled out."
        )
    return IntegrityAssessment(f.verdict, explanation, pipeline=f.id, evidence=evidence)


def _from_generic_rules(t: Traits, evidence: dict[str, object]) -> IntegrityAssessment:
    evidence = {**evidence, "basis": "generic"}
    editors = [
        s for s in t.software if any(e.lower() in s.lower() for e in known_editors())
    ]

    if not t.exif_present:
        if t.real_format == "image/jpeg":
            return IntegrityAssessment(
                IntegrityVerdict.REPROCESSED,
                "The file carries no camera metadata at all. Phones and cameras "
                "write it when they save a photo, so the file was re-saved by an "
                "app or platform that removed it. No measured platform "
                "fingerprint matches, so which one is unknown.",
                evidence=evidence,
            )
        return IntegrityAssessment(
            IntegrityVerdict.UNDETERMINED,
            "The file carries no camera metadata. It may be a screenshot, an "
            "export or a platform copy; nothing in it tells which.",
            evidence=evidence,
        )

    if editors:
        return IntegrityAssessment(
            IntegrityVerdict.UNDETERMINED,
            "Camera metadata is present, but the file was saved by an image "
            f"editor ({', '.join(editors)}). It is no longer the file the "
            "camera produced, and it is not a platform copy either.",
            evidence=evidence,
        )

    marks = {
        "camera make and model": bool(t.make and t.model),
        "original capture time": bool(t.datetime_original),
        "manufacturer-specific data": bool(t.vendor_groups),
    }
    missing = [name for name, ok in marks.items() if not ok]
    if missing:
        return IntegrityAssessment(
            IntegrityVerdict.UNDETERMINED,
            "Some camera metadata is present, but marks a camera original "
            f"always has are missing: {', '.join(missing)}. The file may have "
            "been re-saved by an app that kept part of the metadata.",
            evidence=evidence,
        )

    device = f"{t.make} {t.model}"
    return IntegrityAssessment(
        IntegrityVerdict.ORIGINAL,
        f"The file has the marks of a camera original from a {device}: make "
        "and model, original capture time, and manufacturer-specific data ("
        + ", ".join(t.vendor_groups)
        + "), with no image editor recorded."
        + _FORGERY_CAVEAT,
        evidence=evidence,
    )
