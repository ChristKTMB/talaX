"""User-facing text in English and French, the only two languages of Tala X.

The analysis never stores a finished sentence: it stores a `Message` (a key and
the values to insert), and the sentence is written in the reader's language
when it is displayed. Catalogs live in `talax/data/messages/<lang>.yaml`.
"""

from __future__ import annotations

import functools
import os
import string
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from importlib.resources import files
from types import MappingProxyType
from typing import Any

import yaml


class Language(StrEnum):
    EN = "en"
    FR = "fr"


@functools.cache
def catalog(lang: Language) -> Mapping[str, str]:
    path = files("talax") / "data" / "messages" / f"{lang}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return MappingProxyType({str(k): str(v).strip() for k, v in raw.items()})


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


@dataclass(frozen=True, slots=True)
class Message:
    """A translatable sentence: a catalog key and the values it needs."""

    key: str
    params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        text = catalog(Language.EN).get(self.key)
        if text is None:
            raise ValueError(f"unknown message key {self.key!r}")
        missing = placeholders(text) - self.params.keys()
        if missing:
            raise ValueError(f"message {self.key!r} lacks {sorted(missing)}")
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))


@dataclass(frozen=True, slots=True)
class Localized:
    """A value that has its own wording in each language (e.g. from a YAML file)."""

    en: str
    fr: str

    def __post_init__(self) -> None:
        if not self.en.strip() or not self.fr.strip():
            raise ValueError("a localized text needs an English and a French version")

    def get(self, lang: Language) -> str:
        return self.fr if lang is Language.FR else self.en


def translate(message: Message, lang: Language = Language.EN) -> str:
    return _Formatter(lang).format(catalog(lang)[message.key], **message.params)


def text(key: str, lang: Language = Language.EN, **params: Any) -> str:
    """Translate a catalog entry directly (labels, headings)."""
    return translate(Message(key, params), lang)


def default_language() -> Language:
    """The system language when it is French, English otherwise."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(var, "")
        if value:
            return Language.FR if value.lower().startswith("fr") else Language.EN
    return Language.EN


class _Formatter(string.Formatter):
    def __init__(self, lang: Language) -> None:
        self.lang = lang

    def format_field(self, value: Any, format_spec: str) -> str:
        if isinstance(value, Message):
            return translate(value, self.lang)
        if isinstance(value, Localized):
            return value.get(self.lang)
        if isinstance(value, list | tuple) and all(
            isinstance(v, Message) for v in value
        ):
            separator = " ; " if self.lang is Language.FR else "; "
            return separator.join(translate(v, self.lang) for v in value)
        result = str(super().format_field(value, format_spec))
        if self.lang is Language.FR and isinstance(value, int | float):
            # French writes 0,5 and 3 000.
            result = result.replace(",", "\u202f").replace(".", ",")
        return result
