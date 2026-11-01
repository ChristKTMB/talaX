import re
from pathlib import Path

import pytest

from talax.i18n import (
    Language,
    Localized,
    Message,
    catalog,
    default_language,
    placeholders,
    text,
    translate,
)

SRC = Path(__file__).parent.parent / "src" / "talax"


def test_both_catalogs_have_exactly_the_same_keys() -> None:
    assert set(catalog(Language.EN)) == set(catalog(Language.FR))


@pytest.mark.parametrize("key", sorted(catalog(Language.EN)))
def test_every_message_is_complete_in_both_languages(key: str) -> None:
    en, fr = catalog(Language.EN)[key], catalog(Language.FR)[key]
    assert en.strip() and fr.strip()
    assert placeholders(en) == placeholders(fr), "same values to insert"


def test_every_literal_key_in_the_code_exists() -> None:
    used: set[str] = set()
    for path in SRC.rglob("*.py"):
        used |= set(re.findall(r'Message\(\s*"([a-z0-9_.]+)"', path.read_text()))
        used |= set(re.findall(r'text\(\s*"([a-z0-9_.]+)"', path.read_text()))
    template = (SRC / "templates" / "report.html.j2").read_text()
    used |= set(re.findall(r't\("([a-z0-9_.]+)"', template))
    assert used, "the scan found nothing"
    assert used <= set(catalog(Language.EN)), sorted(used - set(catalog(Language.EN)))


def test_nested_messages_and_lists_are_translated() -> None:
    inner = Message("compass.E")
    outer = Message("c2pa.about", {"parts": [Message("c2pa.about.ai_declared")]})
    assert translate(inner, Language.FR) == "l'est"
    assert "générée par une IA" in translate(outer, Language.FR)


def test_french_number_formatting() -> None:
    nnbsp = "\u202f"  # French thousands separator
    assert (
        text("ui.cli.size", Language.FR, size=3946045)
        == f"3{nnbsp}946{nnbsp}045 octets"
    )
    assert text("ui.cli.size", Language.EN, size=3946045) == "3,946,045 bytes"
    assert text("duration.hours", Language.FR, n=0.5) == "0,5 h"


def test_localized_values() -> None:
    value = Localized(en="photo sent", fr="photo envoyée")
    assert value.get(Language.FR) == "photo envoyée"
    with pytest.raises(ValueError):
        Localized(en="only English", fr=" ")


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"LANG": "fr_FR.UTF-8"}, Language.FR),
        ({"LANG": "fr_CD.UTF-8"}, Language.FR),
        ({"LANG": "en_US.UTF-8"}, Language.EN),
        ({"LC_ALL": "fr_BE.UTF-8", "LANG": "en_US.UTF-8"}, Language.FR),
        ({}, Language.EN),
    ],
)
def test_default_language(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str], expected: Language
) -> None:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        monkeypatch.delenv(var, raising=False)
    for var, value in env.items():
        monkeypatch.setenv(var, value)
    assert default_language() is expected
