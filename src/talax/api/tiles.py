"""Map tiles relayed from OpenStreetMap.

The browser asks us, never OpenStreetMap: OSM learns which areas are viewed,
not by whom. The relay follows the OSM tile usage policy
(https://operations.osmfoundation.org/policies/tiles/): a stable User-Agent
with a contact, the Referer kept (reduced to our site's origin), caching
headers honoured, conditional requests once a tile expires, no no-cache
header. The cache lives in memory only: no trace of the areas viewed is left
on disk.
"""

from __future__ import annotations

import email.utils
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Annotated, NamedTuple
from urllib.parse import urlsplit

from fastapi import APIRouter, Header, Response
from starlette.exceptions import HTTPException

from talax import __version__

# Replaceable without a code change (recommended by the OSM policy), e.g. if
# OSM ever blocks the relay.
TILE_URL = os.environ.get(
    "TALAX_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
)
if not TILE_URL.startswith("https://"):
    raise ValueError("TALAX_TILE_URL must be an https:// URL")

MAX_ZOOM = 19
# Product name and contact stay the same across releases (OSM policy).
USER_AGENT = f"talax/{__version__} (+https://github.com/ChristKTMB/talaX)"
CACHE_BYTES = 128 * 1024 * 1024
_DEFAULT_TTL = 7 * 24 * 3600  # OSM: "at least 7 days" without usable headers
_MIN_TTL, _MAX_TTL = 60, 30 * 24 * 3600
_TIMEOUT_SECONDS = 10
_MAX_TILE_BYTES = 1024 * 1024
_PNG = b"\x89PNG\r\n\x1a\n"
_MAX_AGE = re.compile(r"max-age=(\d+)")

# Courtesy towards the tile server: two downloads at a time at most.
_upstream = threading.BoundedSemaphore(2)

Key = tuple[int, int, int]
_now = time.time  # replaceable in tests


@dataclass(frozen=True, slots=True)
class _Tile:
    data: bytes
    expires: float
    etag: str | None
    last_modified: str | None


class _Cache:
    """Least recently used tiles, bounded in bytes."""

    def __init__(self, max_bytes: int) -> None:
        self._max = max_bytes
        self._items: OrderedDict[Key, _Tile] = OrderedDict()
        self._size = 0
        self._lock = threading.Lock()

    def get(self, key: Key) -> _Tile | None:
        with self._lock:
            tile = self._items.get(key)
            if tile is not None:
                self._items.move_to_end(key)
            return tile

    def put(self, key: Key, tile: _Tile) -> None:
        with self._lock:
            old = self._items.pop(key, None)
            if old is not None:
                self._size -= len(old.data)
            self._items[key] = tile
            self._size += len(tile.data)
            while self._size > self._max and self._items:
                _, evicted = self._items.popitem(last=False)
                self._size -= len(evicted.data)


_cache = _Cache(CACHE_BYTES)


class _Upstream(NamedTuple):
    status: int
    data: bytes
    headers: Mapping[str, str]  # lower-case names


def _download(url: str, headers: Mapping[str, str]) -> _Upstream:
    request = urllib.request.Request(url, headers=dict(headers))
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            data = response.read(_MAX_TILE_BYTES + 1)
            status, raw = response.status, response.headers
    except urllib.error.HTTPError as exc:  # 304 and 404 arrive this way
        status, raw, data = exc.code, exc.headers, b""
    return _Upstream(status, data, {k.lower(): v for k, v in raw.items()})


router = APIRouter()


@router.get("/api/tiles/{z}/{x}/{y}.png")
def tile(
    z: int, x: int, y: int, referer: Annotated[str | None, Header()] = None
) -> Response:
    """One map tile. Show "© OpenStreetMap contributors" on the map."""
    if not (0 <= z <= MAX_ZOOM and 0 <= x < 2**z and 0 <= y < 2**z):
        raise HTTPException(404)
    key = (z, x, y)
    cached = _cache.get(key)
    if cached is not None and cached.expires > _now():
        return _png(cached.data)

    headers = {"User-Agent": USER_AGENT}
    if origin := _origin(referer):
        headers["Referer"] = origin
    if cached is not None and cached.etag:
        headers["If-None-Match"] = cached.etag
    if cached is not None and cached.last_modified:
        headers["If-Modified-Since"] = cached.last_modified

    if not _upstream.acquire(timeout=_TIMEOUT_SECONDS):
        if cached is not None:
            return _png(cached.data)
        raise HTTPException(503)
    try:
        upstream: _Upstream | None = _download(TILE_URL.format(z=z, x=x, y=y), headers)
    except OSError:
        upstream = None
    finally:
        _upstream.release()

    now = _now()
    if upstream is not None and upstream.status == 304 and cached is not None:
        _cache.put(key, replace(cached, expires=now + _ttl(upstream.headers, now)))
        return _png(cached.data)
    if (
        upstream is not None
        and upstream.status == 200
        and upstream.data.startswith(_PNG)
        and len(upstream.data) <= _MAX_TILE_BYTES
    ):
        _cache.put(
            key,
            _Tile(
                data=upstream.data,
                expires=now + _ttl(upstream.headers, now),
                etag=upstream.headers.get("etag"),
                last_modified=upstream.headers.get("last-modified"),
            ),
        )
        return _png(upstream.data)
    if upstream is not None and upstream.status == 404:
        raise HTTPException(404)
    if cached is not None:
        return _png(cached.data)  # an expired tile beats no map
    raise HTTPException(502)


def _ttl(headers: Mapping[str, str], now: float) -> float:
    seconds: float = _DEFAULT_TTL
    if match := _MAX_AGE.search(headers.get("cache-control", "")):
        seconds = int(match.group(1))
    elif expires := headers.get("expires"):
        try:
            seconds = email.utils.parsedate_to_datetime(expires).timestamp() - now
        except (TypeError, ValueError):
            seconds = _DEFAULT_TTL
    return min(max(seconds, _MIN_TTL), _MAX_TTL)


def _origin(referer: str | None) -> str | None:
    """Our page's origin only: the rest of its address is none of OSM's business."""
    if not referer:
        return None
    parts = urlsplit(referer)
    host = parts.netloc.rpartition("@")[2]  # never forward credentials
    if parts.scheme not in ("http", "https") or not host:
        return None
    return f"{parts.scheme}://{host}/"


def _png(data: bytes) -> Response:
    return Response(content=data, media_type="image/png")
