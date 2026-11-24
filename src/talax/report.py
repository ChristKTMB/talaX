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
from talax.model import Analysis, Batch, IntegrityVerdict, State

REPORT_CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'"
"""The policy of the HTML report: nothing loaded from outside."""

SCHEMA_VERSION = 2
"""2: messages carry a key (`message`) and the text in the requested `lang`.

Adding a field keeps the number; removing, renaming or changing one bumps it.
"""

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
    """Stable, JSON-ready view of an analysis (see SCHEMA_VERSION)."""
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
        "source_request": source_request(analysis, lang),
        "reverse_search": reverse_search(lang),
    }


WEATHER_ATTRIBUTION_URL = "https://open-meteo.com/"
"""Open-Meteo's licence (CC BY 4.0) asks for this link next to its data."""

REVERSE_SEARCH = (
    ("Google Lens", "https://lens.google.com/"),
    ("TinEye", "https://tineye.com/"),
    ("Yandex", "https://yandex.com/images/"),
)
"""Upload pages only: Tala X never sends the photo to them."""


def reverse_search(lang: Language) -> dict[str, Any]:
    """Where to look for earlier copies, the user uploading the photo themselves.

    Shown for every file: a camera original can be old and recycled too.
    """
    return {
        "title": text("reverse.title", lang),
        "intro": text("reverse.intro", lang),
        "caution": text("reverse.caution", lang),
        "services": [{"name": name, "url": url} for name, url in REVERSE_SEARCH],
    }


def source_request(analysis: Analysis, lang: Language) -> dict[str, str] | None:
    """What to ask the source for, unless the file already is a camera original.

    A platform copy or an undetermined file is not a failure: the next step is
    to get the original, sent in a way that keeps it intact.
    """
    if analysis.integrity.verdict is IntegrityVerdict.ORIGINAL:
        return None
    return {
        key: text(f"source.{key}", lang)
        for key in ("title", "intro", "message", "caution")
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
        analysed_at=readable_date(analysis.created_at, lang),
        weather_url=WEATHER_ATTRIBUTION_URL,
        generated_at=readable_date(datetime.now(UTC), lang),
    )


