"""Command-line interface: a thin adapter over the analysis core."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from talax.analysis import analyze
from talax.extraction import ExifToolError
from talax.i18n import Language, default_language, text
from talax.model import (
    Analysis,
    Batch,
    Conditions,
    Declaration,
    Observation,
    Sky,
    State,
)
from talax.report import (
    render_html,
    reverse_search,
    signal_name,
    source_request,
    state_label,
    to_dict,
    verdict_label,
)

BANNER = r"""
 _____         _           __  __
|_   _|  __ _ | |  __ _    \ \/ /
  | |   / _` || | / _` |    \  /
  | |  | (_| || || (_| |    /  \
  |_|   \__,_||_| \__,_|   /_/\_\

      See beyond the pixel
"""

_CONTROL = re.compile(r"[\x00-\x09\x0b-\x1f\x7f-\x9f]")

_STYLES = {
    State.CONSISTENT: "green",
    State.TO_CHECK: "yellow",
    State.SUSPICIOUS: "bold red",
    State.UNVERIFIABLE: "dim",
}

app = typer.Typer(
    help="Tala X: what can honestly be said about an image.",
    add_completion=False,
)
out = Console()
err = Console(stderr=True)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Tala X: what can honestly be said about an image."""
    if ctx.invoked_subcommand is None:
        if sys.stdout.isatty():
            out.print(BANNER, highlight=False, markup=False)
        typer.echo(ctx.get_help())


@app.command(name="analyze")
def analyze_command(
    file: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, readable=True, help="Image file."),
    ],
    sky: Annotated[
        Sky | None,
        typer.Option(help="What the photo shows, for the solar check."),
    ] = None,
    weather: Annotated[
        bool,
        typer.Option(
            "--weather",
            help=(
                "Look up the weather at the photo's place and time on Open-Meteo. "
                "Sends a position rounded to about 11 km and the date; "
                "Open-Meteo may keep them 90 days."
            ),
        ),
    ] = False,
    conditions: Annotated[
        Conditions | None,
        typer.Option(help="The weather the photo shows, for --weather."),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print the analysis as JSON.")
    ] = False,
    html: Annotated[
        Path | None,
        typer.Option(dir_okay=False, help="Also write a self-contained HTML report."),
    ] = None,
    lang: Annotated[
        Language | None,
        typer.Option(help="Language of the report (default: the system language)."),
    ] = None,
    place: Annotated[
        str | None,
        typer.Option(
            metavar="LAT,LON",
            help="Place the caption claims, in decimal degrees (with --at).",
        ),
    ] = None,
    at: Annotated[
        str | None,
        typer.Option(
            metavar="'YYYY-MM-DD HH:MM'",
            help="Time the caption claims, local time at --place (with --place).",
        ),
    ] = None,
) -> None:
    """Analyse one file. Nothing is sent over the network, unless --weather."""
    language = lang or default_language()
    declaration = _declaration(place, at)
    try:
        analysis = analyze(
            file,
            declaration=declaration,
            observation=Observation(sky, conditions) if sky or conditions else None,
            weather=weather,
        )
    except (OSError, ExifToolError) as exc:
        err.print(_safe(f"error: {exc}"), style="red")
        raise typer.Exit(1) from exc

    if html is not None:
        report = render_html(analysis, file, language, file_name=file.name)
        html.write_text(report, encoding="utf-8")

    if json_output:
        print(json.dumps(to_dict(analysis, file.name, language), indent=2))
    else:
        _print_text(analysis, file, language)
    if html is not None:
        err.print(_safe(f"HTML report written to {html}"))


@app.command(name="batch")
def batch_command(
    paths: Annotated[
        list[Path],
        typer.Argument(exists=True, readable=True, help="Files or folders."),
    ],
    lang: Annotated[
        Language | None,
        typer.Option(help="Language of the report (default: the system language)."),
    ] = None,
    html: Annotated[
        Path | None,
        typer.Option(dir_okay=False, help="Also write a self-contained HTML report."),
    ] = None,
) -> None:
    """Analyse several files at once. Nothing is sent over the network."""
    from talax.batch import analyze_batch
    from talax.report import render_batch_html

    language = lang or default_language()
    batch = analyze_batch(paths)
    _print_batch(batch, language)
    if html is not None:
        html.write_text(render_batch_html(batch, language), encoding="utf-8")
        err.print(_safe(f"HTML report written to {html}"))


