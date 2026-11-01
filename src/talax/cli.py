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
from talax.model import Analysis, Observation, Sky, State
from talax.report import DISCLAIMER, STATE_LABELS, VERDICT_LABELS, render_html, to_dict

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
) -> None:
    """Analyse one file. Nothing is sent over the network."""
    try:
        analysis = analyze(file, observation=Observation(sky) if sky else None)
    except (OSError, ExifToolError) as exc:
        err.print(_safe(f"error: {exc}"), style="red")
        raise typer.Exit(1) from exc

    if html is not None:
        html.write_text(render_html(analysis, file), encoding="utf-8")

    if json_output:
        print(json.dumps(to_dict(analysis, file.name), indent=2))
    else:
        _print_text(analysis, file, sky is not None)
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


def _print_text(analysis: Analysis, file: Path, sky_given: bool) -> None:
    if sys.stdout.isatty():
        out.print(BANNER, highlight=False, markup=False)
    f = analysis.file
    out.print(
        _safe(f"{file.name}  {f.size:,} bytes  {f.real_format or ''}"), style="bold"
    )
    out.print(_safe(f"SHA-256 {f.sha256}"), style="dim")
    out.print()
    verdict = VERDICT_LABELS[analysis.integrity.verdict]
    out.print(_safe(f"Integrity: {verdict}"), style="bold")
    out.print(_safe(analysis.integrity.explanation))
    out.print()

    table = Table(box=None, show_header=False, padding=(0, 1, 1, 0), expand=True)
    table.add_column(no_wrap=True)
    table.add_column(ratio=1)
    for r in analysis.results:
        body = _safe(r.signal_id)
        body.stylize("bold")
        body.append("\n")
        body.append_text(_safe(r.explanation))
        table.add_row(Text(STATE_LABELS[r.state], style=_STYLES[r.state]), body)
    out.print(table)

    if not sky_given and any(
        r.signal_id == "solar" and "sun was" in r.explanation for r in analysis.results
    ):
        out.print(
            "Tip: add --sky day|twilight|night to check the sun against the photo.",
            style="cyan",
            markup=False,
        )
    out.print(_safe(DISCLAIMER), style="dim")
