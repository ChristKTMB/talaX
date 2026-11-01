"""The integrity test: original camera file, platform copy, or undetermined.

Runs before any signal; its result goes into the context. Measured platform
fingerprints are tried first. Without a match, generic rules decide, and the
explanation says the platform could not be identified.
"""

from __future__ import annotations

from collections.abc import Sequence

from talax.fingerprints import Fingerprint, builtin_fingerprints
from talax.i18n import Message
from talax.model import IntegrityAssessment, IntegrityVerdict
from talax.traits import Traits, editors_in


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
        verdicts = {f.verdict for f in matches}
        return IntegrityAssessment(
            verdicts.pop() if len(verdicts) == 1 else IntegrityVerdict.UNDETERMINED,
            Message(
                "integrity.several_fingerprints", {"platforms": ", ".join(platforms)}
            ),
            evidence=evidence,
        )

    f = matches[0]
    params = {
        "platform": f.platform,
        "route": f.route,
        "summary": f.summary,
        "samples": f.samples,
        "devices": len(f.devices),
        "date": f.measured_on.isoformat(),
    }
    key = (
        "integrity.fingerprint"
        if f.distinguished_from
        else "integrity.fingerprint_alone"
    )
    return IntegrityAssessment(
        f.verdict, Message(key, params), pipeline=f.id, evidence=evidence
    )


def _from_generic_rules(t: Traits, evidence: dict[str, object]) -> IntegrityAssessment:
    evidence = {**evidence, "basis": "generic"}
    editors = editors_in(t.software)

    if not t.exif_present:
        if t.real_format == "image/jpeg":
            return IntegrityAssessment(
                IntegrityVerdict.REPROCESSED,
                Message("integrity.no_metadata_jpeg"),
                evidence=evidence,
            )
        return IntegrityAssessment(
            IntegrityVerdict.UNDETERMINED,
            Message("integrity.no_metadata_other"),
            evidence=evidence,
        )

    if editors:
        return IntegrityAssessment(
            IntegrityVerdict.UNDETERMINED,
            Message("integrity.editor", {"editors": ", ".join(editors)}),
            evidence=evidence,
        )

    if t.recorded_size and t.pixel_size and t.recorded_size != t.pixel_size:
        (rw, rh), (pw, ph) = t.recorded_size, t.pixel_size
        return IntegrityAssessment(
            IntegrityVerdict.UNDETERMINED,
            Message(
                "integrity.size_mismatch",
                {"actual": f"{pw}x{ph}", "recorded": f"{rw}x{rh}"},
            ),
            evidence=evidence,
        )

    marks = {
        "integrity.mark.make_model": bool(t.make and t.model),
        "integrity.mark.capture_time": bool(t.datetime_original),
        "integrity.mark.vendor_data": bool(t.vendor_groups),
    }
    missing = [Message(key) for key, ok in marks.items() if not ok]
    if missing:
        return IntegrityAssessment(
            IntegrityVerdict.UNDETERMINED,
            Message("integrity.missing_marks", {"missing": missing}),
            evidence=evidence,
        )

    return IntegrityAssessment(
        IntegrityVerdict.ORIGINAL,
        Message(
            "integrity.original",
            {"device": f"{t.make} {t.model}", "vendor": ", ".join(t.vendor_groups)},
        ),
        evidence=evidence,
    )
