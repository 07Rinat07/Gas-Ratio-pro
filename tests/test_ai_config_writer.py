from __future__ import annotations

import json

import pytest

from ai.config_writer import (
    build_offline_docs_config,
    build_ollama_config,
    configure_offline_docs,
    configure_ollama,
)
from ai.settings import load_ai_settings


def test_build_offline_docs_config_preserves_privacy_and_ollama_section():
    config = build_offline_docs_config(
        {
            "provider": "ollama",
            "privacy": {
                "send_full_table": False,
                "send_selected_interval_only": False,
            },
            "ollama": {
                "base_url": "http://localhost:11434/",
                "model": "qwen3:4b",
                "timeout_seconds": 30,
            },
        }
    )

    assert config["provider"] == "offline-docs"
    assert config["privacy"]["send_selected_interval_only"] is False
    assert config["ollama"]["base_url"] == "http://localhost:11434"
    assert config["ollama"]["model"] == "qwen3:4b"


def test_build_ollama_config_requires_model_and_positive_timeout():
    with pytest.raises(ValueError, match="model"):
        build_ollama_config(model="")

    with pytest.raises(ValueError, match="timeout"):
        build_ollama_config(model="qwen3:4b", timeout_seconds=0)


def test_configure_ollama_writes_valid_ai_config(tmp_path):
    path = tmp_path / "ai.json"
    path.write_text(
        json.dumps(
            {
                "provider": "offline-docs",
                "privacy": {
                    "send_full_table": False,
                    "send_selected_interval_only": True,
                },
            }
        ),
        encoding="utf-8",
    )

    configure_ollama(path, model="qwen3:4b", base_url="http://localhost:11434/", timeout_seconds=45)
    settings = load_ai_settings(path)

    assert settings.provider == "ollama"
    assert settings.ollama.model == "qwen3:4b"
    assert settings.ollama.base_url == "http://localhost:11434"
    assert settings.ollama.timeout_seconds == 45


def test_configure_offline_docs_writes_valid_ai_config(tmp_path):
    path = tmp_path / "ai.json"
    configure_ollama(path, model="qwen3:4b")

    configure_offline_docs(path)
    settings = load_ai_settings(path)

    assert settings.provider == "offline-docs"
    assert settings.ollama.model == "qwen3:4b"
