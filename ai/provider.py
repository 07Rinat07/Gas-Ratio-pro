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


class OfflineDocumentationProvider:
    provider_name = "offline-docs"

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        answer_parts = [
            "Локальный помощник работает в offline-режиме: использую только документацию проекта и переданный контекст.",
        ]

        if request.context.strip():
            answer_parts.append(
                "По найденным документам проверьте релевантные разделы ниже. "
                "Если вопрос про формулы, ориентируйтесь на `docs/formulas.md`; "
                "если про входные файлы, на `docs/data_format.md`."
            )
        else:
            answer_parts.append(
                "В локальной документации не найден прямой контекст по вопросу. "
                "Уточните вопрос или добавьте методику в `docs/`."
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