from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai.settings import load_ai_settings


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 60


def _default_config() -> dict[str, Any]:
    return {
        "provider": "offline-docs",
        "privacy": {
            "send_full_table": False,
            "send_selected_interval_only": True,
        },
        "ollama": {
            "base_url": DEFAULT_OLLAMA_BASE_URL,
            "model": "",
            "timeout_seconds": DEFAULT_OLLAMA_TIMEOUT_SECONDS,
        },
    }


def read_ai_config_document(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return _default_config()

    with config_path.open("r", encoding="utf-8") as file:
        raw_config = json.load(file)

    if not isinstance(raw_config, dict):
        raise ValueError("AI config root must be an object.")
    return raw_config


def _privacy_section(raw_config: dict[str, Any]) -> dict[str, bool]:
    privacy = raw_config.get("privacy")
    if not isinstance(privacy, dict):
        privacy = {}
    return {
        "send_full_table": privacy.get("send_full_table") if isinstance(privacy.get("send_full_table"), bool) else False,
        "send_selected_interval_only": (
            privacy.get("send_selected_interval_only")
            if isinstance(privacy.get("send_selected_interval_only"), bool)
            else True
        ),
    }


def _ollama_section(raw_config: dict[str, Any]) -> dict[str, Any]:
    ollama = raw_config.get("ollama")
    if not isinstance(ollama, dict):
        ollama = {}
    return {
        "base_url": str(ollama.get("base_url", DEFAULT_OLLAMA_BASE_URL)).rstrip("/") or DEFAULT_OLLAMA_BASE_URL,
        "model": str(ollama.get("model", "")).strip(),
        "timeout_seconds": _positive_int(ollama.get("timeout_seconds"), DEFAULT_OLLAMA_TIMEOUT_SECONDS),
    }


def _positive_int(value: object, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def build_offline_docs_config(existing_config: dict[str, Any] | None = None) -> dict[str, Any]:
    raw_config = existing_config or _default_config()
    return {
        "provider": "offline-docs",
        "privacy": _privacy_section(raw_config),
        "ollama": _ollama_section(raw_config),
    }


def build_ollama_config(
    model: str,
    existing_config: dict[str, Any] | None = None,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: int = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    clean_model = model.strip()
    if not clean_model:
        raise ValueError("Ollama model must be a non-empty string.")

    clean_base_url = base_url.rstrip("/")
    if not clean_base_url:
        raise ValueError("Ollama base_url must be a non-empty string.")

    timeout = int(timeout_seconds)
    if timeout <= 0:
        raise ValueError("Ollama timeout_seconds must be positive.")

    raw_config = existing_config or _default_config()
    return {
        "provider": "ollama",
        "privacy": _privacy_section(raw_config),
        "ollama": {
            "base_url": clean_base_url,
            "model": clean_model,
            "timeout_seconds": timeout,
        },
    }


def write_ai_config(path: str | Path, config: dict[str, Any]) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    load_ai_settings(config_path)


def configure_offline_docs(path: str | Path) -> dict[str, Any]:
    current_config = read_ai_config_document(path)
    config = build_offline_docs_config(current_config)
    write_ai_config(path, config)
    return config


def configure_ollama(
    path: str | Path,
    model: str,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: int = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    current_config = read_ai_config_document(path)
    config = build_ollama_config(
        model=model,
        existing_config=current_config,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )
    write_ai_config(path, config)
    return config
