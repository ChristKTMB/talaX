from pathlib import Path

import pytest

from talax.fileinfo import read_file_info, sniff_format


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        (b"\xff\xd8\xff\xe1", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n", "image/png"),
        (b"GIF89a", "image/gif"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
        (b"II*\x00", "image/tiff"),
        (b"MM\x00*", "image/tiff"),
        (b"\x00\x00\x00\x18ftypheic", "image/heic"),
        (b"\x00\x00\x00\x18ftypmif1", "image/heif"),
        (b"\x00\x00\x00\x18ftypavif", "image/avif"),
        (b"\x00\x00\x00\x14ftypqt  ", "video/quicktime"),
        (b"\x00\x00\x00\x18ftypisom", "video/mp4"),
        (b"\x00\x00\x00\x18ftypzzzz", None),
        (b"hello world", None),
        (b"", None),
    ],
)
def test_sniff_format(head: bytes, expected: str | None) -> None:
    assert sniff_format(head) == expected


def test_file_info_hashes_and_compares_name_with_content(tmp_path: Path) -> None:
    path = tmp_path / "photo.JPG"
    data = b"\x89PNG\r\n\x1a\n" + b"x" * 3_000_000  # larger than one read chunk
    path.write_bytes(data)

    info = read_file_info(path)

    import hashlib

    assert info.sha256 == hashlib.sha256(data).hexdigest()
    assert info.size == len(data)
    assert info.declared_format == "image/jpeg"
    assert info.real_format == "image/png"


def test_unknown_extension(tmp_path: Path) -> None:
    path = tmp_path / "photo"
    path.write_bytes(b"\xff\xd8\xff")
    assert read_file_info(path).declared_format is None
