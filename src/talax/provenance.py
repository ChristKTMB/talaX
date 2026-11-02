"""Reads C2PA Content Credentials through the official c2pa library."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import c2pa

from talax.model import C2paReport

# Nothing leaves the machine: no download of remote manifests, no online
# certificate revocation check. (The library accepts unknown keys silently,
# so these names follow the c2pa-rs settings documentation.)
_SETTINGS = {"verify": {"remote_manifest_fetch": False, "ocsp_fetch": False}}

_AI_SOURCE_TYPES = ("trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia")


def read_c2pa(path: Path, trust_anchors: str | None = None) -> C2paReport:
    """`trust_anchors`: PEM root certificates whose signers count as trusted.
    Without them no signer can be trusted (state "Valid" at best)."""
    settings: dict[str, Any] = dict(_SETTINGS)
    if trust_anchors:
        # The library ignores unknown keys silently: tests/test_c2pa_trust.py
        # proves this one is read.
        settings["trust"] = {"trust_anchors": trust_anchors}
    context = c2pa.Context(settings=c2pa.Settings.from_dict(settings))
    try:
        with c2pa.Reader(str(path), context=context) as reader:
            store = json.loads(reader.json())
            state = reader.get_validation_state()
    except c2pa.C2paError as exc:
        if "ManifestNotFound" in type(exc).__name__ or "no JUMBF" in str(exc):
            return C2paReport(present=False)
        if "NotSupported" in type(exc).__name__ or "not supported" in str(exc):
            return C2paReport(present=False, error="format not supported by C2PA")
        return C2paReport(present=True, error=f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # a C2PA failure must not stop the whole analysis
        return C2paReport(present=False, error=f"{type(exc).__name__}: {exc}")

    manifest = store.get("manifests", {}).get(store.get("active_manifest"), {})
    signature = manifest.get("signature_info", {})
    return C2paReport(
        present=True,
        state=str(state) if state is not None else None,
        codes=tuple(str(s.get("code")) for s in store.get("validation_status") or []),
        signer=signature.get("issuer"),
        signed_at=signature.get("time"),
        generator=_generator(manifest),
        ai_declared=any(t in json.dumps(manifest) for t in _AI_SOURCE_TYPES),
    )


def _generator(manifest: dict[str, Any]) -> str | None:
    if manifest.get("claim_generator"):
        return str(manifest["claim_generator"])
    names = [g.get("name") for g in manifest.get("claim_generator_info", [])]
    return ", ".join(n for n in names if n) or None
