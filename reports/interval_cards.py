from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from core.hydrocarbon_intervals import (
    CONFIDENCE_LABELS,
    FLUID_TYPE_LABELS,
    HydrocarbonInterval,
)
from reports.executive_summary import DECISION_LEVEL_LABELS
from reports.export_html import HtmlReportTable


PRODUCTIVE_FLUIDS = {"gas", "oil", "condensate", "mixed", "gas_oil", "oil_gas"}


@dataclass(frozen=True)
class IntervalReportCard:
    """Engineer-facing report card for one interpreted interval.

    The card is intentionally different from a raw dataframe row. It answers the
    practical reporting questions first: where is the interval, what is the
    likely fluid type, how confident is the interpretation, why the engine made
    that decision, and what should be checked next.
    """

    interval_id: str
    depth_range: str
    thickness: str
    fluid_type: str
    decision_level: str
    confidence: str
    summary: str
    reasoning: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    references: tuple[str, ...] = ()

    @property
    def is_productive(self) -> bool:
        return self.fluid_type in {FLUID_TYPE_LABELS.get(item, item) for item in PRODUCTIVE_FLUIDS} or self.fluid_type in PRODUCTIVE_FLUIDS


def _depth_range(interval: HydrocarbonInterval) -> str:
    return f"{interval.top:g}–{interval.base:g} м"


def _fluid_label(fluid_type: str) -> str:
    return FLUID_TYPE_LABELS.get(fluid_type, fluid_type or "Не определено")


def _decision_label(level: str) -> str:
    return DECISION_LEVEL_LABELS.get(level, level or "неопределенная")


def _confidence_label(interval: HydrocarbonInterval) -> str:
    if interval.confidence_score:
        data = f"данные {interval.data_confidence_score}%" if interval.data_confidence_score else ""
        geology = f"геология {interval.geological_confidence_score}%" if interval.geological_confidence_score else ""
        details = ", ".join(item for item in (data, geology) if item)
        return f"{interval.confidence_score}%" + (f" ({details})" if details else "")
    return CONFIDENCE_LABELS.get(interval.confidence, interval.confidence or "")


def _clean_unique(values: Sequence[object], *, limit: int = 6) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return tuple(result)


def build_interval_report_card(interval: HydrocarbonInterval, *, index: int) -> IntervalReportCard:
    """Build one printable interval card from the frozen HIE interval model."""

    explanation = interval.explanation
    summary = ""
    reasoning: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    references: tuple[str, ...] = ()

    if explanation is not None:
        summary = explanation.summary
        reasoning = _clean_unique(explanation.reasoning or explanation.supporting_evidence, limit=7)
        recommendations = _clean_unique(explanation.recommendations, limit=5)
        limitations = _clean_unique(explanation.limitations, limit=5)
        references = _clean_unique(explanation.references, limit=5)

    if not summary:
        summary = interval.engineering_note or interval.interpretation or "Предварительная инженерная интерпретация требует проверки."
    if not reasoning:
        reasoning = _clean_unique(interval.evidence or tuple(item.description for item in interval.evidence_items), limit=7)
    if not limitations:
        limitations = _clean_unique(tuple(interval.warnings) + tuple(interval.quality_flags), limit=5)
    if not recommendations and interval.engineering_note:
        recommendations = (interval.engineering_note,)

    return IntervalReportCard(
        interval_id=f"HC-{index:03d}",
        depth_range=_depth_range(interval),
        thickness=f"{interval.thickness:g} м",
        fluid_type=_fluid_label(interval.fluid_type),
        decision_level=_decision_label(interval.decision_level),
        confidence=_confidence_label(interval),
        summary=str(summary).strip(),
        reasoning=reasoning,
        recommendations=recommendations,
        limitations=limitations,
        references=references,
    )


def build_interval_report_cards(intervals: Sequence[HydrocarbonInterval]) -> tuple[IntervalReportCard, ...]:
    """Build cards for all intervals, preserving detected interval boundaries."""

    return tuple(build_interval_report_card(interval, index=index) for index, interval in enumerate(intervals, start=1))


def interval_cards_overview_table(cards: Sequence[IntervalReportCard]) -> HtmlReportTable | None:
    """Compact table for the first report pages."""

    if not cards:
        return None
    rows = tuple(
        (
            card.interval_id,
            card.depth_range,
            card.thickness,
            card.fluid_type,
            card.decision_level,
            card.confidence,
            card.summary,
        )
        for card in cards
    )
    return HtmlReportTable(
        title="Карточки интервалов залежей",
        headers=("№", "Интервал", "Мощность", "Тип", "Уровень", "Достоверность", "Заключение"),
        rows=rows,
    )


def interval_cards_reasoning_table(cards: Sequence[IntervalReportCard]) -> HtmlReportTable | None:
    """Detailed interval reasoning table used after the overview."""

    rows: list[tuple[str, str, str, str]] = []
    for card in cards:
        rows.append(
            (
                card.interval_id,
                "Основания",
                "\n".join(card.reasoning) if card.reasoning else "нет структурированных оснований",
                card.summary,
            )
        )
        if card.recommendations:
            rows.append((card.interval_id, "Рекомендации", "\n".join(card.recommendations), ""))
        if card.limitations:
            rows.append((card.interval_id, "Ограничения", "\n".join(card.limitations), ""))
    if not rows:
        return None
    return HtmlReportTable(
        title="Обоснование интерпретации по интервалам",
        headers=("Интервал", "Раздел", "Содержание", "Краткий вывод"),
        rows=tuple(rows),
    )
