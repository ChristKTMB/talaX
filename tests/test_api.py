import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from talax.extraction import ExifToolError

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from talax.api import app as api_module

pytestmark = pytest.mark.skipif(
    shutil.which("exiftool") is None, reason="ExifTool needed"
)


@pytest.fixture
def tmpdir_for_uploads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Where the API writes uploads, so each test can check it is left empty."""
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(uploads))
    return uploads


@pytest.fixture
def client(tmpdir_for_uploads: Path) -> Iterator[TestClient]:
    with TestClient(api_module.app) as c:
        yield c


@pytest.fixture
def jpeg(tmp_path: Path) -> bytes:
    path = tmp_path / "plain.jpg"
    Image.new("RGB", (64, 48), (120, 160, 200)).save(path, quality=90)
    return path.read_bytes()


@pytest.fixture
def paris_noon(tmp_path: Path) -> bytes:
    """Paris, 21 June at noon local time: the sun is high."""
    path = tmp_path / "paris.jpg"
    Image.new("RGB", (64, 48)).save(path)
    subprocess.run(
        [
            "exiftool",
            "-q",
            "-overwrite_original",
            "-ExifIFD:DateTimeOriginal=2025:06:21 13:50:00",
            "-ExifIFD:OffsetTimeOriginal=+02:00",
            "-GPSLatitude=48.8566",
            "-GPSLatitudeRef=N",
            "-GPSLongitude=2.3522",
            "-GPSLongitudeRef=E",
            path,
        ],
        check=True,
    )
    return path.read_bytes()


def post(client: TestClient, name: str, content: bytes, **form: str) -> Any:
    return client.post("/api/analyze", files={"file": (name, content)}, data=form)


def signal(data: dict[str, Any], signal_id: str) -> dict[str, Any]:
    result: dict[str, Any] = next(
        r for r in data["results"] if r["signal"] == signal_id
    )
    return result


def test_health_gives_schema_and_tool_versions(client: TestClient) -> None:
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["schema"] == 2
    assert set(data["tools"]) == {"talax", "exiftool"}


def test_analysis_is_the_cli_json_without_the_file_name(
    client: TestClient, jpeg: bytes, tmpdir_for_uploads: Path
) -> None:
    response = post(client, "holiday.jpg", jpeg)
    assert response.status_code == 200
    data = response.json()
    assert data["schema"] == 2
    assert data["lang"] == "en"
    assert data["file"]["name"] is None
    assert data["file"]["size"] == len(jpeg)
    assert data["file"]["real_format"] == "image/jpeg"
    assert data["thumbnail"] is None
    assert {r["signal"] for r in data["results"]} >= {"gps", "solar", "c2pa"}
    assert "holiday" not in response.text
    assert list(tmpdir_for_uploads.iterdir()) == []


def test_extension_sets_the_declared_format(client: TestClient, jpeg: bytes) -> None:
    data = post(client, "photo.PNG", jpeg).json()
    assert data["file"]["declared_format"] == "image/png"
    assert signal(data, "real_format")["state"] != "consistent"


@pytest.mark.parametrize(
    ("name", "declared"),
    [
        ("../../etc/photo.jpg", "image/jpeg"),
        ("C:\\Users\\me\\photo.jpeg", "image/jpeg"),
        ("photo.jp g;rm -rf", None),
        ("photo", None),
    ],
)
def test_only_a_clean_extension_is_kept(
    client: TestClient, jpeg: bytes, name: str, declared: str | None
) -> None:
    response = post(client, name, jpeg)
    assert response.status_code == 200
    assert response.json()["file"]["declared_format"] == declared


def test_language(client: TestClient, jpeg: bytes) -> None:
    data = post(client, "a.jpg", jpeg, lang="fr").json()
    assert data["lang"] == "fr"
    assert (
        data["results"][0]["label"]
        != post(client, "a.jpg", jpeg).json()["results"][0]["label"]
    )


def test_sky_reaches_the_solar_signal(client: TestClient, paris_noon: bytes) -> None:
    unseen = signal(post(client, "a.jpg", paris_noon).json(), "solar")
    assert unseen["state"] == "unverifiable"
    day = signal(post(client, "a.jpg", paris_noon, sky="day").json(), "solar")
    night = signal(post(client, "a.jpg", paris_noon, sky="night").json(), "solar")
    assert day["state"] == "consistent"
    assert night["state"] == "suspicious"


@pytest.mark.parametrize("form", [{"sky": "noon"}, {"lang": "de"}])
def test_bad_options_are_rejected(
    client: TestClient, jpeg: bytes, form: dict[str, str]
) -> None:
    assert post(client, "a.jpg", jpeg, **form).status_code == 422


def test_embedded_preview_is_returned(
    client: TestClient, tmp_path: Path, jpeg: bytes
) -> None:
    thumb = tmp_path / "thumb.jpg"
    Image.new("RGB", (16, 12), (200, 0, 0)).save(thumb)
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(jpeg)
    subprocess.run(
        ["exiftool", "-q", "-overwrite_original", f"-ThumbnailImage<={thumb}", photo],
        check=True,
    )
    data = post(client, "photo.jpg", photo.read_bytes()).json()
    assert data["thumbnail"].startswith("data:image/jpeg;base64,")


def test_failed_analysis_leaves_nothing_behind(
    client: TestClient,
    jpeg: bytes,
    tmpdir_for_uploads: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail(*_: object, **__: object) -> None:
        raise ExifToolError("secret content from the file")

    monkeypatch.setattr(api_module, "analyze", fail)
    response = post(client, "a.jpg", jpeg)
    assert response.status_code == 500
    assert response.json() == {"error": "analysis_failed"}
    assert "secret" not in response.text
    assert "secret" not in caplog.text
    assert list(tmpdir_for_uploads.iterdir()) == []


def test_unexpected_error_leaves_nothing_behind(
    client: TestClient,
    jpeg: bytes,
    tmpdir_for_uploads: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def crash(*_: object, **__: object) -> None:
        raise RuntimeError("bug")

    monkeypatch.setattr(api_module, "analyze", crash)
    with pytest.raises(RuntimeError):
        post(client, "a.jpg", jpeg)
    assert list(tmpdir_for_uploads.iterdir()) == []