@app.command()
def version() -> None:
    """Show the versions of Tala X and ExifTool."""
    from talax.report import tool_versions

    versions = tool_versions()
    print(f"talax {versions['talax']} (ExifTool {versions['exiftool']})")


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Address to listen on.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port to listen on.")] = 8000,
) -> None:
    """Start the web API (needs `pip install talax[server]`)."""
    try:
        import uvicorn

        from talax.api.app import app as api
    except ImportError as exc:
        err.print(
            "error: the web API needs `pip install talax[server]`",
            style="red",
            markup=False,
        )
        raise typer.Exit(1) from exc
    import logging

    # Uvicorn's access log records client addresses; the API logs its own
    # requests without them.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    uvicorn.run(api, host=host, port=port, access_log=False)


def _declaration(place: str | None, at: str | None) -> Declaration | None:
    """The claimed place and time: both or neither."""
    if place is None and at is None:
        return None
    if place is None or at is None:
        raise typer.BadParameter("--place and --at go together")
    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", place)
    if not match:
        raise typer.BadParameter(
            "expected LAT,LON, e.g. -4.32,15.31", param_hint="--place"
        )
    try:
        moment = datetime.fromisoformat(at.strip())
    except ValueError as exc:
        raise typer.BadParameter(
            "expected 'YYYY-MM-DD HH:MM'", param_hint="--at"
        ) from exc
    try:
        return Declaration(float(match[1]), float(match[2]), moment)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--place") from exc


def _safe(text: str) -> Text:
    """File metadata is written by anyone: no markup, no terminal control codes."""
    return Text(_CONTROL.sub("", text))


def _print_batch(batch: Batch, lang: Language) -> None:
    from talax.batch import concerns, recorded_time

    if sys.stdout.isatty():
        out.print(BANNER, highlight=False, markup=False)
    table = Table(show_lines=False, expand=True, header_style="bold")
    for key in ("file", "integrity", "taken", "position", "concerns"):
        table.add_column(text(f"ui.batch.{key}", lang), overflow="fold")
    for item in batch.items:
        name = _safe(item.name)
        if item.analysis is None:
            table.add_row(name, Text(text("ui.batch.unreadable", lang), style="red"))
            continue
        a = item.analysis
        flags = Text()
        for signal_id, state in concerns(a):
            if flags:
                flags.append(", ")
            flags.append(signal_name(signal_id, lang), style=_STYLES[state])
        table.add_row(
            name,
            verdict_label(a.integrity.verdict, lang),
            _safe(recorded_time(a) or "-"),
            _position_text(a),
            flags or Text("-", style="dim"),
        )
    out.print(table)
    _print_duplicates(batch, lang)
    _print_timeline(batch, lang)
    _print_places(batch, lang)
    readable = sum(1 for item in batch.items if item.analysis is not None)
    out.print(
        text("ui.batch.summary", lang, analysed=readable, total=len(batch.items)),
        markup=False,
    )
    if batch.skipped:
        out.print(
            _safe(text("ui.batch.skipped", lang, names=", ".join(batch.skipped))),
            style="dim",
        )
    out.print(_safe(text("ui.disclaimer", lang)), style="dim")


def _print_duplicates(batch: Batch, lang: Language) -> None:
    out.print()
    out.print(text("ui.batch.duplicates", lang), style="bold", markup=False)
    if not batch.groups:
        out.print(text("ui.batch.no_duplicates", lang), markup=False)
    for group in batch.groups:
        label = text(
            f"ui.batch.group.{group.kind}",
            lang,
            distance=group.distance,
            bits=group.bits,
        )
        out.print(_safe(f"- {label} {', '.join(group.names)}"))
    out.print(text("ui.batch.duplicates_note", lang), style="dim", markup=False)
    out.print()


