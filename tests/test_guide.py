"""The user guide (docs/guide/) says only what exists, in both languages."""

import re
from pathlib import Path

import pytest
import typer

from talax.cli import app

GUIDE = Path(__file__).resolve().parent.parent / "docs" / "guide"
PAGES = ["site", "cli", "report"]
LANGS = ["en", "fr"]


def text(page: str, lang: str) -> str:
    return (GUIDE / f"{page}.{lang}.md").read_text("utf-8")


def commands() -> dict[str, set[str]]:
    """Every talax command and the options it accepts."""
    group = typer.main.get_command(app)
    found: dict[str, set[str]] = {}
    for name, command in group.commands.items():  # type: ignore[attr-defined]
        found[name] = {opt for p in command.params for opt in getattr(p, "opts", [])}
        found[name].add("--help")
    return found


@pytest.mark.parametrize("page", PAGES)
def test_both_languages_have_the_same_sections(page: str) -> None:
    def numbers(content: str) -> list[str]:
        return re.findall(r"^## (\d+)\.", content, re.MULTILINE)

    assert numbers(text(page, "en")) == numbers(text(page, "fr")) != []


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("page", PAGES)
def test_every_command_and_option_cited_exists(page: str, lang: str) -> None:
    known = commands()
    every_option = set().union(*known.values())
    content = text(page, lang)
    for command in re.findall(r"\btalax ([a-z]+)\b", content):
        assert command in known, command
    # An option written in a "talax <command> ..." line belongs to that command.
    for match in re.finditer(r"talax ([a-z]+) [^\n`|]*", content):
        name, *rest = match.group(0).split()[1:]
        for option in re.findall(r"(?<![\w-])--[a-z][a-z-]*", " ".join(rest)):
            assert option in known[name], f"talax {name} {option}"
    # Anywhere else, an option must exist in some command.
    for option in re.findall(r"`(--[a-z][a-z-]*)", content):
        assert option in every_option, option


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("page", PAGES)
def test_links_between_documents_lead_somewhere(page: str, lang: str) -> None:
    for target in re.findall(r"\]\(([^)#]+\.md)\)", text(page, lang)):
        assert (GUIDE / target).resolve().is_file(), target
        assert target.endswith(f".{lang}.md"), f"{target} is in another language"


def test_the_sky_and_conditions_values_cited_exist() -> None:
    for lang in LANGS:
        content = text("cli", lang)
        assert re.search(r"`day`.*`twilight`.*`night`", content)
        assert re.search(r"`rain`.*`snow`.*`overcast`.*`clear`", content)
