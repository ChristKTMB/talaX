"""How far apart are copies of the same photo, and different photos?

Measures the visual hash (talax.similarity) on the corpus, whose truth sheets
say which files are the same shot: in a set, the trailing number of a file
name is the shot; an edits set (`source_set`) reuses the numbers of its source.
Prints distances only, never file contents or positions.

    uv run python scripts/duplicates_report.py
"""

from __future__ import annotations

import itertools
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

from talax.similarity import distance, visual_hash

ROOT = Path(__file__).resolve().parent.parent / "corpus"
_SHOT = re.compile(r"^(?P<route>.*?)(?P<shot>\d+)\.[a-z]+$")


def files() -> list[tuple[str, str, str, Path]]:
    """(shot id, set, route, path) for every file of every set."""
    found = []
    for sheet in sorted((ROOT / "sets").glob("*.yaml")):
        if sheet.name.startswith("_"):
            continue
        meta = yaml.safe_load(sheet.read_text(encoding="utf-8"))
        folder = ROOT / "files" / meta["id"]
        # The official C2PA samples are variants of one photo (cropped,
        # annotated): which ones count as "the same" is not defined.
        if not folder.is_dir() or meta["id"] == "c2pa-public-1.4":
            continue
        family = meta.get("source_set") or meta["id"]
        for path in sorted(folder.iterdir()):
            match = _SHOT.match(path.name)
            shot = f"{family}#{match['shot']}" if match else f"{meta['id']}/{path.name}"
            route = match["route"] if match else path.stem
            found.append((shot, meta["id"], route, path))
    return found


def main(size: int) -> None:
    entries = [(s, st, r, p, visual_hash(p, size)) for s, st, r, p in files()]
    entries = [e for e in entries if e[4] is not None]
    same: list[tuple[int, str]] = []
    different: list[int] = []
    for a, b in itertools.combinations(entries, 2):
        if a[3].read_bytes() == b[3].read_bytes():
            continue  # byte-identical: the SHA-256 already groups them
        d = distance(a[4], b[4])  # type: ignore[arg-type]
        if a[0] == b[0]:
            same.append((d, f"{a[2]} / {b[2]}"))
        else:
            different.append(d)
    bits = size * size
    print(f"hash {size}x{size} ({bits} bits), {len(entries)} files", file=sys.stderr)
    print(f"same shot, {len(same)} pairs: max {max(d for d, _ in same)}")
    worst = sorted(same, reverse=True)[:8]
    for d, routes in worst:
        print(f"   {d:3}  {routes}")
    print(f"different shots, {len(different)} pairs: min {min(different)}")
    low = Counter(d for d in different if d <= bits // 4)
    print(f"   closest: {sorted(low.items())[:10]}")


if __name__ == "__main__":
    main(16)
