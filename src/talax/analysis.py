"""Builds the context of a file and runs the signals on it."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from talax.extraction import read_metadata
from talax.fileinfo import read_file_info
from talax.model import (
    Analysis,
    Context,
    Declaration,
    IntegrityAssessment,
    IntegrityVerdict,
)
from talax.signals import DEFAULT_SIGNALS, Signal, run_signals

# Placeholder until the integrity test exists (step 2, part E).
_INTEGRITY_PENDING = IntegrityAssessment(
    verdict=IntegrityVerdict.UNDETERMINED,
    explanation="The integrity test is not implemented yet.",
)


def analyze(
    path: Path,
    declaration: Declaration | None = None,
    signals: Iterable[Signal] = DEFAULT_SIGNALS,
) -> Analysis:
    file = read_file_info(path)
    ctx = Context(
        file=file,
        metadata=read_metadata(path),
        integrity=_INTEGRITY_PENDING,
        declaration=declaration,
    )
    return Analysis(
        file=file,
        integrity=ctx.integrity,
        results=run_signals(ctx, signals),
        created_at=datetime.now(UTC),
    )
