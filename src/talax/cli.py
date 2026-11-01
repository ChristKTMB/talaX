"""Command-line interface: a thin adapter over the analysis core."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from talax.analysis import analyze
from talax.extraction import ExifToolError
from talax.i18n import Language, default_language, text
from talax.model import Analysis, Observation, Sky, State
from talax.report import render_html, signal_name, state_label, to_dict, verdict_label

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
) -> None:
    """Analyse one file. Nothing is sent over the network."""
    language = lang or default_language()
    try:
        analysis = analyze(file, observation=Observation(sky) if sky else None)
    except (OSError, ExifToolError) as exc:
        err.print(_safe(f"error: {exc}"), style="red")
        raise typer.Exit(1) from exc

    if html is not None:
        html.write_text(render_html(analysis, file, language), encoding="utf-8")

    if json_output:
        print(json.dumps(to_dict(analysis, file.name, language), indent=2))
    else:
        _print_text(analysis, file, language)
    if html is not None:
        err.print(_safe(f"HTML report written to {html}"))


@app.command()
def version() -> None:
    """Show the versions of Tala X and ExifTool."""
    from talax.report import tool_versions

    versions = tool_versions()
    print(f"talax {versions['talax']} (ExifTool {versions['exiftool']})")


def _safe(text: str) -> Text:
    """File metadata is written by anyone: no markup, no terminal control codes."""
    return Text(_CONTROL.sub("", text))


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
    out.print(_safe(text("ui.disclaimer", lang)), style="dim")
