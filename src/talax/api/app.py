"""Web API: a thin adapter over the analysis core.

An uploaded file exists on disk only for the time of its analysis (ExifTool
and the C2PA reader need a path), in a temporary directory deleted afterwards,
errors included. Nothing about it is kept.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path, PurePath
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from talax import __version__
from talax.analysis import analyze
from talax.extraction import ExifToolError, exiftool_version
from talax.i18n import Language
from talax.model import Observation, Sky
from talax.report import SCHEMA_VERSION, thumbnail_uri, to_dict, tool_versions

_log = logging.getLogger("talax.api")
_EXTENSION = re.compile(r"\.[a-z0-9]{1,10}")


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    exiftool_version()  # same rule as the CLI: no suitable ExifTool, no start
    yield


app = FastAPI(
    title="Tala X",
    version=__version__,
    lifespan=_lifespan,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url=None,
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "schema": SCHEMA_VERSION, "tools": tool_versions()}


@app.post("/api/analyze")
def analyze_upload(
    file: Annotated[UploadFile, File()],
    lang: Annotated[Language, Form()] = Language.EN,
    sky: Annotated[Sky | None, Form()] = None,
) -> JSONResponse:
    """Analyse one file. The response is the schema-2 JSON of the CLI, plus
    `thumbnail`: the embedded preview as a `data:` URI, or null."""
    with tempfile.TemporaryDirectory(prefix="talax-") as tmp:
        path = Path(tmp) / f"upload{_extension(file.filename)}"
        with path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        try:
            analysis = analyze(path, observation=Observation(sky) if sky else None)
            thumbnail = thumbnail_uri(path)
        except (OSError, ExifToolError):
            # The exception text may quote file content: never logged.
            _log.error("analysis failed")
            return JSONResponse({"error": "analysis_failed"}, status_code=500)
    # The name stays with the sender: the browser already knows it.
    data = to_dict(analysis, None, lang)
    data["thumbnail"] = thumbnail
    return JSONResponse(data)


def _extension(filename: str | None) -> str:
    """The original extension, which sets the declared format; never the name."""
    suffix = PurePath(filename or "").suffix.lower()
    return suffix if _EXTENSION.fullmatch(suffix) else ""
