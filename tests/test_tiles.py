import logging
import time
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from talax.api import tiles
from talax.api.app import app

PNG = b"\x89PNG\r\n\x1a\n" + b"tile"


class FakeServer:
    """Stands for tile.openstreetmap.org and records what it receives."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []
        self.reply: tiles._Upstream | Exception = tiles._Upstream(
            200, PNG, {"cache-control": "max-age=3600", "etag": '"v1"'}
        )

    def __call__(self, url: str, headers: Mapping[str, str]) -> tiles._Upstream:
        self.calls.append((url, dict(headers)))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> FakeServer:
    fake = FakeServer()
    monkeypatch.setattr(tiles, "_download", fake)
    monkeypatch.setattr(tiles, "_cache", tiles._Cache(tiles.CACHE_BYTES))
    return fake


@pytest.fixture
def client(server: FakeServer) -> Iterator[TestClient]:
    # No lifespan: the relay does not need ExifTool.
    yield TestClient(app)


def get(
    client: TestClient, path: str = "/api/tiles/12/2048/1361.png", **kw: Any
) -> Any:
    return client.get(path, **kw)


def test_tile_is_relayed_with_an_identifying_user_agent(
    client: TestClient, server: FakeServer
) -> None:
    response = get(client)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == PNG
    url, headers = server.calls[0]
    assert url == "https://tile.openstreetmap.org/12/2048/1361.png"
    assert headers["User-Agent"].startswith("talax/")
    assert "github.com/ChristKTMB/talaX" in headers["User-Agent"]
    assert not any("cache" in name.lower() for name in headers)


def test_referer_is_kept_but_reduced_to_our_origin(
    client: TestClient, server: FakeServer
) -> None:
    get(client, headers={"referer": "https://me:pw@talax.example/r?lat=48.85#x"})
    assert server.calls[0][1]["Referer"] == "https://talax.example/"


def test_no_referer_is_invented(client: TestClient, server: FakeServer) -> None:
    get(client)
    assert "Referer" not in server.calls[0][1]


def test_fresh_tile_comes_from_the_cache(
    client: TestClient, server: FakeServer
) -> None:
    get(client)
    assert get(client).content == PNG
    assert len(server.calls) == 1


def test_expired_tile_is_revalidated_with_its_etag(
    client: TestClient, server: FakeServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    get(client)
    later = time.time() + 7200
    monkeypatch.setattr(tiles, "_now", lambda: later)
    server.reply = tiles._Upstream(304, b"", {"cache-control": "max-age=3600"})
    assert get(client).content == PNG
    assert server.calls[1][1]["If-None-Match"] == '"v1"'
    assert get(client).status_code == 200
    assert len(server.calls) == 2  # the 304 made it fresh again


def test_expired_tile_is_served_when_the_server_fails(
    client: TestClient, server: FakeServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    get(client)
    later = time.time() + 7200
    monkeypatch.setattr(tiles, "_now", lambda: later)
    server.reply = OSError("down")
    assert get(client).content == PNG


@pytest.mark.parametrize(
    "path",
    [
        "/api/tiles/20/0/0.png",
        "/api/tiles/2/4/0.png",
        "/api/tiles/2/0/-1.png",
        "/api/tiles/x/0/0.png",
    ],
)
def test_impossible_tiles_are_not_requested(
    client: TestClient, server: FakeServer, path: str
) -> None:
    assert get(client, path).status_code in (404, 422)
    assert server.calls == []


@pytest.mark.parametrize(
    "reply",
    [
        OSError("down"),
        tiles._Upstream(500, b"", {}),
        tiles._Upstream(200, b"<html>not a tile</html>", {}),
    ],
)
def test_failure_without_cache_is_a_translated_error(
    client: TestClient, server: FakeServer, reply: tiles._Upstream | Exception
) -> None:
    server.reply = reply
    response = get(client, headers={"accept-language": "fr"})
    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == "tiles_unavailable"
    assert "carte" in error["message"]


def test_missing_upstream_tile_is_a_404(client: TestClient, server: FakeServer) -> None:
    server.reply = tiles._Upstream(404, b"", {})
    assert get(client).status_code == 404


def test_log_shows_the_route_not_the_area(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="talax.api"):
        get(client)
    assert "GET /api/tiles/{z}/{x}/{y}.png 200" in caplog.text
    assert "2048" not in caplog.text


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"cache-control": "public, max-age=86400"}, 86400),
        ({"expires": "Thu, 01 Jan 2099 00:00:00 GMT"}, tiles._MAX_TTL),
        ({"cache-control": "max-age=1"}, tiles._MIN_TTL),
        ({"expires": "not a date"}, tiles._DEFAULT_TTL),
        ({}, tiles._DEFAULT_TTL),
    ],
)
def test_cache_duration_follows_the_server(
    headers: dict[str, str], expected: int
) -> None:
    assert tiles._ttl(headers, time.time()) == pytest.approx(expected, abs=1)


def test_cache_is_bounded_in_bytes() -> None:
    cache = tiles._Cache(max_bytes=10)
    for i in range(3):
        cache.put((0, 0, i), tiles._Tile(b"12345", 0, None, None))
    assert cache.get((0, 0, 0)) is None
    assert cache.get((0, 0, 1)) is not None
    assert cache.get((0, 0, 2)) is not None
