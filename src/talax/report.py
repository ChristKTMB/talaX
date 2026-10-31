"""Renders an existing analysis: plain data (JSON) and a self-contained HTML page.

Nothing here analyses anything. The HTML page loads no external resource
(fonts, scripts, map tiles), so opening it sends nothing over the network.
"""

from __future__ import annotations

import base64
import io
from collections.abc import Mapping
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape
from PIL import Image, ImageOps

from talax.extraction import exiftool_version, read_thumbnail
from talax.model import Analysis, IntegrityVerdict, State

SCHEMA_VERSION = 1

DISCLAIMER = (
    "Tala X never certifies that an image is authentic. It reports what can "
    "honestly be said about a file. An original camera file is not proof that "
    "its content is true: metadata can be forged by anyone who knows how. "
    "Tala X is built against platform laundering and recycled images, not "
    "against expert forgers."
)

STATE_LABELS = {
    State.CONSISTENT: "Consistent",
    State.TO_CHECK: "To check",
    State.SUSPICIOUS: "Suspicious",
    State.UNVERIFIABLE: "Unverifiable",
}
VERDICT_LABELS = {
    IntegrityVerdict.ORIGINAL: "Original camera file",
    IntegrityVerdict.REPROCESSED: "Reprocessed copy",
    IntegrityVerdict.UNDETERMINED: "Undetermined",
}
_STATE_ORDER = [State.SUSPICIOUS, State.TO_CHECK, State.CONSISTENT, State.UNVERIFIABLE]
_PREVIEW_SIZE = 640


def tool_versions() -> dict[str, str]:
    major, minor = exiftool_version()
    return {"talax": version("talax"), "exiftool": f"{major}.{minor:02d}"}


def to_dict(analysis: Analysis, file_name: str | None = None) -> dict[str, Any]:
    """Stable, JSON-ready view of an analysis. Bump SCHEMA_VERSION on changes."""
    integrity = analysis.integrity
    return {
        "schema": SCHEMA_VERSION,
        "tools": tool_versions(),
        "created_at": analysis.created_at.isoformat(),
        "file": {
            "name": file_name,
            "sha256": analysis.file.sha256,
            "size": analysis.file.size,
            "declared_format": analysis.file.declared_format,
            "real_format": analysis.file.real_format,
        },
        "integrity": {
            "verdict": str(integrity.verdict),
            "pipeline": integrity.pipeline,
            "explanation": integrity.explanation,
            "evidence": _plain(integrity.evidence),
        },
        "results": [
            {
                "signal": r.signal_id,
                "state": str(r.state),
                "explanation": r.explanation,
                "evidence": _plain(r.evidence),
                "confidence": r.confidence,
            }
            for r in analysis.results
        ],
        "disclaimer": DISCLAIMER,
    }


def render_html(analysis: Analysis, source: Path | None = None) -> str:
    env = Environment(
        loader=PackageLoader("talax", "templates"),
        autoescape=select_autoescape(["html", "j2"], default=True),
    )
    data = to_dict(analysis, source.name if source else None)
    results = sorted(analysis.results, key=lambda r: _STATE_ORDER.index(r.state))
    return env.get_template("report.html.j2").render(
        data=data,
        results=results,
        state_labels=STATE_LABELS,
        verdict_label=VERDICT_LABELS[analysis.integrity.verdict],
        verdict=str(analysis.integrity.verdict),
        position=_position(analysis),
        previews=_previews(source) if source else None,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )


def _position(analysis: Analysis) -> dict[str, float] | None:
    for r in analysis.results:
        if r.signal_id == "gps" and r.state is State.CONSISTENT:
            lat, lon = r.evidence.get("latitude"), r.evidence.get("longitude")
            if isinstance(lat, int | float) and isinstance(lon, int | float):
                return {"lat": float(lat), "lon": float(lon)}
    return None


def _previews(source: Path) -> dict[str, str | None] | None:
    """The image and its embedded preview, side by side, both upright."""
    try:
        with Image.open(source) as im:
            orientation = im.getexif().get(0x0112, 1)
            im.draft("RGB", (_PREVIEW_SIZE * 2, _PREVIEW_SIZE * 2))
            main = ImageOps.exif_transpose(im.convert("RGB"))
            main.thumbnail((_PREVIEW_SIZE, _PREVIEW_SIZE))
            main_uri = _data_uri(main)
    except (OSError, ValueError):
        return None
    thumb_uri = None
    raw = read_thumbnail(source)
    if raw:
        try:
            with Image.open(io.BytesIO(raw)) as th:
                thumb = _orient(th.convert("RGB"), orientation)
                thumb_uri = _data_uri(thumb)
        except (OSError, ValueError):
            thumb_uri = None
    return {"image": main_uri, "thumbnail": thumb_uri}


_TRANSPOSE = {
    2: [Image.Transpose.FLIP_LEFT_RIGHT],
    3: [Image.Transpose.ROTATE_180],
    4: [Image.Transpose.FLIP_TOP_BOTTOM],
    5: [Image.Transpose.TRANSPOSE],
    6: [Image.Transpose.ROTATE_270],
    7: [Image.Transpose.TRANSVERSE],
    8: [Image.Transpose.ROTATE_90],
}


def _orient(image: Image.Image, orientation: object) -> Image.Image:
    for op in _TRANSPOSE.get(orientation if isinstance(orientation, int) else 1, []):
        image = image.transpose(op)
    return image


def _data_uri(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
