"""Several files at once: each analysed as on its own, then seen together.

Nothing here changes how one file is judged: a batch is a list of ordinary
analyses, plus what only appears when they are side by side.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from talax.analysis import analyze
from talax.extraction import ExifToolError
from talax.fileinfo import sniff_format
from talax.model import Analysis, Batch, BatchItem, DuplicateGroup, State
from talax.similarity import SAME_IMAGE, SIMILAR, distance, visual_hash

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
    return Batch(
        items=items,
        skipped=tuple(skipped),
        created_at=datetime.now(UTC),
        groups=duplicate_groups(items),
    )


def duplicate_groups(items: tuple[BatchItem, ...]) -> tuple[DuplicateGroup, ...]:
    """Files showing the same picture, or nearly.

    First the files with the same bytes (`identical`). Then, one file standing
    for each set of identical bytes, the pictures linked pair by pair when
    their fingerprints are at most SIMILAR bits apart: `same_image` when no
    two of them are more than SAME_IMAGE bits apart, `similar` otherwise.
    """
    by_bytes: dict[str, list[BatchItem]] = {}
    for item in items:
        if item.analysis is not None:
            by_bytes.setdefault(item.analysis.file.sha256, []).append(item)
    groups = [
        DuplicateGroup("identical", tuple(i.name for i in same), 0, _bits(same))
        for same in by_bytes.values()
        if len(same) > 1
    ]

    picks = [same for same in by_bytes.values() if same[0].visual is not None]
    parent = list(range(len(picks)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    gaps: dict[tuple[int, int], int] = {}
    for i, j in itertools.combinations(range(len(picks)), 2):
        gap = distance(picks[i][0].visual, picks[j][0].visual)  # type: ignore[arg-type]
        gaps[i, j] = gap
        if gap <= SIMILAR:
            parent[root(i)] = root(j)

    members: dict[int, list[int]] = {}
    for i in range(len(picks)):
        members.setdefault(root(i), []).append(i)
    for indexes in members.values():
        if len(indexes) < 2:
            continue
        widest = max(gaps[pair] for pair in itertools.combinations(indexes, 2))
        files = [item for i in indexes for item in picks[i]]
        groups.append(
            DuplicateGroup(
                "same_image" if widest <= SAME_IMAGE else "similar",
                tuple(sorted(item.name for item in files)),
                widest,
                _bits(files),
            )
        )
    kinds = ["identical", "same_image", "similar"]
    return tuple(sorted(groups, key=lambda g: (kinds.index(g.kind), g.names)))


def _bits(items: list[BatchItem]) -> int:
    size = next((item.visual.size for item in items if item.visual), 16)
    return size * size


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
        return BatchItem(name=name, analysis=analyze(path), visual=visual_hash(path))
    except (OSError, ExifToolError):
        return BatchItem(name=name, analysis=None, error="unreadable")


def _recognised(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return sniff_format(f.read(_SNIFF_SIZE)) is not None
    except OSError:
        return False
