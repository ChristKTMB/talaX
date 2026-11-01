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
from talax.i18n import Language, catalog, text
from talax.model import Analysis, IntegrityVerdict, State

REPORT_CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'"
"""The policy of the HTML report: nothing loaded from outside."""

SCHEMA_VERSION = 2
"""2: messages carry a key (`message`) and the text in the requested `lang`."""

_STATE_ORDER = [State.SUSPICIOUS, State.TO_CHECK, State.CONSISTENT, State.UNVERIFIABLE]
_PREVIEW_SIZE = 640


def state_label(state: State, lang: Language) -> str:
    return text(f"state.{state}", lang)


def verdict_label(verdict: IntegrityVerdict, lang: Language) -> str:
    return text(f"verdict.{verdict}", lang)


def signal_name(signal_id: str, lang: Language) -> str:
    key = f"signal.{signal_id}"
    return text(key, lang) if key in catalog(lang) else signal_id


def tool_versions() -> dict[str, str]:
    major, minor = exiftool_version()
    return {"talax": version("talax"), "exiftool": f"{major}.{minor:02d}"}


def to_dict(
    analysis: Analysis, file_name: str | None = None, lang: Language = Language.EN
) -> dict[str, Any]:
    """Stable, JSON-ready view of an analysis. Bump SCHEMA_VERSION on changes."""
    integrity = analysis.integrity
    return {
        "schema": SCHEMA_VERSION,
        "lang": str(lang),
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
            "label": verdict_label(integrity.verdict, lang),
            "pipeline": integrity.pipeline,
            "message": integrity.message.key,
            "explanation": integrity.explain(lang),
            "evidence": _plain(integrity.evidence),
        },
        "results": [
            {
                "signal": r.signal_id,
                "name": signal_name(r.signal_id, lang),
                "state": str(r.state),
                "label": state_label(r.state, lang),
                "message": r.message.key,
                "explanation": r.explain(lang),
                "evidence": _plain(r.evidence),
                "confidence": r.confidence,
            }
            for r in analysis.results
        ],
        "disclaimer": text("ui.disclaimer", lang),
    }


def render_html(
    analysis: Analysis,
    source: Path | None = None,
    lang: Language = Language.EN,
    file_name: str | None = None,
) -> str:
    """`source` gives the previews; the name shown is `file_name`, never the
    path's (the web service analyses a temporary copy)."""
    env = Environment(
        loader=PackageLoader("talax", "templates"),
        autoescape=select_autoescape(["html", "j2"], default=True),
    )
    data = to_dict(analysis, file_name, lang)
    results = sorted(
        data["results"], key=lambda r: _STATE_ORDER.index(State(r["state"]))
    )
    return env.get_template("report.html.j2").render(
        data=data,
        csp=REPORT_CSP,
        results=results,
        lang=str(lang),
        t=lambda key, **params: text(key, lang, **params),
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
    except (OSError, ValueError, Image.DecompressionBombError):
        return None
    return {"image": main_uri, "thumbnail": _thumbnail(source, orientation)}


def thumbnail_uri(source: Path) -> str | None:
    """The embedded preview as a `data:` URI, upright like the image, or None."""
    try:
        with Image.open(source) as im:
            orientation = im.getexif().get(0x0112, 1)
    except (OSError, ValueError, Image.DecompressionBombError):
        orientation = 1
    return _thumbnail(source, orientation)


def _thumbnail(source: Path, orientation: object) -> str | None:
    raw = read_thumbnail(source)
    if not raw:
        return None
    try:
        with Image.open(io.BytesIO(raw)) as th:
            return _data_uri(_orient(th.convert("RGB"), orientation))
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


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
