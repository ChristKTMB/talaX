import logging
import shutil
import struct
import subprocess
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from talax.extraction import ExifToolError
from talax.report import REPORT_CSP

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
    assert response.json()["error"]["code"] == "analysis_failed"
    assert "secret" not in response.text
    assert "secret" not in caplog.text
    assert list(tmpdir_for_uploads.iterdir()) == []


def test_unexpected_error_is_answered_and_logged_without_its_text(
    client: TestClient,
    jpeg: bytes,
    tmpdir_for_uploads: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def crash(*_: object, **__: object) -> None:
        raise RuntimeError("secret content from the file")

    monkeypatch.setattr(api_module, "analyze", crash)
    response = post(client, "a.jpg", jpeg)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal"
    assert "RuntimeError" in caplog.text
    assert "secret" not in response.text + caplog.text
    assert list(tmpdir_for_uploads.iterdir()) == []


def test_errors_follow_the_browser_language(client: TestClient) -> None:
    response = client.get("/api/nowhere", headers={"accept-language": "fr-CD,fr"})
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["message"] == "Cette adresse n'existe pas."


def test_analysis_follows_the_browser_language_unless_told(
    client: TestClient, jpeg: bytes
) -> None:
    files = {"file": ("a.jpg", jpeg)}
    fr = {"accept-language": "fr-FR"}
    assert client.post("/api/analyze", files=files, headers=fr).json()["lang"] == "fr"
    data = client.post("/api/analyze", files=files, headers=fr, data={"lang": "en"})
    assert data.json()["lang"] == "en"


def test_validation_errors_do_not_echo_the_values(
    client: TestClient, jpeg: bytes
) -> None:
    response = post(client, "a.jpg", jpeg, sky="<script>")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["fields"] == ["sky"]
    assert "script" not in response.text


def test_missing_file_is_an_invalid_request(client: TestClient) -> None:
    response = client.post("/api/analyze", data={"lang": "fr"})
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == ["file"]


@pytest.fixture
def small_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_module, "MAX_UPLOAD_MB", 1)


def test_declared_oversize_is_refused_before_reading(
    client: TestClient, small_limit: None
) -> None:
    response = client.post(
        "/api/analyze", content=b"x", headers={"content-length": str(10**9)}
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_oversize_is_refused_while_reading_even_without_length(
    client: TestClient, small_limit: None, tmpdir_for_uploads: Path
) -> None:
    boundary = b"talaxboundary"
    head = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename="a.jpg"\r\n\r\n'
    )

    def chunks() -> Iterator[bytes]:
        yield head
        for _ in range(40):  # 2.5 MB, sent without Content-Length
            yield b"\xff" * 65536

    response = client.post(
        "/api/analyze",
        content=chunks(),
        headers={"content-type": f"multipart/form-data; boundary={boundary.decode()}"},
    )
    assert response.status_code == 413
    assert "MB" in response.json()["error"]["message"]
    assert list(tmpdir_for_uploads.iterdir()) == []


def test_busy_service_refuses_at_once(
    client: TestClient, jpeg: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_module, "_slots", threading.BoundedSemaphore(1))
    api_module._slots.acquire()
    response = post(client, "a.jpg", jpeg)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "busy"


def test_slot_is_released_after_a_failure(
    client: TestClient, jpeg: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(api_module, "_slots", slots)

    def crash(*_: object, **__: object) -> None:
        raise RuntimeError("bug")

    monkeypatch.setattr(api_module, "analyze", crash)
    assert post(client, "a.jpg", jpeg).status_code == 500
    assert slots.acquire(blocking=False)


def test_security_headers(client: TestClient, jpeg: bytes) -> None:
    for response in (client.get("/api/health"), post(client, "a.jpg", jpeg)):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["cache-control"] == "no-store"
        assert "default-src 'none'" in response.headers["content-security-policy"]


def test_access_log_has_route_and_status_but_no_path_or_address(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="talax.api"):
        client.get("/api/health")
        client.get("/api/48.8566,2.3522")
    assert "GET /api/health 200" in caplog.text
    assert "GET - 404" in caplog.text
    assert "48.85" not in caplog.text
    assert "testclient" not in caplog.text


def test_lying_preview_size_does_not_break_the_analysis(
    client: TestClient, tmp_path: Path
) -> None:
    """An embedded preview whose header claims 60000 x 60000 pixels."""
    small = tmp_path / "small.jpg"
    Image.new("RGB", (16, 16)).save(small)
    liar = bytearray(small.read_bytes())
    sof = liar.find(b"\xff\xc0")
    liar[sof + 5 : sof + 9] = struct.pack(">HH", 60000, 60000)
    small.write_bytes(liar)
    photo = tmp_path / "photo.jpg"
    Image.new("RGB", (64, 48)).save(photo)
    subprocess.run(
        ["exiftool", "-q", "-overwrite_original", f"-ThumbnailImage<={small}", photo],
        check=True,
    )
    response = post(client, "photo.jpg", photo.read_bytes())
    assert response.status_code == 200
    assert response.json()["thumbnail"] is None


HOSTILE = "<script>alert(1)</script>"


def test_html_report_is_a_self_contained_download(
    client: TestClient, tmp_path: Path, tmpdir_for_uploads: Path
) -> None:
    photo = tmp_path / "holiday.jpg"
    Image.new("RGB", (64, 48)).save(photo)
    subprocess.run(
        ["exiftool", "-q", "-overwrite_original", f"-IFD0:Software={HOSTILE}", photo],
        check=True,
    )
    response = client.post(
        "/api/analyze?format=html",
        files={"file": ("holiday.jpg", photo.read_bytes())},
        data={"lang": "fr"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="talax-')
    # One policy only, the report's: a stricter one would hide its styles.
    assert response.headers.get_list("content-security-policy") == [REPORT_CSP]
    assert '<html lang="fr"' in response.text
    assert HOSTILE not in response.text
    assert "holiday" not in response.text + disposition
    assert "upload" not in response.text
    assert "data:image/jpeg;base64," in response.text  # the image preview
    assert list(tmpdir_for_uploads.iterdir()) == []


def test_unknown_format_is_rejected(client: TestClient, jpeg: bytes) -> None:
    response = client.post("/api/analyze?format=pdf", files={"file": ("a.jpg", jpeg)})
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == ["format"]
