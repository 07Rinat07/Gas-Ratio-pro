from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai.knowledge_base import DocumentationKnowledgeBase
from ai.prompts import build_assistant_prompt
from ai.provider import AssistantProvider, OfflineDocumentationProvider, ProviderRequest


SAFE_INTERVAL_FIELDS: tuple[str, ...] = (
    "depth",
    "depth_from",
    "depth_to",
    "wh",
    "bh",
    "ch",
    "bar2",
    "c1_c2",
    "c1_c3",
    "c1_c4",
    "c1_c5",
    "interpretation",
)


@dataclass(frozen=True)
class AssistantAnswer:
    answer: str
    provider_name: str
    sources: tuple[str, ...]
    prompt: str


def build_interval_context(row: pd.Series | dict | None) -> str:
    if row is None:
        return ""

    lines: list[str] = []
    for field in SAFE_INTERVAL_FIELDS:
        value = row.get(field) if hasattr(row, "get") else None
        if value is None or pd.isna(value):
            continue
        lines.append(f"{field}: {value}")

    return "\n".join(lines)


class LocalAssistant:
    def __init__(
        self,
        knowledge_base: DocumentationKnowledgeBase | None = None,
        provider: AssistantProvider | None = None,
    ) -> None:
        self.knowledge_base = knowledge_base or DocumentationKnowledgeBase()
        self.provider = provider or OfflineDocumentationProvider()

    def answer(
        self,
        question: str,
        interval_row: pd.Series | dict | None = None,
        limit: int = 4,
    ) -> AssistantAnswer:
        clean_question = question.strip()
        if not clean_question:
            return AssistantAnswer(
                answer="Введите вопрос по расчетам, данным или ограничениям интерпретации.",
                provider_name=self.provider.provider_name,
                sources=(),
                prompt="",
            )

        interval_context = build_interval_context(interval_row)
        search_query = f"{clean_question}\n{interval_context}"
        context, sources = self.knowledge_base.build_context(search_query, limit=limit)
        prompt = build_assistant_prompt(clean_question, context, interval_context)

        response = self.provider.generate(
            ProviderRequest(
                question=clean_question,
                prompt=prompt,
                context=context,
                interval_context=interval_context,
            )
        )

        return AssistantAnswer(
            answer=response.answer,
            provider_name=response.provider_name,
            sources=sources,
            prompt=prompt,
        )
