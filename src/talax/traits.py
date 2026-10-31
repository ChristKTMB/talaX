"""Measurable traits of a file, the vocabulary shared by fingerprints and rules."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

import yaml

from talax.jpeg import JpegStructure
from talax.model import FileInfo, Metadata

_EXIF_GROUPS = ("IFD0", "ExifIFD", "GPS", "IFD1", "InteropIFD")


@functools.cache
def vendor_group_names() -> frozenset[str]:
    """Groups only a manufacturer writes, as observed in the corpus."""
    raw = yaml.safe_load((files("talax") / "data" / "vendor_groups.yaml").read_text())
    return frozenset(raw["vendor_groups"])


@functools.cache
def known_editors() -> tuple[str, ...]:
    raw = yaml.safe_load((files("talax") / "data" / "editors.yaml").read_text())
    return tuple(raw["editors"])


def editors_in(software: tuple[str, ...]) -> list[str]:
    """Software strings that name a known image editor."""
    names = [e.lower() for e in known_editors()]
    return [s for s in software if any(n in s.lower() for n in names)]


def software_strings(metadata: Metadata) -> tuple[str, ...]:
    found: list[str] = []
    for tag in SOFTWARE_TAGS:
        value = metadata.get(tag)
        values = value if isinstance(value, list) else [value]
        found.extend(str(v) for v in values if v not in (None, ""))
    return tuple(found)


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
    pixel_size: tuple[int, int] | None
    """Width and height of the stored image, as decoded."""
    recorded_size: tuple[int, int] | None
    """Width and height the camera wrote in the EXIF, when present."""
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
            "pixel_size": self.pixel_size,
            "recorded_size": self.recorded_size,
            "segments": list(self.segments) if self.segments else None,
            "progressive": self.progressive,
        }


def read_traits(
    file: FileInfo, metadata: Metadata, jpeg: JpegStructure | None
) -> Traits:
    groups = {key.split(":", 1)[0] for key in metadata.tags if ":" in key}
    return Traits(
        real_format=file.real_format,
        exif_present=bool(groups & set(_EXIF_GROUPS)),
        make=_text(metadata.get("IFD0:Make")),
        model=_text(metadata.get("IFD0:Model")),
        datetime_original=_text(metadata.get("ExifIFD:DateTimeOriginal")),
        vendor_groups=tuple(sorted(groups & vendor_group_names())),
        software=software_strings(metadata),
        pixel_size=_size(metadata, "File:ImageWidth", "File:ImageHeight"),
        recorded_size=_size(
            metadata, "ExifIFD:ExifImageWidth", "ExifIFD:ExifImageHeight"
        ),
        segments=jpeg.segments if jpeg else None,
        progressive=jpeg.progressive if jpeg else None,
        tags=metadata,
    )


def _size(metadata: Metadata, width: str, height: str) -> tuple[int, int] | None:
    w, h = metadata.get(width), metadata.get(height)
    if isinstance(w, int) and isinstance(h, int):
        return w, h
    return None


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
