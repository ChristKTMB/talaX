"""Measurable traits of a file, the vocabulary shared by fingerprints and rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from talax.jpeg import JpegStructure
from talax.model import FileInfo, Metadata

_EXIF_GROUPS = ("IFD0", "ExifIFD", "GPS", "IFD1", "InteropIFD")

# Groups any software may write. Everything else ExifTool reports is
# manufacturer-specific (maker notes, Samsung trailer, Google camera XMP...).
_STANDARD_GROUPS = {
    *_EXIF_GROUPS,
    "ExifTool",
    "File",
    "Composite",
    "JFIF",
    "IPTC",
    "Photoshop",
    "XMP-x",
    "XMP-xmp",
    "XMP-xmpMM",
    "XMP-dc",
    "XMP-tiff",
    "XMP-exif",
    "XMP-exifEX",
    "XMP-photoshop",
    "XMP-crs",
    "XMP-aux",
}

SOFTWARE_TAGS = (
    "IFD0:Software",
    "XMP-xmp:CreatorTool",
    "XMP-xmpMM:HistorySoftwareAgent",
)


@dataclass(frozen=True, slots=True)
class Traits:
    real_format: str | None
    exif_present: bool
    make: str | None
    model: str | None
    datetime_original: str | None
    vendor_groups: tuple[str, ...]
    software: tuple[str, ...]
    segments: tuple[str, ...] | None
    """JPEG segment names, None when the file is not a readable JPEG."""
    progressive: bool | None
    tags: Metadata

    def as_evidence(self) -> dict[str, Any]:
        return {
            "exif_present": self.exif_present,
            "make": self.make,
            "model": self.model,
            "datetime_original": self.datetime_original,
            "vendor_groups": list(self.vendor_groups),
            "software": list(self.software),
            "segments": list(self.segments) if self.segments else None,
            "progressive": self.progressive,
        }


def read_traits(
    file: FileInfo, metadata: Metadata, jpeg: JpegStructure | None
) -> Traits:
    groups = {key.split(":", 1)[0] for key in metadata.tags if ":" in key}
    software: list[str] = []
    for tag in SOFTWARE_TAGS:
        value = metadata.get(tag)
        values = value if isinstance(value, list) else [value]
        software.extend(str(v) for v in values if v not in (None, ""))
    return Traits(
        real_format=file.real_format,
        exif_present=bool(groups & set(_EXIF_GROUPS)),
        make=_text(metadata.get("IFD0:Make")),
        model=_text(metadata.get("IFD0:Model")),
        datetime_original=_text(metadata.get("ExifIFD:DateTimeOriginal")),
        vendor_groups=tuple(sorted(groups - _STANDARD_GROUPS)),
        software=tuple(software),
        segments=jpeg.segments if jpeg else None,
        progressive=jpeg.progressive if jpeg else None,
        tags=metadata,
    )


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
