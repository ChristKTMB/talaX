"""Writes docs/api-examples/: real responses of the web API, one per situation.

Every file analysed here is synthetic, built on the spot with Pillow and
ExifTool: corpus photos carry real positions and device serial numbers and
must never end up in the repository. A forged file can pass for a camera
original; that is the threat model of Tala X (section 5 of the project
notes), and the reason these examples say nothing about real devices.

    uv run python scripts/api_examples.py

tests/test_api_examples.py regenerates them and fails if the committed files
no longer match what the API answers.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

from talax.api import app as api

OUT = Path(__file__).resolve().parent.parent / "docs" / "api-examples"
LANGS = ("en", "fr")
_FIXED_TIME = "2026-01-01T12:00:00+00:00"  # keeps diffs to what matters

_CAMERA = [
    "-IFD0:Make=Generic",
    "-IFD0:Model=Camera 1",
    "-ExifIFD:DateTimeOriginal=2025:06:21 13:50:00",
    "-ExifIFD:OffsetTimeOriginal=+02:00",
    "-ExifIFD:ExifImageWidth=640",
    "-ExifIFD:ExifImageHeight=480",
    # Manufacturer data observed on real phones (see vendor_groups.yaml).
    "-XMP-GCamera:MotionPhoto=0",
]
_PARIS = [
    "-GPSLatitude=48.8566",
    "-GPSLatitudeRef=N",
    "-GPSLongitude=2.3522",
    "-GPSLongitudeRef=E",
]


def _exiftool(path: Path, *args: str) -> None:
    cmd = ["exiftool", "-q", "-overwrite_original", *args, str(path)]
    subprocess.run(cmd, check=True)


def _jpeg(path: Path, **save: Any) -> Path:
    Image.new("RGB", (640, 480), (90, 130, 170)).save(path, quality=90, **save)
    return path


def _camera_original(d: Path) -> Path:
    path = _jpeg(d / "original.jpg")
    _exiftool(path, *_CAMERA, *_PARIS)
    thumb = _jpeg(d / "thumb.jpg")
    Image.open(thumb).resize((160, 120)).save(thumb)
    _exiftool(path, f"-ThumbnailImage<={thumb}")
    return path


def _gps_masked(d: Path) -> Path:
    path = _jpeg(d / "masked.jpg")
    _exiftool(path, *_CAMERA, "-GPS:GPSVersionID=2 3 0 0")
    return path


def _edited(d: Path) -> Path:
    path = _jpeg(d / "edited.jpg")
    _exiftool(path, *_CAMERA, *_PARIS, "-IFD0:Software=Adobe Photoshop 26.0")
    return path


def _platform_copy(d: Path) -> Path:
    # What WhatsApp sends from the gallery: progressive JPEG, JFIF, no EXIF,
    # and its tables packed in one DQT and one DHT segment, where libjpeg
    # writes one segment per table.
    path = _jpeg(d / "copy.jpg", progressive=True)
    path.write_bytes(_pack_tables(path.read_bytes()))
    return path


def _pack_tables(data: bytes) -> bytes:
    """Merges consecutive DQT (or DHT) segments before the first scan."""
    out, pos = bytearray(data[:2]), 2  # SOI
    pending: tuple[int, bytearray] | None = None
    while data[pos + 1] != 0xDA:  # until SOS
        marker = data[pos + 1]
        length = int.from_bytes(data[pos + 2 : pos + 4], "big")
        payload = data[pos + 4 : pos + 2 + length]
        pos += 2 + length
        if pending is not None and pending[0] == marker and marker in (0xDB, 0xC4):
            pending[1].extend(payload)
            continue
        if pending is not None:
            out += _segment(*pending)
        pending = (marker, bytearray(payload))
    if pending is not None:
        out += _segment(*pending)
    return bytes(out + data[pos:])


def _segment(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + (len(payload) + 2).to_bytes(2, "big") + payload


def _png(d: Path) -> Path:
    path = d / "image.png"
    Image.new("RGB", (640, 480), (90, 130, 170)).save(path)
    return path


# name -> (file builder, name sent as the upload, form fields)
CASES: dict[str, tuple[Callable[[Path], Path], str, dict[str, str]]] = {
    "camera-original": (_camera_original, "photo.jpg", {"sky": "day"}),
    "camera-original-no-sky": (_camera_original, "photo.jpg", {}),
    "solar-contradiction": (_camera_original, "photo.jpg", {"sky": "night"}),
    "gps-masked": (_gps_masked, "photo.jpg", {}),
    "edited": (_edited, "photo.jpg", {}),
    "platform-copy": (_platform_copy, "photo.jpg", {}),
    "png-without-metadata": (_png, "image.png", {}),
    "wrong-extension": (_platform_copy, "photo.png", {}),
}


@contextmanager
def _all_slots_taken() -> Iterator[None]:
    for _ in range(api.MAX_CONCURRENT_ANALYSES):
        api._slots.acquire()
    try:
        yield
    finally:
        for _ in range(api.MAX_CONCURRENT_ANALYSES):
            api._slots.release()


def _errors(client: TestClient, lang: str) -> dict[str, Any]:
    h = {"accept-language": lang}
    tiny = {"file": ("photo.jpg", b"\xff\xd8\xff")}
    with _all_slots_taken():
        busy = client.post("/api/analyze", files=tiny, headers=h)
    responses = {
        "file-too-large": client.post(
            "/api/analyze", content=b"x", headers={**h, "content-length": "10" * 5}
        ),
        "invalid-request": client.post(
            "/api/analyze", files=tiny, data={"sky": "noon"}, headers=h
        ),
        "busy": busy,
        "not-found": client.get("/api/nowhere", headers=h),
    }
    return {
        name: {"status": r.status_code, **r.json()} for name, r in responses.items()
    }


def generate() -> dict[str, Any]:
    """Every example, keyed by file name (without the .json)."""
    examples: dict[str, Any] = {}
    with TestClient(api.app) as client, tempfile.TemporaryDirectory() as tmp:
        for name, (build, upload_name, form) in CASES.items():
            case_dir = Path(tmp) / name
            case_dir.mkdir()
            content = build(case_dir).read_bytes()
            for lang in LANGS:
                response = client.post(
                    "/api/analyze",
                    files={"file": (upload_name, content)},
                    data={**form, "lang": lang},
                )
                response.raise_for_status()
                data = response.json()
                data["created_at"] = _FIXED_TIME
                examples[f"{name}.{lang}"] = data
        for lang in LANGS:
            for name, body in _errors(client, lang).items():
                examples[f"error-{name}.{lang}"] = body
    return examples


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for name, data in generate().items():
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        (OUT / f"{name}.json").write_text(text, encoding="utf-8")
        verdict = data.get("integrity", {}).get("verdict", data.get("status"))
        print(f"{name:40} {verdict}", file=sys.stderr)


if __name__ == "__main__":
    main()