def readable_date(moment: datetime, lang: Language) -> str:
    """A date a reader can take in at once: "19 November 2026, 12:58 UTC"."""
    utc = moment.astimezone(UTC)
    months = text("ui.report.months", lang).split(",")
    return text(
        "ui.report.date",
        lang,
        day=str(utc.day),
        month=months[utc.month - 1],
        year=str(utc.year),
        time=utc.strftime("%H:%M"),
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


def render_batch_html(batch: Batch, lang: Language = Language.EN) -> str:
    """The report of a batch: one self-contained page, no image inside (a
    batch of photos would weigh hundreds of megabytes), nothing loaded."""
    from talax.batch import concerns, places, position, recorded_time, span, timeline
    from talax.phrases import duration

    env = Environment(
        loader=PackageLoader("talax", "templates"),
        autoescape=select_autoescape(["html", "j2"], default=True),
    )
    rows = []
    for item in batch.items:
        a = item.analysis
        data = to_dict(a, item.name, lang) if a else None
        rows.append(
            {
                "name": item.name,
                "data": data,
                "taken": recorded_time(a) if a else None,
                "position": position(a) if a else None,
                "concerns": [
                    {"name": signal_name(sid, lang), "state": str(state)}
                    for sid, state in concerns(a)
                ]
                if a
                else [],
                "results": sorted(
                    data["results"], key=lambda r: _STATE_ORDER.index(State(r["state"]))
                )
                if data
                else [],
            }
        )
    moments, undated = timeline(batch)
    gap = span(moments)
    span_text = None
    if gap is not None:
        key = "ui.batch.span" if all(m.utc for m in moments) else "ui.batch.span_approx"
        span_text = text(key, lang, duration=duration(gap))
    found, missing, widest = places(batch)
    return env.get_template("batch.html.j2").render(
        csp=REPORT_CSP,
        lang=str(lang),
        t=lambda key, **params: text(key, lang, **params),
        rows=rows,
        analysed=sum(1 for item in batch.items if item.analysis),
        skipped=batch.skipped,
        groups=batch.groups,
        moments=moments,
        undated=undated,
        span_text=span_text,
        found=found,
        missing=missing,
        widest=widest,
        tools=tool_versions(),
        analysed_at=readable_date(batch.created_at, lang),
        generated_at=readable_date(datetime.now(UTC), lang),
    )


def batch_to_dict(batch: Batch, lang: Language = Language.EN) -> dict[str, Any]:
    """JSON-ready view of a batch (`kind: batch`), each file in the same form
    as `to_dict`. Same schema rule: adding a field keeps the number."""
    from talax.batch import places, span, timeline

    moments, undated = timeline(batch)
    found, missing, widest = places(batch)
    gap = span(moments)
    return {
        "schema": SCHEMA_VERSION,
        "kind": "batch",
        "lang": str(lang),
        "tools": tool_versions(),
        "created_at": batch.created_at.isoformat(),
        "files": [
            {
                "name": item.name,
                "error": item.error,
                "analysis": to_dict(item.analysis, item.name, lang)
                if item.analysis
                else None,
            }
            for item in batch.items
        ],
        "skipped": list(batch.skipped),
        "same_picture": [
            {
                "kind": g.kind,
                "files": list(g.names),
                "distance_bits": g.distance,
                "of_bits": g.bits,
            }
            for g in batch.groups
        ],
        "timeline": {
            "ordered_by": "utc" if all(m.utc for m in moments) else "device_time",
            "files": [
                {
                    "name": m.name,
                    "device_time": m.local.isoformat(),
                    "offset": m.offset,
                    "utc": m.utc.isoformat() if m.utc else None,
                }
                for m in moments
            ],
            "undated": undated,
            "span_seconds": gap.total_seconds() if gap is not None else None,
        },
        "places": {
            "files": [
                {"name": p.name, "latitude": p.latitude, "longitude": p.longitude}
                for p in found
            ],
            "no_position": missing,
            "widest": {
                "first": widest.first,
                "second": widest.second,
                "km": round(widest.km, 1),
            }
            if widest
            else None,
        },
        "disclaimer": text("ui.disclaimer", lang),
    }


# A cell starting with one of these is run as a formula by spreadsheets: a
# file name or a metadata value could carry one ("=HYPERLINK(...)").
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def write_batch_csv(batch: Batch, path: Path, lang: Language = Language.EN) -> None:
    """One row per file, one column per check, written over `path`.

    Standard CSV (comma, decimal point), UTF-8 with a byte order mark so that
    spreadsheets read accents. Text cells that could run as a formula are
    prefixed with an apostrophe; numbers are written as numbers.
    """
    import csv

    from talax.batch import position, recorded_time, timeline
    from talax.signals import DEFAULT_SIGNALS

    offsets = {m.name: m.offset for m in timeline(batch)[0]}
    groups: dict[str, list[str]] = {}
    for number, group in enumerate(batch.groups, start=1):
        for name in group.names:
            groups.setdefault(name, []).append(str(number))
    present = {
        r.signal_id for i in batch.items if i.analysis for r in i.analysis.results
    }
    signal_ids = [s.id for s in DEFAULT_SIGNALS if s.id in present]
    header = [
        text("ui.batch.file", lang),
        text("ui.batch.integrity", lang),
        text("ui.batch.fingerprint", lang),
        text("ui.batch.taken", lang),
        text("ui.batch.offset", lang),
        text("ui.batch.latitude", lang),
        text("ui.batch.longitude", lang),
        text("ui.batch.group_column", lang),
        *(signal_name(sid, lang) for sid in signal_ids),
        text("ui.batch.error", lang),
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([_cell(h) for h in header])
        for item in batch.items:
            a = item.analysis
            if a is None:
                row: list[object] = [item.name, *[""] * (len(header) - 2)]
                row.append(text("ui.batch.unreadable", lang))
                writer.writerow([_cell(v) for v in row])
                continue
            states = {r.signal_id: state_label(r.state, lang) for r in a.results}
            where = position(a)
            row = [
                item.name,
                verdict_label(a.integrity.verdict, lang),
                a.integrity.pipeline or "",
                recorded_time(a) or "",
                f"UTC{offsets[item.name]}" if offsets.get(item.name) else "",
                where[0] if where else "",
                where[1] if where else "",
                ", ".join(groups.get(item.name, [])),
                *(states.get(sid, "") for sid in signal_ids),
                "",
            ]
            writer.writerow([_cell(v) for v in row])


def _cell(value: object) -> object:
    if isinstance(value, str) and value.startswith(_FORMULA_START):
        return "'" + value
    return value
