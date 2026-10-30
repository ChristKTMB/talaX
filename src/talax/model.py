"""Domain entities. All of them are immutable once built."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any


def _freeze(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


class State(StrEnum):
    """Verdict of a single signal."""

    CONSISTENT = "consistent"
    TO_CHECK = "to_check"
    SUSPICIOUS = "suspicious"
    # Missing information. Never to be merged with SUSPICIOUS.
    UNVERIFIABLE = "unverifiable"


class IntegrityVerdict(StrEnum):
    """Outcome of the integrity check, which runs before any signal."""

    ORIGINAL = "original"
    REPROCESSED = "reprocessed"
    # Mixed marks: editor export, HEIC converted on share, screenshot...
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class FileInfo:
    sha256: str
    size: int
    declared_format: str | None
    """MIME type implied by the file name extension."""
    real_format: str | None
    """MIME type read from the file content."""


@dataclass(frozen=True, slots=True)
class Metadata:
    """Raw metadata as read from the file, keyed by `Group:Tag`."""

    tags: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", _freeze(self.tags))

    def get(self, key: str) -> Any:
        return self.tags.get(key)


@dataclass(frozen=True, slots=True)
class Declaration:
    """Place and time claimed for the file, typed in by the user (manual mode)."""

    latitude: float
    longitude: float
    taken_at: datetime
    """Naive datetimes are local time at the declared place."""

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"latitude out of range: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"longitude out of range: {self.longitude}")


@dataclass(frozen=True, slots=True)
class IntegrityAssessment:
    verdict: IntegrityVerdict
    explanation: str
    pipeline: str | None = None
    """Identified platform pipeline, e.g. `whatsapp-gallery`, when known."""
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.explanation.strip():
            raise ValueError("an integrity assessment needs an explanation")
        object.__setattr__(self, "evidence", _freeze(self.evidence))


@dataclass(frozen=True, slots=True)
class Context:
    """The single object every signal receives."""

    file: FileInfo
    metadata: Metadata
    integrity: IntegrityAssessment
    declaration: Declaration | None = None


@dataclass(frozen=True, slots=True)
class Result:
    signal_id: str
    state: State
    explanation: str
    """Plain language, never empty: a flag without explanation is never shown."""
    evidence: Mapping[str, Any] = field(default_factory=dict)
    """Raw values that led to the verdict, so the report can show the reasoning."""
    confidence: float | None = None
    """Only where a real probability exists; None for deterministic signals."""

    def __post_init__(self) -> None:
        if not self.explanation.strip():
            raise ValueError(f"signal {self.signal_id!r} returned no explanation")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence out of [0, 1]: {self.confidence}")
        object.__setattr__(self, "evidence", _freeze(self.evidence))


@dataclass(frozen=True, slots=True)
class Analysis:
    file: FileInfo
    integrity: IntegrityAssessment
    results: tuple[Result, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
