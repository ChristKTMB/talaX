"""Builds the context of a file and runs the signals on it."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from talax.extraction import read_metadata
from talax.fileinfo import read_file_info
from talax.integrity import assess_integrity
from talax.jpeg import JpegError, JpegStructure, read_jpeg_structure
from talax.model import Analysis, Context, Declaration, Observation
from talax.provenance import embedded_trust_list, read_c2pa
from talax.signals import DEFAULT_SIGNALS, Signal, run_signals
from talax.traits import read_traits


def analyze(
    path: Path,
    declaration: Declaration | None = None,
    observation: Observation | None = None,
    signals: Iterable[Signal] = DEFAULT_SIGNALS,
) -> Analysis:
    file = read_file_info(path)
    metadata = read_metadata(path)
    traits = read_traits(file, metadata, _jpeg_structure(path, file.real_format))
    ctx = Context(
        file=file,
        metadata=metadata,
        integrity=assess_integrity(traits),
        declaration=declaration,
        c2pa=read_c2pa(path, embedded_trust_list()),
        observation=observation,
    )
    return Analysis(
        file=file,
        integrity=ctx.integrity,
        results=run_signals(ctx, signals),
        created_at=datetime.now(UTC),
    )


def _jpeg_structure(path: Path, real_format: str | None) -> JpegStructure | None:
    if real_format != "image/jpeg":
        return None
    try:
        return read_jpeg_structure(path)
    except JpegError:
        # A damaged structure leaves the generic rules with less to go on;
        # it is not a reason to stop the analysis.
        return None
