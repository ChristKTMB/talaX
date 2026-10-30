from dataclasses import dataclass

import pytest

from talax import Context, Result, Signal, State, run_signals


@dataclass
class FakeSignal:
    id: str
    name: str = "Fake"
    relevant: bool = True
    outcome: Result | Exception | object | None = None

    def is_relevant(self, ctx: Context) -> bool:
        return self.relevant

    def evaluate(self, ctx: Context) -> Result:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        if self.outcome is not None:
            return self.outcome  # type: ignore[return-value]
        return Result(self.id, State.CONSISTENT, "Everything matches.")


class RaisingRelevance(FakeSignal):
    def is_relevant(self, ctx: Context) -> bool:
        raise RuntimeError("boom")


def test_fake_satisfies_the_contract() -> None:
    assert isinstance(FakeSignal("a"), Signal)


def test_results_follow_signal_order(ctx: Context) -> None:
    results = run_signals(ctx, [FakeSignal("a"), FakeSignal("b")])
    assert [r.signal_id for r in results] == ["a", "b"]


def test_irrelevant_signal_is_left_out(ctx: Context) -> None:
    results = run_signals(ctx, [FakeSignal("a", relevant=False), FakeSignal("b")])
    assert [r.signal_id for r in results] == ["b"]


@pytest.mark.parametrize(
    "signal",
    [
        FakeSignal("a", outcome=RuntimeError("boom")),
        FakeSignal("a", outcome="not a result"),
        FakeSignal("a", outcome=Result("other", State.CONSISTENT, "ok")),
        RaisingRelevance("a"),
    ],
)
def test_a_broken_signal_becomes_unverifiable(ctx: Context, signal: Signal) -> None:
    (result,) = run_signals(ctx, [signal, FakeSignal("b")])[:1]

    assert result.signal_id == "a"
    assert result.state is State.UNVERIFIABLE
    assert "internal error" in result.explanation
    assert "error_type" in result.evidence


def test_one_broken_signal_does_not_stop_the_others(ctx: Context) -> None:
    results = run_signals(
        ctx, [FakeSignal("a", outcome=RuntimeError()), FakeSignal("b")]
    )
    assert [r.state for r in results] == [State.UNVERIFIABLE, State.CONSISTENT]


def test_empty_explanation_inside_a_signal_becomes_unverifiable(
    ctx: Context,
) -> None:
    class Silent(FakeSignal):
        def evaluate(self, ctx: Context) -> Result:
            return Result(self.id, State.SUSPICIOUS, "")

    (result,) = run_signals(ctx, [Silent("a")])
    assert result.state is State.UNVERIFIABLE


def test_duplicate_ids_are_rejected(ctx: Context) -> None:
    with pytest.raises(ValueError, match="duplicate"):
        run_signals(ctx, [FakeSignal("a"), FakeSignal("a")])
