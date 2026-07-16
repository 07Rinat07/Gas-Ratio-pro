"""Application boundary for three-language localization."""

from __future__ import annotations

from pathlib import Path

from core.internationalization import LocalizationService


class LocalizationApplicationService:
    def __init__(self, *, catalogs_dir: Path | str, language: str = "ru") -> None:
        self._service = LocalizationService.from_directory(
            catalogs_dir, language=language, fallback_language="ru"
        )

    @property
    def language(self) -> str:
        return self._service.language

    def set_language(self, language: str) -> str:
        return self._service.set_language(language)

    def translate(self, key: str, /, **values: object) -> str:
        return self._service.translate(key, **values)

    __call__ = translate

    def health(self) -> dict[str, object]:
        snapshot = self._service.snapshot()
        snapshot["status"] = "ok"
        return snapshot
