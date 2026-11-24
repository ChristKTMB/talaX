"""Whether two files show the same picture: a small visual fingerprint.

A difference hash: the image, upright, shrunk to a tiny grey grid, and for
each cell whether it is brighter than its right neighbour. Recompression and
resizing barely change it; a different scene changes about half of it.

This compares two images with each other. It says nothing about whether an
image is true, and it is never a check with a state (project rules, section 3).
"""

from __future__ import annotations

from pathlib import Path
from statistics import pstdev

from PIL import Image, ImageOps

from talax.model import VisualHash

# Measured on the corpus (2026-11-24, 16x16 grid, training figures): platform
# copies and rotations 0-12 bits apart, edits 13-43, different photos 82 and
# more. Crops are mostly not found.
SAME_IMAGE = 16
SIMILAR = 48
# Spread of grey levels (standard deviation, 0-255) below which a picture has
# too little detail to fingerprint: two black frames would look identical.
# A uniform image measures 0; the flattest real photo of the corpus 7.2.
MIN_DETAIL = 3.0


def visual_hash(path: Path, size: int = 16) -> VisualHash | None:
    """None when the file cannot be read as an image (video, damaged...), or
    when the picture is too uniform to tell apart from another one."""
    try:
        with Image.open(path) as im:
            im.draft("L", (size * 8, size * 8))
            grey = ImageOps.exif_transpose(im).convert("L")
    except (OSError, ValueError, Image.DecompressionBombError):
        return None
    if (
        pstdev(grey.resize((size + 1, size), Image.Resampling.LANCZOS).tobytes())
        < MIN_DETAIL
    ):
        return None
    turns = tuple(
        _dhash(grey.rotate(angle, expand=True), size) for angle in (0, 90, 180, 270)
    )
    return VisualHash(turns=turns, size=size)  # type: ignore[arg-type]


def distance(a: VisualHash, b: VisualHash) -> int:
    """Bits that differ, the copy turned the way that matches best."""
    if a.size != b.size:
        raise ValueError("hashes of different sizes")
    return min(bin(a.turns[0] ^ turned).count("1") for turned in b.turns)


def _dhash(image: Image.Image, size: int) -> int:
    small = image.resize((size + 1, size), Image.Resampling.LANCZOS)
    pixels = small.tobytes()  # one byte per pixel in mode L
    bits = 0
    for row in range(size):
        for col in range(size):
            left = pixels[row * (size + 1) + col]
            right = pixels[row * (size + 1) + col + 1]
            bits = (bits << 1) | (left > right)
    return bits
