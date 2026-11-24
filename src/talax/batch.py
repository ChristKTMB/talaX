"""Several files at once: each analysed as on its own, then seen together.

Nothing here changes how one file is judged: a batch is a list of ordinary
analyses, plus what only appears when they are side by side.
"""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from talax.analysis import analyze
from talax.extraction import ExifToolError
from talax.fileinfo import sniff_format
from talax.model import Analysis, Batch, BatchItem, State

# ExifTool is an external process: threads wait on it in parallel. Measured
# at about 90 ms per file, so 4 at a time keeps 100 files to a few seconds.
WORKERS = 4
_SNIFF_SIZE = 32


def collect(paths: Iterable[Path]) -> tuple[list[tuple[str, Path]], list[str]]:
    """Files to analyse and names skipped, both sorted, from files or folders.

    A folder gives the files directly inside it (not its subfolders), hidden
    files excepted. A file is kept when its first bytes are a format Tala X
    recognises, whatever its extension.
    """
    found: list[tuple[str, Path]] = []
    for path in paths:
        if path.is_dir():
            found += [
                (f"{path.name}/{child.name}", child)
                for child in path.iterdir()
                if child.is_file() and not child.name.startswith(".")
            ]
        else:
            found.append((path.name, path))
    kept: list[tuple[str, Path]] = []
    skipped: list[tuple[str, Path]] = []
    for name, path in sorted(found):
        (kept if _recognised(path) else skipped).append((name, path))
    return kept, [name for name, _ in skipped]


def analyze_batch(paths: Iterable[Path], workers: int = WORKERS) -> Batch:
    """Analyse every recognised file. A file that cannot be read is listed
    with its error; it never stops the others."""
    kept, skipped = collect(paths)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        items = tuple(pool.map(lambda entry: _analyse(*entry), kept))
    return Batch(items=items, skipped=tuple(skipped), created_at=datetime.now(UTC))


def concerns(analysis: Analysis) -> tuple[tuple[str, State], ...]:
    """The checks to look at first: suspicious ones, then those to check."""
    order = (State.SUSPICIOUS, State.TO_CHECK)
    return tuple(
        (r.signal_id, r.state)
        for state in order
        for r in analysis.results
        if r.state is state
    )


def _analyse(name: str, path: Path) -> BatchItem:
    try:
        return BatchItem(name=name, analysis=analyze(path))
    except (OSError, ExifToolError):
        return BatchItem(name=name, analysis=None, error="unreadable")


def _recognised(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return sniff_format(f.read(_SNIFF_SIZE)) is not None
    except OSError:
        return False
