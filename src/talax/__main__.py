"""Temporary debug entry point: `python -m talax FILE`. The real CLI is step 5."""

from __future__ import annotations

import sys
from pathlib import Path

from talax.analysis import analyze
from talax.extraction import ExifToolError
from talax.jpeg import JpegError, read_jpeg_structure


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m talax FILE", file=sys.stderr)
        return 2
    path = Path(argv[0])
    try:
        analysis = analyze(path)
    except (OSError, ExifToolError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    f = analysis.file
    print(f"sha256      {f.sha256}")
    print(f"size        {f.size} bytes")
    print(f"declared    {f.declared_format}")
    print(f"real        {f.real_format}")
    print(f"integrity   {analysis.integrity.verdict}: {analysis.integrity.explanation}")
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
