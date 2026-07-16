"""Payload-light translation service with deterministic fallback behaviour."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from typing import Mapping

from core.internationalization.language_registry import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    normalize_language,
)


@dataclass(frozen=True, slots=True)
class CatalogDiagnostics:
    language: str
    fallback_language: str
    key_count: int
    missing_from_language: tuple[str, ...]
    extra_in_language: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "fallback_language": self.fallback_language,
            "key_count": self.key_count,
            "missing_count": len(self.missing_from_language),
            "extra_count": len(self.extra_in_language),
            "missing_keys": list(self.missing_from_language),
            "extra_keys": list(self.extra_in_language),
        }


class LocalizationService:
    """Translate stable message keys without evaluating catalog content."""

    def __init__(
        self,
        catalogs: Mapping[str, Mapping[str, str]],
        *,
        language: str = DEFAULT_LANGUAGE,
        fallback_language: str = DEFAULT_LANGUAGE,
    ) -> None:
        self._fallback_language = normalize_language(fallback_language)
        self._language = normalize_language(language, fallback=self._fallback_language)
        self._catalogs = self._normalize_catalogs(catalogs)
        if self._fallback_language not in self._catalogs:
            raise ValueError("Fallback translation catalog is required.")

    @classmethod
    def from_directory(
        cls,
        directory: Path | str,
        *,
        language: str = DEFAULT_LANGUAGE,
        fallback_language: str = DEFAULT_LANGUAGE,
    ) -> "LocalizationService":
        root = Path(directory)
        catalogs: dict[str, dict[str, str]] = {}
        for code in SUPPORTED_LANGUAGES:
            path = root / f"{code}.json"
            if not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"Translation catalog must be a JSON object: {path.name}")
            catalogs[code] = payload
        return cls(catalogs, language=language, fallback_language=fallback_language)

    @staticmethod
    def _normalize_catalogs(
        catalogs: Mapping[str, Mapping[str, str]],
    ) -> dict[str, dict[str, str]]:
        normalized: dict[str, dict[str, str]] = {}
        for raw_code, raw_catalog in catalogs.items():
            code = normalize_language(raw_code)
            if code != str(raw_code).strip().lower().replace("_", "-").split("-", 1)[0]:
                continue
            catalog: dict[str, str] = {}
            for raw_key, raw_value in raw_catalog.items():
                key = str(raw_key).strip()
                if not key or not isinstance(raw_value, str):
                    raise ValueError(f"Invalid translation entry in catalog {code!r}.")
                catalog[key] = raw_value
            normalized[code] = catalog
        return normalized

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> str:
        self._language = normalize_language(language, fallback=self._fallback_language)
        return self._language

    def translate(self, key: str, /, **values: object) -> str:
        clean_key = str(key).strip()
        if not clean_key:
            raise ValueError("Translation key must not be empty.")
        template = self._catalogs.get(self._language, {}).get(clean_key)
        if template is None:
            template = self._catalogs[self._fallback_language].get(clean_key)
        if template is None:
            return clean_key
        if not values:
            return template
        required = {
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name
        }
        missing = required.difference(values)
        if missing:
            # A broken UI string is safer than raising during a Streamlit rerun.
            return template
        safe_values = {name: str(value) for name, value in values.items()}
        try:
            return template.format_map(safe_values)
        except (KeyError, ValueError, IndexError):
            return template

    __call__ = translate

    def diagnostics(self, language: str | None = None) -> CatalogDiagnostics:
        code = normalize_language(language or self._language, fallback=self._fallback_language)
        fallback_keys = set(self._catalogs[self._fallback_language])
        language_keys = set(self._catalogs.get(code, {}))
        return CatalogDiagnostics(
            language=code,
            fallback_language=self._fallback_language,
            key_count=len(language_keys),
            missing_from_language=tuple(sorted(fallback_keys - language_keys)),
            extra_in_language=tuple(sorted(language_keys - fallback_keys)),
        )

    def snapshot(self) -> dict[str, object]:
        return {
            "language": self._language,
            "fallback_language": self._fallback_language,
            "supported_languages": [
                SUPPORTED_LANGUAGES[code].to_dict() for code in SUPPORTED_LANGUAGES
            ],
            "catalogs": {
                code: self.diagnostics(code).to_dict() for code in SUPPORTED_LANGUAGES
            },
        }
