"""Runs against the reference corpus. Skipped when the files are absent (CI)."""

import hashlib
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from talax import Analysis, Observation, Sky, State
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
    if truth.get("expected_integrity") is None:
        pytest.skip("integrity not evaluated for this route")
    integrity = analyze(path).integrity
    assert integrity.verdict == truth["expected_integrity"], integrity.explanation
    assert integrity.pipeline == truth.get("expected_pipeline")


@pytest.mark.parametrize(("path", "sheet"), FILES, ids=ids(FILES))
def test_no_signal_is_suspicious_on_unmanipulated_files(
    path: Path, sheet: dict[str, Any]
) -> None:
    if sheet["id"].startswith("c2pa-"):
        pytest.skip("C2PA test files are manipulated on purpose")
    # No corpus file so far had its metadata manipulated: any SUSPICIOUS
    # verdict here is a false positive.
    suspicious = [r for r in analyze(path).results if r.state is State.SUSPICIOUS]
    assert not suspicious, suspicious[0].explanation


@pytest.mark.skipif(shutil.which("exiftool") is None, reason="ExifTool needed")
def test_backdated_original_is_caught(tmp_path: Path) -> None:
    source = CORPUS / "files" / "2026-10-31-a34" / "original2.jpg"
    if not source.exists():
        pytest.skip("corpus file missing")
    forged = tmp_path / "forged.jpg"
    subprocess.run(
        [
            "exiftool",
            "-q",
            "-DateTimeOriginal=2025:06:01 21:00:00",
            "-o",
            forged,
            source,
        ],
        check=True,
    )
    (result,) = (r for r in analyze(forged).results if r.signal_id == "capture_time")
    assert result.state is State.SUSPICIOUS


@pytest.mark.parametrize(("path", "sheet"), FILES, ids=ids(FILES))
def test_c2pa_matches_the_truth(path: Path, sheet: dict[str, Any]) -> None:
    truth = sheet["routes"][sheet["route"]]
    if "expected_c2pa" not in truth:
        pytest.skip("no C2PA expectation for this route")
    (result,) = (r for r in analyze(path).results if r.signal_id == "c2pa")
    assert result.state == truth["expected_c2pa"], result.explanation


def outdoor_with_gps() -> list[tuple[Path, dict[str, Any]]]:
    return [
        (p, s)
        for p, s in FILES
        if s["id"] == "2026-10-31-a34"
        and s["route"] == "original"
        and s["shots"][int(p.stem.removeprefix("original"))].get("location")
        == "outdoor"
    ]


OUTDOOR = outdoor_with_gps()


@pytest.mark.parametrize(("path", "sheet"), OUTDOOR, ids=ids(OUTDOOR))
def test_outdoor_daytime_photos_fit_the_sun(path: Path, sheet: dict[str, Any]) -> None:
    day = analyze(path, observation=Observation(Sky.DAY))
    night = analyze(path, observation=Observation(Sky.NIGHT))

    def solar(analysis: Analysis) -> State:
        return next(r.state for r in analysis.results if r.signal_id == "solar")

    assert solar(day) is State.CONSISTENT
    assert solar(night) is State.SUSPICIOUS


@pytest.mark.parametrize(("path", "sheet"), FILES, ids=ids(FILES))
def test_time_zone_never_contradicts_on_the_corpus(
    path: Path, sheet: dict[str, Any]
) -> None:
    if sheet["id"].startswith("c2pa-"):
        pytest.skip("third-party samples")
    (result,) = (r for r in analyze(path).results if r.signal_id == "time_zone")
    assert result.state is not State.TO_CHECK, result.explanation
