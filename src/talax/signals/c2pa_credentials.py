"""C2PA Content Credentials: signed provenance information, when present."""

from __future__ import annotations

from talax.i18n import Message
from talax.model import C2paReport, Context, Result, State

# The signed information itself was altered, or the signature is broken.
_TAMPERED = {
    "claimSignature.mismatch",
    "claimSignature.missing",
    "assertion.hashedURI.mismatch",
    "assertion.missing",
}
# The image no longer matches what was signed.
_CONTENT_CHANGED = {
    "assertion.dataHash.mismatch",
    "assertion.bmffHash.mismatch",
    "assertion.boxesHash.mismatch",
}
# Codes with their own plain-language message; others are shown as they are.
_EXPLAINED = _TAMPERED | {
    "signingCredential.untrusted",
    "signingCredential.expired",
    "signingCredential.revoked",
    "ingredient.manifest.missing",
}


def _code(code: str) -> Message:
    if code in _EXPLAINED:
        return Message(f"c2pa.code.{code}")
    return Message("c2pa.code.other", {"code": code})


class C2paCredentials:
    id = "c2pa"
    name = "C2PA Content Credentials"

    def is_relevant(self, ctx: Context) -> bool:
        return True

    def evaluate(self, ctx: Context) -> Result:
        report = ctx.c2pa
        if report is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("c2pa.not_read"),
            )
        evidence = _evidence(report)

        if report.error:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("c2pa.read_error", {"error": report.error}),
                evidence,
            )
        if not report.present:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("c2pa.absent"),
                evidence,
            )

        about = _about(report)
        tampered = [_code(c) for c in report.codes if c in _TAMPERED]
        if tampered:
            return Result(
                self.id,
                State.SUSPICIOUS,
                Message("c2pa.tampered", {"problems": tampered, "about": about}),
                evidence,
            )
        if any(c in _CONTENT_CHANGED for c in report.codes):
            return Result(
                self.id,
                State.TO_CHECK,
                Message("c2pa.content_changed", {"about": about}),
                evidence,
            )
        trust_list = _trust_list(report)
        if report.state == "Trusted":
            return Result(
                self.id,
                State.CONSISTENT,
                Message("c2pa.trusted", {"about": about, "trust_list": trust_list}),
                evidence,
            )
        problems = [_code(c) for c in report.codes] or [Message("c2pa.code.none")]
        return Result(
            self.id,
            State.TO_CHECK,
            Message(
                "c2pa.unconfirmed_signer",
                {"problems": problems, "about": about, "trust_list": trust_list},
            ),
            evidence,
        )


def _about(report: C2paReport) -> Message:
    parts: list[Message] = []
    if report.signer:
        parts.append(Message("c2pa.about.signer", {"signer": report.signer}))
    if report.generator:
        parts.append(Message("c2pa.about.generator", {"generator": report.generator}))
    if report.signed_at:
        parts.append(Message("c2pa.about.signed_at", {"when": report.signed_at}))
    if report.ai_declared:
        parts.append(Message("c2pa.about.ai_declared"))
    if not parts:
        return Message("c2pa.about.nothing")
    return Message("c2pa.about", {"parts": parts})


def _trust_list(report: C2paReport) -> Message:
    if report.trust_list_issued is None:
        return Message("c2pa.trust_list.none")
    if report.trust_list_stale:
        return Message(
            "c2pa.trust_list.stale",
            {
                "issued": report.trust_list_issued,
                "next_update": report.trust_list_next_update,
            },
        )
    return Message("c2pa.trust_list", {"issued": report.trust_list_issued})


def _evidence(report: C2paReport) -> dict[str, object]:
    return {
        "present": report.present,
        "state": report.state,
        "codes": list(report.codes),
        "signer": report.signer,
        "signed_at": report.signed_at,
        "generator": report.generator,
        "ai_declared": report.ai_declared,
        "error": report.error,
        "trust_list_issued": report.trust_list_issued,
        "trust_list_stale": report.trust_list_stale,
    }
