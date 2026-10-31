"""Runs against the reference corpus. Skipped when the files are absent (CI)."""

import hashlib
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from talax import State
from talax.analysis import analyze
from talax.jpeg import read_jpeg_structure

CORPUS = Path(__file__).parent.parent / "corpus"
SHEETS = sorted((CORPUS / "sets").glob("[!_]*.yaml"))


def corpus_files() -> list[tuple[Path, dict[str, Any]]]:
    """Every existing corpus file with the truth sheet of its route."""
    found = []
    for sheet_path in SHEETS:
        sheet = yaml.safe_load(sheet_path.read_text())
        folder = CORPUS / "files" / sheet["id"]
        for name in sheet["sha256"]:
            route = re.sub(r"\d+$", "", Path(name).stem)
            path = folder / name
            if path.exists() and "excluded" not in sheet["routes"][route]:
                found.append((path, {"route": route, **sheet}))
    return found


FILES = corpus_files()
pytestmark = pytest.mark.skipif(not FILES, reason="corpus files not present")


def ids(files: list[tuple[Path, dict[str, Any]]]) -> list[str]:
    return [f"{p.parent.name}/{p.name}" for p, _ in files]


@pytest.mark.parametrize(("path", "sheet"), FILES, ids=ids(FILES))
def test_file_matches_its_truth_sheet(path: Path, sheet: dict[str, Any]) -> None:
    expected = sheet["sha256"][path.name]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


@pytest.mark.parametrize(("path", "sheet"), FILES, ids=ids(FILES))
def test_analysis_runs_and_format_is_consistent(
    path: Path, sheet: dict[str, Any]
) -> None:
    analysis = analyze(path)
    (result,) = (r for r in analysis.results if r.signal_id == "real_format")
    assert result.state is State.CONSISTENT
    read_jpeg_structure(path)  # every corpus file so far is a readable JPEG


@pytest.mark.parametrize(("path", "sheet"), FILES, ids=ids(FILES))
def test_integrity_matches_the_truth(path: Path, sheet: dict[str, Any]) -> None:
    truth = sheet["routes"][sheet["route"]]
    integrity = analyze(path).integrity
    assert integrity.verdict == truth["expected_integrity"], integrity.explanation
    assert integrity.pipeline == truth.get("expected_pipeline")
