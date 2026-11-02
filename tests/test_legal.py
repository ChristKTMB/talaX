"""The terms and privacy policy exist in both languages and stay aligned."""

import re
from pathlib import Path

import pytest

LEGAL = Path(__file__).resolve().parent.parent / "docs" / "legal"


@pytest.mark.parametrize("doc", ["terms", "privacy"])
def test_both_languages_have_the_same_sections(doc: str) -> None:
    en = (LEGAL / f"{doc}.en.md").read_text("utf-8")
    fr = (LEGAL / f"{doc}.fr.md").read_text("utf-8")

    def numbers(text: str) -> list[str]:
        return re.findall(r"^## (\d+)\.", text, re.MULTILINE)

    assert numbers(en) == numbers(fr) != []
    for text in (en, fr):
        assert "contact@talax.online" in text
        assert "Christ KATUMBA KATUMBA" in text
