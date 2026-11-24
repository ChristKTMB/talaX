"""Several files at once: each analysed as on its own, then seen together.

Nothing here changes how one file is judged: a batch is a list of ordinary
analyses, plus what only appears when they are side by side.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from talax.analysis import analyze
from talax.clock import offset_from_text
from talax.extraction import ExifToolError
from talax.fileinfo import sniff_format
from talax.geo import distance_km
from talax.model import Analysis, Batch, BatchItem, DuplicateGroup, State
from talax.similarity import SAME_IMAGE, SIMILAR, distance, visual_hash
from talax.solar import utc_offset, zone_at

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


@dataclass(frozen=True, slots=True)
class Moment:
    """When a file says it was taken."""

    name: str
    local: datetime
    """As the device recorded it, without a time zone."""
    utc: datetime | None
    """None when the time zone is unknown: then sorted on the local time."""
    offset: str | None
    """`+02:00`, from the file or from the time zone of its GPS position."""


@dataclass(frozen=True, slots=True)
class Place:
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class Spread:
    """The two places of a batch farthest apart."""

    first: str
    second: str
    km: float


def timeline(batch: Batch) -> tuple[list[Moment], list[str]]:
    """Dated files in order, and the names of files with no capture time."""
    dated, undated = [], []
    for item in batch.items:
        moment = _moment(item)
        if moment is not None:
            dated.append(moment)
        elif item.analysis is not None:
            undated.append(item.name)
    real_time = all(m.utc is not None for m in dated)
    dated.sort(key=lambda m: (_sort_key(m, real_time), m.name))
    return dated, undated


def span(moments: list[Moment]) -> timedelta | None:
    """From the first photo to the last; approximate if a time zone is unknown."""
    if len(moments) < 2:
        return None
    real_time = all(m.utc is not None for m in moments)
    keys = [_sort_key(m, real_time) for m in moments]
    return max(keys) - min(keys)


def _sort_key(moment: Moment, real_time: bool) -> datetime:
    """Real time when every time zone is known; otherwise the time shown by
    the devices for all, so that a file of unknown zone is not misplaced."""
    if real_time and moment.utc is not None:
        return moment.utc
    return moment.local.replace(tzinfo=UTC)


def places(batch: Batch) -> tuple[list[Place], list[str], Spread | None]:
    """Files with a consistent GPS position, those without, and the widest
    distance between two of them."""
    found, missing = [], []
    for item in batch.items:
        place = _place(item)
        if place is not None:
            found.append(place)
        elif item.analysis is not None:
            missing.append(item.name)
    widest = max(
        (
            Spread(
                a.name,
                b.name,
                distance_km(a.latitude, a.longitude, b.latitude, b.longitude),
            )
            for a, b in itertools.combinations(found, 2)
        ),
        key=lambda s: s.km,
        default=None,
    )
    return found, missing, widest


def concerns(analysis: Analysis) -> tuple[tuple[str, State], ...]:
    """The checks to look at first: suspicious ones, then those to check."""
    order = (State.SUSPICIOUS, State.TO_CHECK)
    return tuple(
        (r.signal_id, r.state)
        for state in order
        for r in analysis.results
        if r.state is state
    )


def recorded_time(analysis: Analysis) -> str | None:
    """Capture time as recorded (local time of the device), to the minute."""
    for r in analysis.results:
        if r.signal_id == "capture_time" and r.state is not State.UNVERIFIABLE:
            value = r.evidence.get("date_time_original")
            if isinstance(value, str):
                return value[:16].replace("T", " ")
    return None


def position(analysis: Analysis) -> tuple[float, float] | None:
    """The GPS position, when the GPS check found it consistent."""
    for r in analysis.results:
        if r.signal_id == "gps" and r.state is State.CONSISTENT:
            lat, lon = r.evidence.get("latitude"), r.evidence.get("longitude")
            if isinstance(lat, int | float) and isinstance(lon, int | float):
                return float(lat), float(lon)
    return None


def _moment(item: BatchItem) -> Moment | None:
    if item.analysis is None:
        return None
    evidence = next(
        (r.evidence for r in item.analysis.results if r.signal_id == "capture_time"),
        {},
    )
    raw = evidence.get("date_time_original")
    if not isinstance(raw, str):
        return None
    try:
        local = datetime.fromisoformat(raw)
    except ValueError:
        return None
    offset = evidence.get("offset")
    zone: timezone | None
    if isinstance(offset, str):
        zone = offset_from_text(offset)
    else:
        place = _place(item)
        found = zone_at(place.latitude, place.longitude) if place else None
        zone = utc_offset(found, local) if found else None
    if zone is None:
        return Moment(item.name, local, None, None)
    utc = local.replace(tzinfo=zone).astimezone(UTC)
    shown = zone.utcoffset(None)
    sign = "-" if shown < timedelta(0) else "+"
    minutes = int(abs(shown).total_seconds() // 60)
    return Moment(
        item.name, local, utc, f"{sign}{minutes // 60:02d}:{minutes % 60:02d}"
    )


def _place(item: BatchItem) -> Place | None:
    found = position(item.analysis) if item.analysis else None
    return Place(item.name, *found) if found else None


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
