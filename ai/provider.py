from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ai.prompts import INTERPRETATION_DISCLAIMER


@dataclass(frozen=True)
class ProviderRequest:
    question: str
    prompt: str
    context: str
    interval_context: str = ""


@dataclass(frozen=True)
class ProviderResponse:
    answer: str
    provider_name: str


class AssistantProvider(Protocol):
    provider_name: str

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        ...


def ensure_disclaimer(answer: str) -> str:
    clean_answer = answer.strip()
    if INTERPRETATION_DISCLAIMER in clean_answer:
        return clean_answer
    return f"{clean_answer}\n\n{INTERPRETATION_DISCLAIMER}" if clean_answer else INTERPRETATION_DISCLAIMER


def _extract_verified_context_answer(context: str) -> str:
    for line in context.splitlines():
        clean_line = line.strip()
        if clean_line.startswith("Проверенный ответ:"):
            return clean_line.replace("Проверенный ответ:", "", 1).strip()
    return ""


class OfflineDocumentationProvider:
    provider_name = "offline-docs"

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        verified_answer = _extract_verified_context_answer(request.context)
        answer_parts = [
            "Быстрый локальный ответ по базе знаний проекта.",
        ]

        if verified_answer:
            answer_parts.append(verified_answer)
        elif request.context.strip():
            answer_parts.append(
                "В локальной базе знаний найден релевантный контекст. Проверьте источники под ответом "
                "и уточните вопрос, если нужна более точная инструкция."
            )
        else:
            answer_parts.append(
                "В локальной документации не найден прямой контекст по вопросу. "
                "Уточните вопрос или добавьте методику в `docs/` и Q/A-каталог."
            )

        if request.interval_context.strip():
            answer_parts.append(
                "По выбранному интервалу я могу комментировать только переданные расчетные коэффициенты, "
                "без окончательного геологического заключения."
            )

        return ProviderResponse(
            answer=ensure_disclaimer("\n\n".join(answer_parts)),
            provider_name=self.provider_name,
        )
