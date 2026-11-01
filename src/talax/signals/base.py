"""Signal contract and the orchestrator that runs signals."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from talax.i18n import Language, Message, catalog
from talax.model import Context, Result, State


@runtime_checkable
class Signal(Protocol):
    id: str
    name: str

    def is_relevant(self, ctx: Context) -> bool:
        """Whether the signal makes sense for this kind of file.

        Only for file-type mismatches (JPEG tables on a PNG, photo signal on a
        video). Missing data is NOT a reason to return False: the signal must
        run and return UNVERIFIABLE, so the report shows what was not checked.
        """
        ...

    def evaluate(self, ctx: Context) -> Result:
        """Return a verdict. Exceptions are tolerated but treated as bugs."""
        ...


def run_signals(ctx: Context, signals: Iterable[Signal]) -> tuple[Result, ...]:
    """Run every relevant signal. Never raises because of a signal."""
    signals = tuple(signals)
    ids = [s.id for s in signals]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"duplicate signal ids: {sorted(duplicates)}")

    results: list[Result] = []
    for signal in signals:
        try:
            if not signal.is_relevant(ctx):
                continue
            result = signal.evaluate(ctx)
            if not isinstance(result, Result):
                raise TypeError(f"returned {type(result).__name__}, not Result")
            if result.signal_id != signal.id:
                raise ValueError(f"returned a result for {result.signal_id!r}")
        except Exception as exc:
            result = _internal_error(signal, exc)
        results.append(result)
    return tuple(results)


def _internal_error(signal: Signal, exc: Exception) -> Result:
    name_key = f"signal.{signal.id}"
    name = Message(name_key) if name_key in catalog(Language.EN) else signal.name
    return Result(
        signal_id=signal.id,
        state=State.UNVERIFIABLE,
        message=Message("signal.internal_error", {"signal": name}),
        evidence={"error_type": type(exc).__name__, "error": str(exc)},
    )