def _position_text(analysis: Analysis) -> str:
    from talax.batch import position

    found = position(analysis)
    return f"{found[0]:.5f}, {found[1]:.5f}" if found else "-"


def _print_timeline(batch: Batch, lang: Language) -> None:
    from talax.batch import span, timeline
    from talax.phrases import duration

    moments, undated = timeline(batch)
    out.print(text("ui.batch.timeline", lang), style="bold", markup=False)
    for m in moments:
        zone = f"UTC{m.offset}" if m.offset else text("ui.batch.zone_unknown", lang)
        out.print(_safe(f"  {m.local:%Y-%m-%d %H:%M}  ({zone})  {m.name}"))
    if undated:
        out.print(_safe(text("ui.batch.undated", lang, names=", ".join(undated))))
    gap = span(moments)
    if gap is not None:
        key = "ui.batch.span" if all(m.utc for m in moments) else "ui.batch.span_approx"
        out.print(text(key, lang, duration=duration(gap)), markup=False)
    out.print(text("ui.batch.timeline_note", lang), style="dim", markup=False)
    out.print()


def _print_places(batch: Batch, lang: Language) -> None:
    from talax.batch import places

    found, missing, widest = places(batch)
    out.print(text("ui.batch.places", lang), style="bold", markup=False)
    for p in found:
        out.print(_safe(f"  {p.latitude:.5f}, {p.longitude:.5f}  {p.name}"))
    if missing:
        out.print(_safe(text("ui.batch.no_position", lang, names=", ".join(missing))))
    if widest is not None:
        out.print(
            _safe(
                text(
                    "ui.batch.widest",
                    lang,
                    km=widest.km,
                    first=widest.first,
                    second=widest.second,
                )
            )
        )
    out.print()


def _print_text(analysis: Analysis, file: Path, lang: Language) -> None:
    if sys.stdout.isatty():
        out.print(BANNER, highlight=False, markup=False)
    f = analysis.file
    size = text("ui.cli.size", lang, size=f.size)
    out.print(_safe(f"{file.name}  {size}  {f.real_format or ''}"), style="bold")
    out.print(_safe(f"SHA-256 {f.sha256}"), style="dim")
    out.print()
    verdict = verdict_label(analysis.integrity.verdict, lang)
    out.print(_safe(text("ui.integrity_line", lang, verdict=verdict)), style="bold")
    out.print(_safe(analysis.integrity.explain(lang)))
    out.print()

    table = Table(box=None, show_header=False, padding=(0, 1, 1, 0), expand=True)
    table.add_column(no_wrap=True)
    table.add_column(ratio=1)
    for r in analysis.results:
        body = _safe(signal_name(r.signal_id, lang))
        body.stylize("bold")
        body.append("\n")
        body.append_text(_safe(r.explain(lang)))
        table.add_row(Text(state_label(r.state, lang), style=_STYLES[r.state]), body)
    out.print(table)

    if any(r.message.key == "solar.no_observation" for r in analysis.results):
        out.print(text("ui.cli.sky_tip", lang), style="cyan", markup=False)
    if any(r.message.key == "weather.no_observation" for r in analysis.results):
        out.print(text("ui.cli.conditions_tip", lang), style="cyan", markup=False)
    if any(
        r.signal_id == "weather" and r.evidence.get("source") for r in analysis.results
    ):
        out.print(text("ui.weather_credit", lang), style="dim", markup=False)
    if request := source_request(analysis, lang):
        out.print()
        out.print(request["title"], style="bold", markup=False)
        out.print(request["intro"], markup=False)
        out.print()
        out.print(request["message"], style="cyan", markup=False, highlight=False)
        out.print()
        out.print(request["caution"], style="yellow", markup=False)
        out.print()
    search = reverse_search(lang)
    out.print(search["title"], style="bold", markup=False)
    out.print(search["intro"], markup=False)
    for service in search["services"]:
        out.print(
            f"  {service['name']}: {service['url']}", markup=False, highlight=False
        )
    out.print(search["caution"], style="yellow", markup=False)
    out.print()
    out.print(_safe(text("ui.disclaimer", lang)), style="dim")
