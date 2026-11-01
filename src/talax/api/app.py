"""Web API: a thin adapter over the analysis core.

An uploaded file exists on disk only for the time of its analysis (ExifTool
and the C2PA reader need a path), in a temporary directory deleted afterwards,
errors included. Nothing about it is kept, and nothing about it is logged:
no file name, no metadata, no exception text, no client address.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import threading
import time
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path, PurePath
from typing import Annotated, Any, Literal

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.types import Message as AsgiMessage

from talax import __version__
from talax.analysis import analyze
from talax.extraction import ExifToolError, exiftool_version
from talax.i18n import Language, Message, translate
from talax.model import Observation, Sky
from talax.report import (
    REPORT_CSP,
    SCHEMA_VERSION,
    render_html,
    thumbnail_uri,
    to_dict,
    tool_versions,
)

MAX_UPLOAD_MB = 50
# Room for the multipart envelope and the small form fields around the file.
_ENVELOPE_BYTES = 64 * 1024
MAX_CONCURRENT_ANALYSES = 4
# Each analysis runs ExifTool (about 90 ms); beyond this, refuse at once
# rather than let a queue grow.
_slots = threading.BoundedSemaphore(MAX_CONCURRENT_ANALYSES)

_log = logging.getLogger("talax.api")
_EXTENSION = re.compile(r"\.[a-z0-9]{1,10}")
_SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    # Responses describe a user's file (position, device): never cached.
    (b"cache-control", b"no-store"),
]
_CSP = (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'")
_DOCS_PATH = "/api/docs"  # the interactive docs page loads its own scripts


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    exiftool_version()  # same rule as the CLI: no suitable ExifTool, no start
    yield


app = FastAPI(
    title="Tala X",
    version=__version__,
    lifespan=_lifespan,
    openapi_url="/api/openapi.json",
    docs_url=_DOCS_PATH,
    redoc_url=None,
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "schema": SCHEMA_VERSION, "tools": tool_versions()}


@app.post("/api/analyze")
def analyze_upload(
    request: Request,
    file: Annotated[UploadFile, File()],
    lang: Annotated[Language | None, Form()] = None,
    sky: Annotated[Sky | None, Form()] = None,
    format: Annotated[Literal["json", "html"], Query()] = "json",
) -> Response:
    """Analyse one file. The response is the schema-2 JSON of the CLI, plus
    `thumbnail`: the embedded preview as a `data:` URI, or null.
    `?format=html` returns the self-contained HTML report instead, as a
    download.

    `lang` defaults to the browser language (`Accept-Language`)."""
    language = lang or _language(request.headers.get("accept-language"))
    if not _slots.acquire(blocking=False):
        return _error(503, Message("error.busy"), language)
    try:
        with tempfile.TemporaryDirectory(prefix="talax-") as tmp:
            path = Path(tmp) / f"upload{_extension(file.filename)}"
            with path.open("wb") as out:
                shutil.copyfileobj(file.file, out)
            try:
                observation = Observation(sky) if sky else None
                analysis = analyze(path, observation=observation)
                if format == "html":
                    # Built while the file still exists: it holds the previews.
                    return _html_report(
                        render_html(analysis, path, language), analysis.file.sha256
                    )
                thumbnail = thumbnail_uri(path)
            except (OSError, ExifToolError):
                _log.warning("analysis failed")
                return _error(500, Message("error.analysis_failed"), language)
    finally:
        _slots.release()
    # The name stays with the sender: the browser already knows it.
    data = to_dict(analysis, None, language)
    data["thumbnail"] = thumbnail
    return JSONResponse(data)


@app.exception_handler(RequestValidationError)
def _invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's own body would echo the submitted values back.
    fields = sorted({str(e["loc"][-1]) for e in exc.errors() if e.get("loc")})
    language = _language(request.headers.get("accept-language"))
    return _error(422, Message("error.invalid_request"), language, fields=fields)


@app.exception_handler(HTTPException)
def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
    language = _language(request.headers.get("accept-language"))
    if exc.status_code == 413:
        message = Message("error.file_too_large", {"max_mb": MAX_UPLOAD_MB})
    elif exc.status_code in (404, 405):
        message = Message("error.not_found")
    else:
        message = Message("error.invalid_request")
    return _error(exc.status_code, message, language)


class _Guard:
    """Outermost layer: upload size, unexpected errors, access log, headers.

    It catches errors itself because Starlette's last-resort handler re-raises
    them to the server, which would log their text, and that text may quote
    file content.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        language = _language(_header(scope, b"accept-language"))
        limit = MAX_UPLOAD_MB * 1024 * 1024 + _ENVELOPE_BYTES
        status = 0

        declared = _header(scope, b"content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            status = 413
            message = Message("error.file_too_large", {"max_mb": MAX_UPLOAD_MB})
            await _error(413, message, language)(scope, receive, send)
            _access(scope, status, start)
            return

        received = 0

        async def counted_receive() -> AsgiMessage:
            # Content-Length can lie or be absent (chunked): count what arrives.
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise HTTPException(413)
            return message

        async def guarded_send(message: AsgiMessage) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers += _SECURITY_HEADERS
                has_csp = any(k == _CSP[0] for k, _ in headers)
                if not has_csp and scope["path"] != _DOCS_PATH:
                    headers.append(_CSP)
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, counted_receive, guarded_send)
        except Exception as exc:
            frame = traceback.extract_tb(exc.__traceback__)[-1]
            where = f"{PurePath(frame.filename).name}:{frame.lineno}"
            _log.error("unexpected %s at %s", type(exc).__name__, where)
            if status == 0:
                status = 500
                response = _error(500, Message("error.internal"), language)
                await response(scope, receive, guarded_send)
        _access(scope, status, start)


app.add_middleware(_Guard)


def _error(status: int, message: Message, lang: Language, **extra: Any) -> JSONResponse:
    code = message.key.removeprefix("error.")
    body = {"code": code, "message": translate(message, lang), **extra}
    return JSONResponse({"error": body}, status_code=status)


def _html_report(html: str, sha256: str) -> HTMLResponse:
    # A download, not a page of our site: the report shows metadata that
    # anyone may have written. The name is the hash, never the file's name.
    return HTMLResponse(
        html,
        headers={
            "content-security-policy": REPORT_CSP,
            "content-disposition": f'attachment; filename="talax-{sha256[:12]}.html"',
        },
    )


def _access(scope: Scope, status: int, start: float) -> None:
    # The route template, never the raw path: an unknown path is free text.
    route = getattr(scope.get("route"), "path", "-")
    elapsed = (time.perf_counter() - start) * 1000
    _log.info("%s %s %d %.0f ms", scope["method"], route, status, elapsed)


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope["headers"]:
        if key == name:
            return bytes(value).decode("latin-1")
    return None


def _language(accept_language: str | None) -> Language:
    """Same rule as the CLI: French for `fr*`, English otherwise."""
    first = (accept_language or "").split(",")[0].strip().lower()
    return Language.FR if first.startswith("fr") else Language.EN


def _extension(filename: str | None) -> str:
    """The original extension, which sets the declared format; never the name."""
    suffix = PurePath(filename or "").suffix.lower()
    return suffix if _EXTENSION.fullmatch(suffix) else ""
