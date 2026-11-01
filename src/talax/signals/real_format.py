"""Does the file name extension match what the bytes actually contain?"""

from __future__ import annotations

from talax.i18n import Message
from talax.model import Context, Result, State

# Formats that are the same thing under two names.
_FAMILY = {"image/heif": "image/heic"}

_NAMES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/gif": "GIF",
    "image/webp": "WebP",
    "image/tiff": "TIFF",
    "image/heic": "HEIC",
    "image/heif": "HEIF",
    "image/avif": "AVIF",
    "video/mp4": "MP4",
    "video/quicktime": "QuickTime (MOV)",
    "video/3gpp": "3GP",
}


def _family(mime: str) -> str:
    return _FAMILY.get(mime, mime)


def _name(mime: str) -> str:
    return _NAMES.get(mime, mime)


class RealFormat:
    id = "real_format"
    name = "Real file format"

    def is_relevant(self, ctx: Context) -> bool:
        return True

    def evaluate(self, ctx: Context) -> Result:
        declared = ctx.file.declared_format
        real = ctx.file.real_format
        exiftool = ctx.metadata.get("File:MIMEType")
        evidence = {"declared": declared, "real": real, "exiftool": exiftool}

        if real is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("real_format.unrecognised"),
                evidence,
            )
        if isinstance(exiftool, str) and _family(exiftool) != _family(real):
            return Result(
                self.id,
                State.TO_CHECK,
                Message(
                    "real_format.readers_disagree",
                    {"ours": _name(real), "exiftool": _name(exiftool)},
                ),
                evidence,
            )
        if declared is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("real_format.no_extension", {"real": _name(real)}),
                evidence,
            )
        if _family(declared) == _family(real):
            return Result(
                self.id,
                State.CONSISTENT,
                Message("real_format.consistent", {"real": _name(real)}),
                evidence,
            )
        return Result(
            self.id,
            State.TO_CHECK,
            Message(
                "real_format.mismatch",
                {"declared": _name(declared), "real": _name(real)},
            ),
            evidence,
        )
