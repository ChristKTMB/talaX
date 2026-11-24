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


# --- same picture ----------------------------------------------------------


def scene(path: Path, size: tuple[int, int] = (640, 480), quality: int = 95) -> Path:
    """A synthetic picture with enough detail to fingerprint."""
    from PIL import ImageDraw

    im = Image.new("RGB", (640, 480), (30, 90, 40))
    draw = ImageDraw.Draw(im)
    for i in range(30):
        x, y = (i * 97) % 600, (i * 53) % 440
        draw.ellipse(
            (x, y, x + 20 + i * 2, y + 15 + i), fill=(i * 8, 255 - i * 7, i * 5)
        )
    im.resize(size).save(path, quality=quality)
    return path


def other(path: Path) -> Path:
    from PIL import ImageDraw

    im = Image.new("RGB", (640, 480), (200, 200, 230))
    ImageDraw.Draw(im).line((0, 0, 640, 480), fill=(0, 0, 0), width=30)
    im.save(path)
    return path


def test_groups_copies_and_keeps_others_apart(tmp_path: Path) -> None:
    import shutil as sh

    scene(tmp_path / "a.jpg")
    sh.copy(tmp_path / "a.jpg", tmp_path / "a-again.jpg")
    scene(tmp_path / "a-small.jpg", size=(320, 240), quality=60)
    Image.open(tmp_path / "a.jpg").rotate(90, expand=True).save(
        tmp_path / "a-turned.jpg"
    )
    other(tmp_path / "b.jpg")

    groups = analyze_batch([tmp_path]).groups
    kinds = {g.kind: g for g in groups}
    assert kinds["identical"].names == (
        f"{tmp_path.name}/a-again.jpg",
        f"{tmp_path.name}/a.jpg",
    )
    same = kinds["same_image"]
    assert [n.split("/")[1] for n in same.names] == [
        "a-again.jpg",
        "a-small.jpg",
        "a-turned.jpg",
        "a.jpg",
    ]
    assert same.distance <= 16 and same.bits == 256
    assert all("b.jpg" not in g.names[0] and "b.jpg" not in g.names for g in groups)
    assert [g.kind for g in groups] == ["identical", "same_image"]


def test_an_edited_copy_is_only_very_close(tmp_path: Path) -> None:
    from PIL import ImageDraw

    scene(tmp_path / "a.jpg")
    edited = Image.open(tmp_path / "a.jpg")
    ImageDraw.Draw(edited).rectangle((0, 0, 640, 100), fill=(30, 90, 40))
    edited.save(tmp_path / "a-edited.jpg")
    (group,) = analyze_batch([tmp_path]).groups
    assert group.kind == "similar"
    assert 16 < group.distance <= 48


def test_no_group_for_different_pictures(tmp_path: Path) -> None:
    scene(tmp_path / "a.jpg")
    other(tmp_path / "b.jpg")
    batch = analyze_batch([tmp_path])
    assert batch.groups == ()
    out = runner.invoke(app, ["batch", str(tmp_path)], env={"COLUMNS": "200"}).output
    assert "No two files show the same picture." in out
    assert "A cropped copy is usually not found." in out


def test_groups_in_the_terminal(tmp_path: Path) -> None:
    scene(tmp_path / "a.jpg")
    scene(tmp_path / "a-small.jpg", size=(320, 240), quality=60)
    out = runner.invoke(
        app, ["batch", str(tmp_path), "--lang", "fr"], env={"COLUMNS": "200"}
    ).output
    assert "Même image (" in out and "bits sur 256 diffèrent" in out
    assert "à vérifier à l'œil" in out


# --- timeline and places -----------------------------------------------------

PARIS = [
    "-GPSLatitude=48.8566",
    "-GPSLatitudeRef=N",
    "-GPSLongitude=2.3522",
    "-GPSLongitudeRef=E",
]
KINSHASA = [
    "-GPSLatitude=4.3217",
    "-GPSLatitudeRef=S",
    "-GPSLongitude=15.3125",
    "-GPSLongitudeRef=E",
]


def taken(stamp: str, *more: str) -> list[str]:
    return [f"-ExifIFD:DateTimeOriginal={stamp}", *more]


def test_timeline_in_real_time_across_time_zones(tmp_path: Path) -> None:
    from talax.batch import span, timeline

    # 13:00 in Paris (UTC+2 in June) is 11:00 UTC; 12:30 in Kinshasa (UTC+1)
    # is 11:30 UTC: Paris comes first, though its clock shows a later time.
    jpeg(tmp_path / "kin.jpg", *taken("2025:06:21 12:30:00", *KINSHASA))
    jpeg(
        tmp_path / "par.jpg",
        *taken("2025:06:21 13:00:00", "-ExifIFD:OffsetTimeOriginal=+02:00"),
    )
    jpeg(tmp_path / "none.jpg")
    moments, undated = timeline(analyze_batch([tmp_path]))
    assert [m.name.split("/")[1] for m in moments] == ["par.jpg", "kin.jpg"]
    assert [m.offset for m in moments] == ["+02:00", "+01:00"]  # Kinshasa from its GPS
    assert undated == [f"{tmp_path.name}/none.jpg"]
    assert span(moments) is not None and span(moments).total_seconds() == 30 * 60  # type: ignore[union-attr]


def test_an_unknown_time_zone_orders_by_device_time(tmp_path: Path) -> None:
    from talax.batch import timeline

    jpeg(
        tmp_path / "a.jpg",
        *taken("2025:06:21 13:50:00", "-ExifIFD:OffsetTimeOriginal=+02:00"),
    )
    jpeg(tmp_path / "b.jpg", *taken("2025:06:21 15:00:00"))
    jpeg(
        tmp_path / "c.jpg",
        *taken("2025:06:21 16:05:00", "-ExifIFD:OffsetTimeOriginal=+02:00"),
    )
    moments, _ = timeline(analyze_batch([tmp_path]))
    assert [m.name[-5:] for m in moments] == ["a.jpg", "b.jpg", "c.jpg"]
    assert moments[1].utc is None


def test_places_and_the_widest_distance(tmp_path: Path) -> None:
    from talax.batch import places

    jpeg(tmp_path / "p.jpg", *PARIS)
    jpeg(tmp_path / "k.jpg", *KINSHASA)
    jpeg(tmp_path / "n.jpg")
    found, missing, widest = places(analyze_batch([tmp_path]))
    assert {p.name[-5:] for p in found} == {"p.jpg", "k.jpg"}
    assert missing == [f"{tmp_path.name}/n.jpg"]
    assert widest is not None and widest.km == pytest.approx(6040, rel=0.02)


def test_timeline_and_places_in_the_terminal(tmp_path: Path) -> None:
    jpeg(tmp_path / "p.jpg", *taken("2025:06:21 13:50:00", *PARIS))
    jpeg(tmp_path / "q.jpg", *taken("2025:06:21 14:20:00", *PARIS))
    out = runner.invoke(
        app, ["batch", str(tmp_path), "--lang", "fr"], env={"COLUMNS": "200"}
    ).output
    assert "Chronologie" in out and "(UTC+02:00)" in out
    assert "De la première à la dernière photo : 30 min." in out
    assert "dont l'horloge peut être mal réglée" in out
    assert "Lieux" in out and "48.85660, 2.35220" in out
    assert "Plus grande distance entre deux photos : 0 km" in out
