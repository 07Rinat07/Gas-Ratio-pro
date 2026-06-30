from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from ai.settings import AiSettings


HttpGet = Callable[[str, int], dict]


@dataclass(frozen=True)
class AiRuntimeStatus:
    provider: str
    ready: bool
    message: str
    available_models: tuple[str, ...] = ()


def default_http_get(url: str, timeout_seconds: int) -> dict:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response_text = response.read().decode("utf-8")
    return json.loads(response_text)


def _extract_ollama_model_names(response: dict) -> tuple[str, ...]:
    models = response.get("models", [])
    if not isinstance(models, list):
        return ()

    names: list[str] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        name = str(model.get("name", "")).strip()
        if name:
            names.append(name)
    return tuple(names)


def check_ai_runtime_status(
    settings: AiSettings,
    http_get: HttpGet = default_http_get,
) -> AiRuntimeStatus:
    if settings.provider == "offline-docs":
        return AiRuntimeStatus(
            provider=settings.provider,
            ready=True,
            message="Offline-docs готов: интернет и локальная модель не требуются.",
        )

    if settings.provider != "ollama":
        return AiRuntimeStatus(
            provider=settings.provider,
            ready=False,
            message=f"Неизвестный AI provider: {settings.provider}.",
        )

    if not settings.ollama.model:
        return AiRuntimeStatus(
            provider=settings.provider,
            ready=False,
            message="Ollama provider выбран, но имя модели не указано в config/ai.json.",
        )

    try:
        response = http_get(
            f"{settings.ollama.base_url}/api/tags",
            settings.ollama.timeout_seconds,
        )
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return AiRuntimeStatus(
            provider=settings.provider,
            ready=False,
            message=(
                f"Ollama недоступен на {settings.ollama.base_url}: "
                f"{exc.__class__.__name__}."
            ),
        )

    available_models = _extract_ollama_model_names(response)
    if settings.ollama.model not in available_models:
        return AiRuntimeStatus(
            provider=settings.provider,
            ready=False,
            message=(
                f"Модель {settings.ollama.model} не найдена локально. "
                "Загрузите ее заранее и проверьте `ollama list`."
            ),
            available_models=available_models,
        )

    return AiRuntimeStatus(
        provider=settings.provider,
        ready=True,
        message=f"Ollama готов: локальная модель {settings.ollama.model} найдена.",
        available_models=available_models,
    )
