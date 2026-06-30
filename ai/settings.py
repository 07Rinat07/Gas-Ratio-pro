from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_AI_PROVIDERS = {"offline-docs", "ollama"}


@dataclass(frozen=True)
class OllamaSettings:
    base_url: str = "http://localhost:11434"
    model: str = ""
    timeout_seconds: int = 60


@dataclass(frozen=True)
class AiPrivacySettings:
    send_full_table: bool = False
    send_selected_interval_only: bool = True


@dataclass(frozen=True)
class AiSettings:
    provider: str = "offline-docs"
    privacy: AiPrivacySettings = AiPrivacySettings()
    ollama: OllamaSettings = OllamaSettings()


def default_ai_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "ai.json"


def _read_bool(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _read_int(value: object, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def load_ai_settings(path: str | Path | None = None) -> AiSettings:
    config_path = Path(path) if path is not None else default_ai_config_path()
    if not config_path.exists():
        return AiSettings()

    with config_path.open("r", encoding="utf-8") as file:
        raw_config = json.load(file)

    if not isinstance(raw_config, dict):
        raise ValueError("AI config root must be an object.")

    provider = str(raw_config.get("provider", "offline-docs")).strip() or "offline-docs"
    if provider not in SUPPORTED_AI_PROVIDERS:
        raise ValueError(f"Unsupported AI provider: {provider}")

    raw_privacy = raw_config.get("privacy", {})
    if not isinstance(raw_privacy, dict):
        raise ValueError("AI config privacy section must be an object.")

    raw_ollama = raw_config.get("ollama", {})
    if not isinstance(raw_ollama, dict):
        raise ValueError("AI config ollama section must be an object.")

    return AiSettings(
        provider=provider,
        privacy=AiPrivacySettings(
            send_full_table=_read_bool(raw_privacy.get("send_full_table"), False),
            send_selected_interval_only=_read_bool(
                raw_privacy.get("send_selected_interval_only"),
                True,
            ),
        ),
        ollama=OllamaSettings(
            base_url=str(raw_ollama.get("base_url", "http://localhost:11434")).rstrip("/"),
            model=str(raw_ollama.get("model", "")).strip(),
            timeout_seconds=_read_int(raw_ollama.get("timeout_seconds"), 60),
        ),
    )
