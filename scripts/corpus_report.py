"""Integrity test against the reference corpus: per-route results and errors.

uv run python scripts/corpus_report.py
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

import yaml

from talax.analysis import analyze

CORPUS = Path(__file__).resolve().parent.parent / "corpus"


def main() -> int:
    rows: collections.Counter[tuple[str, str, str, str]] = collections.Counter()
    errors: list[str] = []
    excluded = 0

    for sheet_path in sorted((CORPUS / "sets").glob("[!_]*.yaml")):
        sheet = yaml.safe_load(sheet_path.read_text())
        for name in sheet["sha256"]:
            route = re.sub(r"\d+$", "", Path(name).stem)
            truth = sheet["routes"][route]
            path = CORPUS / "files" / sheet["id"] / name
            if "excluded" in truth:
                excluded += 1
                continue
            if not path.exists():
                continue
            got = analyze(path).integrity
            expected = (truth["expected_integrity"], truth.get("expected_pipeline"))
            actual = (str(got.verdict), got.pipeline)
            rows[
                (route, *map(str, expected), "ok" if actual == expected else "ERROR")
            ] += 1
            if actual != expected:
                errors.append(
                    f"{sheet['id']}/{name}: expected {expected}, got {actual}"
                )

    total = sum(rows.values())
    if not total:
        print("No corpus files found in corpus/files/.")
        return 1

    print(f"{'route':<22} {'expected':<14} {'pipeline':<18} {'result':<7} files")
    for (route, verdict, pipeline, status), n in sorted(rows.items()):
        print(f"{route:<22} {verdict:<14} {pipeline:<18} {status:<7} {n}")
    wrong = len(errors)
    print(
        f"\n{total} files checked, {wrong} errors ({wrong / total:.0%}), "
        f"{excluded} excluded."
    )
    for line in errors:
        print("  " + line)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
