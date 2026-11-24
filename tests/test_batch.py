import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

import talax.batch
from talax import Batch, State, analyze_batch
from talax.batch import collect, concerns
from talax.cli import app
from talax.extraction import ExifToolError

pytestmark = pytest.mark.skipif(
    shutil.which("exiftool") is None, reason="ExifTool needed"
)
runner = CliRunner()


def jpeg(path: Path, *exif: str) -> Path:
    Image.new("RGB", (64, 48), (120, 160, 200)).save(path, quality=90)
    if exif:
        subprocess.run(
            ["exiftool", "-q", "-overwrite_original", *exif, path], check=True
        )
    return path


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    root = tmp_path / "lot"
    (root / "inner").mkdir(parents=True)
    jpeg(root / "b.jpg")
    jpeg(root / "a.jpg")
    jpeg(root / "inner" / "deep.jpg")  # subfolders are not entered
    jpeg(root / ".hidden.jpg")
    (root / "notes.txt").write_text("not a photo")
    (root / "photo.jpg").write_bytes(b"not a photo either")
    return root


def test_collect_keeps_recognised_files_by_their_bytes(folder: Path) -> None:
    kept, skipped = collect([folder])
    assert [name for name, _ in kept] == ["lot/a.jpg", "lot/b.jpg"]
    assert skipped == ["lot/notes.txt", "lot/photo.jpg"]


def test_files_and_folders_together(folder: Path) -> None:
    kept, _ = collect([folder / "inner" / "deep.jpg", folder])
    assert [name for name, _ in kept] == ["deep.jpg", "lot/a.jpg", "lot/b.jpg"]


def test_every_file_is_analysed_as_on_its_own(folder: Path) -> None:
    batch = analyze_batch([folder])
    assert isinstance(batch, Batch)
    assert [item.name for item in batch.items] == ["lot/a.jpg", "lot/b.jpg"]
    assert all(item.analysis is not None and item.error is None for item in batch.items)
    assert batch.skipped == ("lot/notes.txt", "lot/photo.jpg")


def test_an_unreadable_file_never_stops_the_others(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = talax.batch.analyze  # type: ignore[attr-defined]

    def failing(path: Path) -> object:
        if path.name == "a.jpg":
            raise ExifToolError("broken")
        return real(path)

    monkeypatch.setattr(talax.batch, "analyze", failing)
    a, b = analyze_batch([folder]).items
    assert a.analysis is None and a.error == "unreadable"
    assert b.analysis is not None


def test_concerns_put_suspicious_first(tmp_path: Path) -> None:
    # The manufacturer's clock disagrees with the capture time: suspicious.
    path = jpeg(
        tmp_path / "x.jpg",
        "-IFD0:Software=Adobe Photoshop 25.0",
        "-ExifIFD:DateTimeOriginal=2026:01:01 10:00:00",
    )
    analysis = analyze_batch([path]).items[0].analysis
    assert analysis is not None
    found = concerns(analysis)
    assert ("software", State.TO_CHECK) in found
    states = [state for _, state in found]
    assert states == sorted(states, key=[State.SUSPICIOUS, State.TO_CHECK].index)


def test_batch_needs_an_aware_time() -> None:
    with pytest.raises(ValueError):
        Batch(items=(), skipped=(), created_at=datetime(2026, 1, 1))


def test_batch_command(folder: Path) -> None:
    jpeg(folder / "edited.jpg", "-IFD0:Software=Adobe Photoshop 25.0")
    out = runner.invoke(
        app, ["batch", str(folder), "--lang", "fr"], env={"COLUMNS": "200"}
    ).output
    assert "lot/edited.jpg" in out and "Logiciel de retouche" in out
    assert "3 fichiers analysés sur 3" in out
    assert "lot/notes.txt" in out and "lot/photo.jpg" in out
    assert "ne certifie jamais" in out


def test_batch_names_are_shown_without_control_codes(tmp_path: Path) -> None:
    jpeg(tmp_path / "evil\x1b[2J.jpg")
    out = runner.invoke(app, ["batch", str(tmp_path)]).output
    assert "\x1b[2J" not in out
