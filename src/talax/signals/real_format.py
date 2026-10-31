"""Does the file name extension match what the bytes actually contain?"""

from __future__ import annotations

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
                "The file content is not a format Tala X recognises, so its "
                "real format cannot be compared with its name.",
                evidence,
            )
        if isinstance(exiftool, str) and _family(exiftool) != _family(real):
            return Result(
                self.id,
                State.TO_CHECK,
                f"The file content was read as {_name(real)} by Tala X but as "
                f"{_name(exiftool)} by ExifTool. Such a disagreement is unusual "
                "and worth a closer look.",
                evidence,
            )
        if declared is None:
            return Result(
                self.id,
                State.UNVERIFIABLE,
                f"The file contains {_name(real)} data, but its name has no "
                "known extension to compare with.",
                evidence,
            )
        if _family(declared) == _family(real):
            return Result(
                self.id,
                State.CONSISTENT,
                f"The extension and the content agree: this is a {_name(real)} file.",
                evidence,
            )
        return Result(
            self.id,
            State.TO_CHECK,
            f"The file is named as {_name(declared)} but contains "
            f"{_name(real)} data. This is often harmless (a renamed file, an "
            "app saving in another format), but it means the file is not "
            "what its name says.",
            evidence,
        )
