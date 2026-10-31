import shutil
import struct
from pathlib import Path

import pytest

from talax.extraction import _keep_duplicates, exiftool_version, read_metadata

needs_exiftool = pytest.mark.skipif(
    shutil.which("exiftool") is None, reason="ExifTool not installed"
)


def test_duplicate_keys_are_all_kept() -> None:
    pairs = [("IFD0:Make", "samsung"), ("IFD0:Make", "Forged"), ("IFD0:Make", "x")]
    assert _keep_duplicates(pairs) == {
        "IFD0:Make": "samsung",
        "IFD0:Make#2": "Forged",
        "IFD0:Make#3": "x",
    }


@needs_exiftool
def test_version_is_supported() -> None:
    assert exiftool_version() >= (13, 0)


@needs_exiftool
def test_reads_content_tags_but_not_local_file_details(tmp_path: Path) -> None:
    # Minimal JPEG with an EXIF block holding Make = "TestCam".
    ifd = struct.pack("<HHHII", 1, 0x010F, 2, 8, 26) + b"\x00\x00\x00\x00"
    tiff = b"II*\x00" + struct.pack("<I", 8) + ifd + b"TestCam\x00"
    app1 = b"Exif\x00\x00" + tiff
    data = b"\xff\xd8\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xd9"
    path = tmp_path / "-private-name.jpg"
    path.write_bytes(data)

    metadata = read_metadata(path)

    assert metadata.get("IFD0:Make") == "TestCam"
    assert metadata.get("File:MIMEType") == "image/jpeg"
    assert "SourceFile" not in metadata.tags
    assert not any(k.startswith("System:") for k in metadata.tags)
    assert not any("private-name" in str(v) for v in metadata.tags.values())
