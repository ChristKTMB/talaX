"""File identity: hash, format implied by the name, format read from the bytes."""

from __future__ import annotations

import hashlib
from pathlib import Path

from talax.model import FileInfo

_CHUNK = 1024 * 1024
_SNIFF_SIZE = 32

EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".jpe": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".avif": "image/avif",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
}

# ISO base media files (HEIC, AVIF, MP4, MOV) all start with an `ftyp` box;
# its major brand tells them apart.
_FTYP_BRANDS = {
    b"heic": "image/heic",
    b"heix": "image/heic",
    b"heim": "image/heic",
    b"heis": "image/heic",
    b"hevc": "image/heic",
    b"hevx": "image/heic",
    b"mif1": "image/heif",
    b"msf1": "image/heif",
    b"avif": "image/avif",
    b"avis": "image/avif",
    b"qt  ": "video/quicktime",
    b"isom": "video/mp4",
    b"iso2": "video/mp4",
    b"iso4": "video/mp4",
    b"iso5": "video/mp4",
    b"iso6": "video/mp4",
    b"mp41": "video/mp4",
    b"mp42": "video/mp4",
    b"avc1": "video/mp4",
    b"M4V ": "video/mp4",
    b"3gp4": "video/3gpp",
    b"3gp5": "video/3gpp",
}


def read_file_info(path: Path) -> FileInfo:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        head = f.read(_SNIFF_SIZE)
        digest.update(head)
        size += len(head)
        while chunk := f.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return FileInfo(
        sha256=digest.hexdigest(),
        size=size,
        declared_format=EXTENSIONS.get(path.suffix.lower()),
        real_format=sniff_format(head),
    )


def sniff_format(head: bytes) -> str | None:
    """MIME type from the first bytes of a file, or None if unrecognised."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    if head[4:8] == b"ftyp":
        return _FTYP_BRANDS.get(head[8:12])
    return None
