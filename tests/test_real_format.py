import dataclasses

import pytest

from talax import Context, Metadata, State
from talax.signals import RealFormat


def with_formats(
    ctx: Context,
    declared: str | None,
    real: str | None,
    exiftool: str | None = None,
) -> Context:
    file = dataclasses.replace(ctx.file, declared_format=declared, real_format=real)
    tags = {"File:MIMEType": exiftool} if exiftool else {}
    return dataclasses.replace(ctx, file=file, metadata=Metadata(tags))


@pytest.mark.parametrize(
    ("declared", "real", "exiftool", "state"),
    [
        ("image/jpeg", "image/jpeg", "image/jpeg", State.CONSISTENT),
        ("image/jpeg", "image/jpeg", None, State.CONSISTENT),
        ("image/heic", "image/heif", "image/heif", State.CONSISTENT),
        ("image/jpeg", "image/png", "image/png", State.TO_CHECK),
        ("image/jpeg", "image/jpeg", "image/png", State.TO_CHECK),
        (None, "image/jpeg", "image/jpeg", State.UNVERIFIABLE),
        ("image/jpeg", None, None, State.UNVERIFIABLE),
    ],
)
def test_verdicts(
    ctx: Context,
    declared: str | None,
    real: str | None,
    exiftool: str | None,
    state: State,
) -> None:
    result = RealFormat().evaluate(with_formats(ctx, declared, real, exiftool))
    assert result.state is state
    assert result.evidence["declared"] == declared
    assert result.evidence["real"] == real


def test_a_mismatch_is_never_suspicious(ctx: Context) -> None:
    result = RealFormat().evaluate(with_formats(ctx, "image/jpeg", "image/png"))
    assert result.state is not State.SUSPICIOUS
    assert "PNG" in result.explanation
