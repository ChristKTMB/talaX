"""The examples in docs/api-examples/ must stay what the API really answers.

Compared on what a reader relies on (verdicts, states, message keys, field
names), not byte for byte: tool versions, hashes and wording of explanations
may change without making an example wrong.
"""

import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

pytest.importorskip("fastapi")

pytestmark = pytest.mark.skipif(
    shutil.which("exiftool") is None, reason="ExifTool needed"
)

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "docs" / "api-examples"


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "api_examples", ROOT / "scripts" / "api_examples.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _shape(data: Any) -> Any:
    """Field names everywhere; values only where they carry the meaning."""
    if isinstance(data, dict):
        meaningful = {"verdict", "pipeline", "signal", "state", "message", "code"}
        meaningful |= {"status", "lang", "schema", "fields", "real_format"}
        return {
            k: (v if k in meaningful and not isinstance(v, dict) else _shape(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_shape(v) for v in data]
    return type(data).__name__


@pytest.fixture(scope="module")
def generated() -> dict[str, Any]:
    examples: dict[str, Any] = _script().generate()
    return examples


def test_every_example_is_committed_and_none_is_stale(
    generated: dict[str, Any],
) -> None:
    committed = {p.stem for p in EXAMPLES.glob("*.json")}
    assert committed == set(generated), "run `uv run python scripts/api_examples.py`"


def test_examples_match_the_api(generated: dict[str, Any]) -> None:
    for name, data in generated.items():
        committed = json.loads((EXAMPLES / f"{name}.json").read_text("utf-8"))
        assert _shape(committed) == _shape(data), (
            f"{name}.json is out of date: run `uv run python scripts/api_examples.py`"
        )


def test_examples_cover_every_verdict_and_state(generated: dict[str, Any]) -> None:
    analyses = [d for d in generated.values() if "integrity" in d]
    verdicts = {d["integrity"]["verdict"] for d in analyses}
    states = {r["state"] for d in analyses for r in d["results"]}
    assert verdicts == {"original", "reprocessed", "undetermined"}
    assert states == {"consistent", "to_check", "suspicious", "unverifiable"}
    assert any(d["integrity"]["pipeline"] for d in analyses)
    assert any(d["thumbnail"] for d in analyses)
