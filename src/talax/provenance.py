"""Reads C2PA Content Credentials through the official c2pa library."""

from __future__ import annotations

import functools
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

import c2pa
import yaml

from talax.model import C2paReport

# Nothing leaves the machine: no download of remote manifests, no online
# certificate revocation check. (The library accepts unknown keys silently;
# `signingCredential.ocsp.skipped` in its results shows the second is read.)
_SETTINGS = {"verify": {"remote_manifest_fetch": False, "ocsp_fetch": False}}

_AI_SOURCE_TYPES = ("trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia")


@dataclass(frozen=True, slots=True)
class TrustList:
    """The C2PA trust list embedded in the package (see data/c2pa/source.yaml)."""

    anchors: str
    issued: str
    next_update: str
    commit: str


@functools.cache
def embedded_trust_list() -> TrustList:
    """Never downloaded at analysis time: refreshed before each release by
    scripts/update_c2pa_trust.py."""
    return load_trust_list(files("talax") / "data" / "c2pa")


def load_trust_list(folder: Traversable) -> TrustList:
    pem = (folder / "C2PA-TRUST-LIST.pem").read_bytes()
    source = yaml.safe_load((folder / "source.yaml").read_text(encoding="utf-8"))
    if hashlib.sha256(pem).hexdigest() != source["sha256"]:
        raise RuntimeError("the embedded C2PA trust list does not match source.yaml")
    return TrustList(
        anchors=pem.decode("ascii"),
        issued=str(source["issued"]),
        next_update=str(source["next_update"]),
        commit=str(source["commit"]),
    )


def read_c2pa(
    path: Path, trust: TrustList | None = None, now: datetime | None = None
) -> C2paReport:
    """`trust`: the list whose signers count as trusted. Without one no signer
    can be trusted (state "Valid" at best)."""
    settings: dict[str, Any] = dict(_SETTINGS)
    if trust is not None:
        # The library ignores unknown keys silently: tests/test_c2pa_trust.py
        # proves this one is read.
        settings["trust"] = {"trust_anchors": trust.anchors}
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
        **_trust_fields(trust, now or datetime.now(UTC)),
    )


def _trust_fields(trust: TrustList | None, now: datetime) -> dict[str, Any]:
    if trust is None:
        return {}
    next_update = datetime.fromisoformat(trust.next_update)
    if next_update.tzinfo is None:
        next_update = next_update.replace(tzinfo=UTC)
    return {
        "trust_list_issued": trust.issued[:10],
        "trust_list_next_update": trust.next_update[:10],
        "trust_list_stale": now > next_update,
    }


def _generator(manifest: dict[str, Any]) -> str | None:
    if manifest.get("claim_generator"):
        return str(manifest["claim_generator"])
    names = [g.get("name") for g in manifest.get("claim_generator_info", [])]
    return ", ".join(n for n in names if n) or None
