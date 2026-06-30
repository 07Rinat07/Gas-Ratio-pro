from __future__ import annotations

from ai.ollama_client import OllamaProvider
from ai.provider import AssistantProvider, OfflineDocumentationProvider
from ai.settings import AiSettings


def build_provider(settings: AiSettings) -> AssistantProvider:
    if settings.provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama.base_url,
            model=settings.ollama.model,
            timeout_seconds=settings.ollama.timeout_seconds,
        )

    return OfflineDocumentationProvider()
