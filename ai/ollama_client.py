from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from ai.prompts import INTERPRETATION_DISCLAIMER
from ai.provider import ProviderRequest, ProviderResponse, ensure_disclaimer


HttpPost = Callable[[str, dict, int], dict]


def default_http_post(url: str, payload: dict, timeout_seconds: int) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response_text = response.read().decode("utf-8")
    return json.loads(response_text)


def _fallback_from_context(context: str, reason: str, timeout_seconds: int) -> str:
    lines = [
        f"Ollama не успел ответить за {timeout_seconds} сек. ({reason}). Показываю быстрый ответ по локальной базе знаний.",
    ]

    for line in context.splitlines():
        clean_line = line.strip()
        if clean_line.startswith("Проверенный ответ:"):
            lines.append(clean_line.replace("Проверенный ответ:", "", 1).strip())
            break

    if len(lines) == 1 and context.strip():
        lines.append("В локальной базе знаний найден релевантный контекст. Проверьте источники под ответом и уточните вопрос, если нужна детализация.")
    elif len(lines) == 1:
        lines.append("В локальной базе знаний нет прямого ответа. Проверьте документацию проекта или добавьте Q/A-пример.")

    return ensure_disclaimer("\n\n".join(lines))


class OllamaProvider:
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "",
        timeout_seconds: int = 60,
        http_post: HttpPost = default_http_post,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds
        self.http_post = http_post

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        if not self.model:
            return ProviderResponse(
                answer=(
                    "Локальная модель Ollama не настроена. Укажите имя модели в "
                    "AI config -> `ollama.model` и убедитесь, что Ollama запущен локально.\n\n"
                    f"{INTERPRETATION_DISCLAIMER}"
                ),
                provider_name=self.provider_name,
            )

        payload = {
            "model": self.model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 160,
                "num_ctx": 4096,
            },
        }

        try:
            response = self.http_post(
                f"{self.base_url}/api/generate",
                payload,
                self.timeout_seconds,
            )
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            return ProviderResponse(
                answer=_fallback_from_context(
                    request.context,
                    reason=exc.__class__.__name__,
                    timeout_seconds=self.timeout_seconds,
                ),
                provider_name=self.provider_name,
            )

        answer = str(response.get("response", "")).strip()
        if not answer:
            answer = "Ollama вернул пустой ответ. Проверьте локальную модель и prompt."

        return ProviderResponse(
            answer=ensure_disclaimer(answer),
            provider_name=self.provider_name,
        )
