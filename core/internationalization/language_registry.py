"""Supported-language registry for the GAS RATIO PRO user experience.

Language codes are deliberately restricted to an explicit allow-list.  This
prevents arbitrary paths or untrusted locale names from reaching catalog I/O.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

DEFAULT_LANGUAGE = "ru"


@dataclass(frozen=True, slots=True)
class LanguageDefinition:
    code: str
    native_name: str
    english_name: str
    direction: str = "ltr"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


SUPPORTED_LANGUAGES: dict[str, LanguageDefinition] = {
    "ru": LanguageDefinition("ru", "Русский", "Russian"),
    "kk": LanguageDefinition("kk", "Қазақша", "Kazakh"),
    "en": LanguageDefinition("en", "English", "English"),
}


def normalize_language(value: object, *, fallback: str = DEFAULT_LANGUAGE) -> str:
    """Return a supported BCP-47 base language or a safe fallback.

    Values such as ``kk-KZ`` and ``en_US`` resolve to ``kk`` and ``en``.
    Unknown or empty values never escape the supported-language allow-list.
    """

    raw = str(value or "").strip().lower().replace("_", "-")
    base = raw.split("-", 1)[0]
    if base in SUPPORTED_LANGUAGES:
        return base
    return fallback if fallback in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
