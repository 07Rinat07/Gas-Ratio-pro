"""Persistent user locale preference with atomic, allow-listed storage."""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from core.internationalization.language_registry import DEFAULT_LANGUAGE, normalize_language
from core.storage_lifecycle import DeleteEngine


class UserLocalePreferenceService:
    SCHEMA = "gas-ratio-pro.user-locale-preference"
    VERSION = 1

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._delete_engine = DeleteEngine(attempts=2, delay_seconds=0.0)

    def load(self) -> str:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
            return DEFAULT_LANGUAGE
        if not isinstance(payload, dict) or payload.get("schema") != self.SCHEMA:
            return DEFAULT_LANGUAGE
        return normalize_language(payload.get("language"))

    def save(self, language: object) -> str:
        normalized = normalize_language(language)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": self.SCHEMA,
            "version": self.VERSION,
            "language": normalized,
        }
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temp_path = Path(handle.name)
        try:
            os.replace(temp_path, self.path)
        finally:
            self._delete_engine.delete_path(temp_path, missing_ok=True)
        return normalized

    def snapshot(self) -> dict[str, object]:
        language = self.load()
        return {
            "status": "ok",
            "language": language,
            "path": str(self.path),
            "exists": self.path.exists(),
            "schema": self.SCHEMA,
            "version": self.VERSION,
        }
