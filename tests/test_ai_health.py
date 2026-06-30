from __future__ import annotations

from ai.health import check_ai_runtime_status
from ai.settings import AiSettings, OllamaSettings


def test_offline_docs_status_is_ready():
    status = check_ai_runtime_status(AiSettings(provider="offline-docs"))

    assert status.ready
    assert status.provider == "offline-docs"
    assert "не требуются" in status.message


def test_ollama_status_requires_model_name():
    status = check_ai_runtime_status(AiSettings(provider="ollama"))

    assert not status.ready
    assert "имя модели" in status.message


def test_ollama_status_ready_when_model_is_available():
    def fake_http_get(url: str, timeout_seconds: int) -> dict:
        return {"models": [{"name": "local-model"}, {"name": "other-model"}]}

    status = check_ai_runtime_status(
        AiSettings(
            provider="ollama",
            ollama=OllamaSettings(model="local-model"),
        ),
        http_get=fake_http_get,
    )

    assert status.ready
    assert status.available_models == ("local-model", "other-model")
    assert "local-model" in status.message


def test_ollama_status_reports_missing_model():
    def fake_http_get(url: str, timeout_seconds: int) -> dict:
        return {"models": [{"name": "another-model"}]}

    status = check_ai_runtime_status(
        AiSettings(
            provider="ollama",
            ollama=OllamaSettings(model="local-model"),
        ),
        http_get=fake_http_get,
    )

    assert not status.ready
    assert status.available_models == ("another-model",)
    assert "не найдена локально" in status.message
