"""Tala X — see beyond the pixel.

from pathlib import Path
from talax import analyze

analysis = analyze(Path("photo.jpg"))
print(analysis.integrity.verdict)
for result in analysis.results:
    print(result.signal_id, result.state, result.explanation)
"""

from importlib.metadata import version as _version

from talax.analysis import analyze
from talax.model import (
    Analysis,
    Context,
    Declaration,
    FileInfo,
    IntegrityAssessment,
    IntegrityVerdict,
    Metadata,
    Observation,
    Result,
    Sky,
    State,
)
from talax.signals import Signal, run_signals

__version__ = _version("talax")

__all__ = [
    "Analysis",
    "Context",
    "Declaration",
    "FileInfo",
    "IntegrityAssessment",
    "IntegrityVerdict",
    "Metadata",
    "Observation",
    "Result",
    "Signal",
    "Sky",
    "State",
    "__version__",
    "analyze",
    "run_signals",
]
