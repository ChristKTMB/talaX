"""Temporary debug entry point: `python -m talax FILE`. The real CLI is step 5."""

from __future__ import annotations

import sys
from pathlib import Path

from talax.analysis import analyze
from talax.extraction import ExifToolError
from talax.jpeg import JpegError, read_jpeg_structure
from talax.model import Observation, Sky


def main(argv: list[str]) -> int:
    if len(argv) not in (1, 2) or (len(argv) == 2 and argv[1] not in set(Sky)):
        print("usage: python -m talax FILE [day|twilight|night]", file=sys.stderr)
        return 2
    path = Path(argv[0])
    observation = Observation(Sky(argv[1])) if len(argv) == 2 else None
    try:
        analysis = analyze(path, observation=observation)
    except (OSError, ExifToolError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    f = analysis.file
    print(f"sha256      {f.sha256}")
    print(f"size        {f.size} bytes")
    print(f"declared    {f.declared_format}")
    print(f"real        {f.real_format}")
    i = analysis.integrity
    print(f"integrity   {i.verdict} ({i.evidence.get('basis')}): {i.explanation}")
    if i.pipeline:
        print(f"pipeline    {i.pipeline}")
    if f.real_format == "image/jpeg":
        try:
            jpeg = read_jpeg_structure(path)
        except JpegError as exc:
            print(f"jpeg        unreadable structure: {exc}")
        else:
            print(f"segments    {' '.join(jpeg.segments)}")
            print(f"progressive {jpeg.progressive}")
            for t in jpeg.quant_tables:
                print(f"dqt {t.table_id}       {' '.join(map(str, t.values[:8]))} ...")
    print()
    for r in analysis.results:
        print(f"[{r.state}] {r.signal_id}: {r.explanation}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
