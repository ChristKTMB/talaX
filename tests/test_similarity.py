from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from talax.model import VisualHash
from talax.similarity import distance, visual_hash


def picture(path: Path) -> Path:
    im = Image.new("RGB", (400, 300), (10, 10, 10))
    draw = ImageDraw.Draw(im)
    for i in range(20):
        draw.rectangle(
            (i * 19, i * 13, i * 19 + 40, i * 13 + 25), fill=(250 - i * 9, i * 12, 128)
        )
    im.save(path, quality=95)
    return path


def test_a_copy_is_close_and_a_rotation_is_found(tmp_path: Path) -> None:
    original = visual_hash(picture(tmp_path / "a.jpg"))
    Image.open(tmp_path / "a.jpg").resize((200, 150)).save(
        tmp_path / "s.jpg", quality=50
    )
    Image.open(tmp_path / "a.jpg").rotate(270, expand=True).save(tmp_path / "r.jpg")
    assert original is not None
    assert distance(original, visual_hash(tmp_path / "s.jpg")) <= 16  # type: ignore[arg-type]
    assert distance(original, visual_hash(tmp_path / "r.jpg")) <= 16  # type: ignore[arg-type]


def test_the_exif_orientation_is_applied(tmp_path: Path) -> None:
    upright = visual_hash(picture(tmp_path / "a.jpg"))
    turned = Image.open(tmp_path / "a.jpg").rotate(90, expand=True)
    exif = turned.getexif()
    exif[0x0112] = 6  # the viewer turns it back a quarter clockwise
    turned.save(tmp_path / "t.jpg", exif=exif, quality=95)
    hashed = visual_hash(tmp_path / "t.jpg")
    assert upright is not None and hashed is not None
    assert bin(upright.turns[0] ^ hashed.turns[0]).count("1") <= 16


def test_unreadable_files_have_no_hash(tmp_path: Path) -> None:
    (tmp_path / "x.jpg").write_bytes(b"\xff\xd8\xff nothing")
    assert visual_hash(tmp_path / "x.jpg") is None


def test_sizes_must_match() -> None:
    with pytest.raises(ValueError):
        distance(VisualHash((0, 0, 0, 0), 8), VisualHash((0, 0, 0, 0), 16))
