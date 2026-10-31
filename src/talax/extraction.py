"""Metadata extraction through ExifTool, an external program."""

from __future__ import annotations

import functools
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from talax.model import Metadata

MIN_EXIFTOOL_VERSION = (13, 0)
_TIMEOUT_SECONDS = 60

# -G1: precise group (`ExifIFD:DateTimeOriginal`), so a tag forged in another
#      block shows up separately. -a: keep duplicates. -n: raw numeric values.
# System tags (file name, directory, dates, permissions) describe the local
# copy, not the content, and may leak private paths: excluded.
_ARGS = ("-json", "-G1", "-a", "-n", "--System:all")


class ExifToolError(RuntimeError):
    pass


class ExifToolMissingError(ExifToolError):
    pass


@functools.cache
def exiftool_version() -> tuple[int, int]:
    """Installed ExifTool version. Raises if missing or too old."""
    if shutil.which("exiftool") is None:
        raise ExifToolMissingError(
            "ExifTool is required but was not found. Install it from "
            "https://exiftool.org/ and make sure `exiftool` is on your PATH."
        )
    out = _run(["-ver"]).strip()
    try:
        major, minor = (int(part) for part in out.split(".")[:2])
    except ValueError as exc:
        raise ExifToolError(f"unexpected ExifTool version output: {out!r}") from exc
    if (major, minor) < MIN_EXIFTOOL_VERSION:
        wanted = ".".join(map(str, MIN_EXIFTOOL_VERSION))
        raise ExifToolError(
            f"ExifTool {out} is too old; Tala X needs {wanted} or newer. Older "
            "versions miss vendor tags and would give different results."
        )
    return major, minor


def read_metadata(path: Path) -> Metadata:
    exiftool_version()
    # An absolute path cannot be mistaken for an option (`-name.jpg`).
    out = _run([*_ARGS, str(path.resolve())])
    try:
        (record,) = json.loads(out, object_pairs_hook=_keep_duplicates)
    except ValueError as exc:
        raise ExifToolError("could not parse ExifTool output") from exc
    record.pop("SourceFile", None)  # local path: private, not content
    return Metadata(record)


def read_thumbnail(path: Path) -> bytes | None:
    """Embedded EXIF preview image (IFD1), or None if the file has none."""
    exiftool_version()
    try:
        proc = subprocess.run(
            ["exiftool", "-b", "-ThumbnailImage", str(path.resolve())],
            capture_output=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    return proc.stdout or None


def _run(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["exiftool", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExifToolError(f"ExifTool timed out after {_TIMEOUT_SECONDS}s") from exc
    if proc.returncode != 0 and not proc.stdout:
        raise ExifToolError(proc.stderr.strip() or "ExifTool failed")
    return proc.stdout


def _keep_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Same tag twice in the same group is itself evidence: never drop one."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        name, n = key, 1
        while name in result:
            n += 1
            name = f"{key}#{n}"
        result[name] = value
    return result
