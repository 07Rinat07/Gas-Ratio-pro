from __future__ import annotations

import json

import pandas as pd
import pytest

from ai.assistant import LocalAssistant, build_interval_context
from ai.factory import build_provider
from ai.knowledge_base import DocumentationKnowledgeBase
from ai.ollama_client import OllamaProvider
from ai.prompts import INTERPRETATION_DISCLAIMER
from ai.provider import ProviderRequest
from ai.settings import load_ai_settings


def test_knowledge_base_finds_formula_docs():
    kb = DocumentationKnowledgeBase()

    context, sources = kb.build_context("Как считается Wh?")

    assert "Wh" in context
    assert "docs/formulas.md" in sources


def test_knowledge_base_uses_manifest_metadata_for_ai_topics():
    kb = DocumentationKnowledgeBase()

    results = kb.search("Как подготовить ollama модель без интернета?")

    assert results
    assert results[0].chunk.source in {
        "config/knowledge_qa.json#ollama_offline_preparation",
        "docs/ai_usage.md",
        "docs/local_model_profiles.md",
        "docs/troubleshooting.md",
    }
    assert "ollama" in results[0].chunk.topics


def test_knowledge_base_uses_qa_examples_for_common_questions():
    kb = DocumentationKnowledgeBase()

    context, sources = kb.build_context("Почему Wh стал NaN из-за C2?")

    assert "Проверенный ответ" in context
    assert "config/knowledge_qa.json#wh_nan_missing_components" in sources
    assert "Не заменять NaN нулем" in context


def test_local_assistant_answer_contains_disclaimer_and_sources():
    assistant = LocalAssistant()

    result = assistant.answer("Какие колонки нужны для расчета Wh?")

    assert INTERPRETATION_DISCLAIMER in result.answer
    assert result.provider_name == "offline-docs"
    assert result.sources


def test_interval_context_exposes_only_safe_fields():
    row = pd.Series(
        {
            "depth": 1000,
            "wh": 12.5,
            "bh": 20,
            "c1": 80,
            "c2": 10,
            "interpretation": "Газовая залежь",
        }
    )

    context = build_interval_context(row)

    assert "depth: 1000" in context
    assert "wh: 12.5" in context
    assert "interpretation: Газовая залежь" in context
    assert "c1:" not in context
    assert "c2:" not in context


def test_load_ai_settings_from_json(tmp_path):
    config_path = tmp_path / "ai.json"
    config_path.write_text(
        json.dumps(
            {
                "provider": "ollama",
                "privacy": {
                    "send_full_table": False,
                    "send_selected_interval_only": True,
                },
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model": "local-model",
                    "timeout_seconds": 10,
                },
            }
        ),
        encoding="utf-8",
    )

    settings = load_ai_settings(config_path)

    assert settings.provider == "ollama"
    assert settings.ollama.model == "local-model"
    assert settings.ollama.timeout_seconds == 10
    assert build_provider(settings).provider_name == "ollama"


def test_invalid_ai_provider_is_rejected(tmp_path):
    config_path = tmp_path / "ai.json"
    config_path.write_text(json.dumps({"provider": "cloud-api"}), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported AI provider"):
        load_ai_settings(config_path)


def test_ollama_provider_uses_local_http_post_and_adds_disclaimer():
    calls = []

    def fake_http_post(url: str, payload: dict, timeout_seconds: int) -> dict:
        calls.append((url, payload, timeout_seconds))
        return {"response": "Ответ локальной модели."}

    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model="local-model",
        timeout_seconds=5,
        http_post=fake_http_post,
    )
    response = provider.generate(
        ProviderRequest(
            question="Что такое Wh?",
            prompt="prompt",
            context="context",
        )
    )

    assert calls[0][0] == "http://localhost:11434/api/generate"
    assert calls[0][1]["model"] == "local-model"
    assert calls[0][1]["options"]["num_predict"] == 160
    assert response.provider_name == "ollama"
    assert "Ответ локальной модели." in response.answer
    assert INTERPRETATION_DISCLAIMER in response.answer


def test_ollama_provider_without_model_returns_clear_message():
    provider = OllamaProvider(model="")

    response = provider.generate(
        ProviderRequest(
            question="Что такое Wh?",
            prompt="prompt",
            context="context",
        )
    )

    assert "модель Ollama не настроена" in response.answer
    assert INTERPRETATION_DISCLAIMER in response.answer


def test_ollama_provider_timeout_returns_local_docs_fallback():
    def timeout_http_post(url: str, payload: dict, timeout_seconds: int) -> dict:
        raise TimeoutError("slow model")

    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model="local-model",
        timeout_seconds=180,
        http_post=timeout_http_post,
    )
    response = provider.generate(
        ProviderRequest(
            question="Что делать, если колонки не сопоставились?",
            prompt="prompt",
            context="Проверенный ответ: Проверьте строку заголовков и mapping колонок.",
        )
    )

    assert "не успел ответить за 180 сек" in response.answer
    assert "Проверьте строку заголовков" in response.answer
    assert INTERPRETATION_DISCLAIMER in response.answer
