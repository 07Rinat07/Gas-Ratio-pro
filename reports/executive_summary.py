from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import pandas as pd

from core.hydrocarbon_intervals import (
    CONFIDENCE_LABELS,
    FLUID_TYPE_LABELS,
    HydrocarbonInterval,
    HydrocarbonIntervalResult,
    detect_hydrocarbon_intervals,
    summarize_hydrocarbon_interval_result,
)
from reports.export_html import HtmlReportTable
from reports.report_i18n import fluid_label, generated, localize_text


PRODUCTIVE_FLUIDS = {"gas", "oil", "condensate", "mixed", "gas_oil", "oil_gas"}

DECISION_LEVEL_LABELS: Mapping[str, str] = {
    "very_high": "очень высокая",
    "high": "высокая",
    "medium": "средняя",
    "low": "низкая",
    "review": "требует проверки",
    "unknown": "неопределенная",
}


@dataclass(frozen=True)
class ExecutiveSummaryItem:
    """One engineer-facing summary item for the first report page.

    The item intentionally avoids technical counters such as dataframe row count.
    It answers practical questions: what was found, where it was found and how
    confidently the engine supports the interpretation.
    """

    title: str
    value: str
    note: str = ""


@dataclass(frozen=True)
class ExecutiveSummary:
    """Professional first-page summary for hydrocarbon interpretation reports."""

    title: str
    overall_assessment: str
    items: tuple[ExecutiveSummaryItem, ...]
    main_intervals: tuple[HydrocarbonInterval, ...]
    recommendations: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    schema: str = "gas-ratio-pro/professional-reporting/executive-summary/v1"


def _format_depth_range(interval: HydrocarbonInterval) -> str:
    return f"{interval.top:g}–{interval.base:g} м"


def _fluid_label(fluid_type: str, locale: str = "ru") -> str:
    return fluid_label(fluid_type, locale)


def _decision_label(level: str, locale: str = "ru") -> str:
    key = str(level or "unknown").strip().lower()
    return generated(locale, f"decision.{key}" if key in DECISION_LEVEL_LABELS else "decision.unknown")


def _confidence_label(interval: HydrocarbonInterval) -> str:
    if interval.confidence_score:
        return f"{interval.confidence_score}%"
    return CONFIDENCE_LABELS.get(interval.confidence, interval.confidence or "")


def _best_intervals(intervals: Sequence[HydrocarbonInterval], *, limit: int = 5) -> tuple[HydrocarbonInterval, ...]:
    """Return the intervals most useful on the first report page."""

    productive = [interval for interval in intervals if interval.fluid_type in PRODUCTIVE_FLUIDS]
    candidates = productive or list(intervals)
    return tuple(
        sorted(
            candidates,
            key=lambda item: (
                -int(item.confidence_score or 0),
                -float(item.thickness or 0),
                float(item.top),
            ),
        )[:limit]
    )


def _collect_recommendations(intervals: Sequence[HydrocarbonInterval]) -> tuple[str, ...]:
    recommendations: list[str] = []
    for interval in intervals:
        if interval.explanation is not None:
            recommendations.extend(str(item).strip() for item in interval.explanation.recommendations if str(item).strip())
        if not recommendations and interval.engineering_note:
            recommendations.append(str(interval.engineering_note).strip())
    seen: set[str] = set()
    unique: list[str] = []
    for item in recommendations:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return tuple(unique[:5])


def _collect_limitations(intervals: Sequence[HydrocarbonInterval]) -> tuple[str, ...]:
    limitations: list[str] = []
    for interval in intervals:
        if interval.explanation is not None:
            limitations.extend(str(item).strip() for item in interval.explanation.limitations if str(item).strip())
        limitations.extend(str(item).strip() for item in interval.warnings if str(item).strip())
        limitations.extend(str(item).strip() for item in interval.quality_flags if str(item).strip())
    seen: set[str] = set()
    unique: list[str] = []
    for item in limitations:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return tuple(unique[:5])


def _overall_assessment(result: HydrocarbonIntervalResult, locale: str = "ru") -> str:
    summary = summarize_hydrocarbon_interval_result(result)
    productive = int(summary.get("productive_intervals", 0) or 0)
    total = int(summary.get("total_intervals", 0) or 0)
    review = int(summary.get("review_required", 0) or 0)

    if productive > 0 and review == 0:
        return generated(locale, "summary.overall.productive")
    if productive > 0:
        return generated(locale, "summary.overall.review")
    if total > 0:
        return generated(locale, "summary.overall.interest")
    return generated(locale, "summary.overall.none")


def build_executive_summary(result: HydrocarbonIntervalResult, *, locale: str = "ru") -> ExecutiveSummary:
    """Build a decision-oriented first-page summary for geoscience teams."""

    summary = summarize_hydrocarbon_interval_result(result)
    main_intervals = _best_intervals(result.intervals)
    productive = tuple(item for item in result.intervals if item.fluid_type in PRODUCTIVE_FLUIDS)

    items: list[ExecutiveSummaryItem] = []
    if productive:
        top = min(float(item.top) for item in productive)
        base = max(float(item.base) for item in productive)
        total_thickness = sum(float(item.thickness or 0.0) for item in productive)
        items.append(ExecutiveSummaryItem(
            title=generated(locale, "summary.hc_range"),
            value=f"{top:g}–{base:g} м",
            note=generated(locale, "summary.total_thickness", value=f"{total_thickness:.1f}"),
        ))

    for fluid_type in ("oil", "gas", "condensate", "gas_oil", "oil_gas", "mixed"):
        intervals = [item for item in productive if item.fluid_type == fluid_type]
        if not intervals:
            continue
        best = sorted(intervals, key=lambda item: (-int(item.confidence_score or 0), -float(item.thickness or 0)))[0]
        total = sum(float(item.thickness or 0.0) for item in intervals)
        items.append(ExecutiveSummaryItem(
            title=_fluid_label(fluid_type, locale),
            value=f"{best.top:g}–{best.base:g} м",
            note=(
                generated(locale, "summary.best_note", thickness=f"{best.thickness:g}", confidence=_confidence_label(best), total=f"{total:.1f}")
            ),
        ))

    review_required = int(summary.get("review_required", 0) or 0)
    if review_required:
        items.append(ExecutiveSummaryItem(
            title=generated(locale, "summary.manual_review"),
            value=generated(locale, "summary.interval_count", count=review_required),
            note=generated(locale, "summary.review_note"),
        ))

    if main_intervals:
        best = main_intervals[0]
        items.append(ExecutiveSummaryItem(
            title=generated(locale, "summary.best_interval"),
            value=_format_depth_range(best),
            note=generated(locale, "summary.best_interval_note", fluid=_fluid_label(best.fluid_type, locale), thickness=f"{best.thickness:g}", confidence=_confidence_label(best)),
        ))

    return ExecutiveSummary(
        title=generated(locale, "summary.title"),
        overall_assessment=_overall_assessment(result, locale),
        items=tuple(items),
        main_intervals=main_intervals,
        recommendations=tuple(localize_text(x, locale) for x in _collect_recommendations(main_intervals)),
        limitations=tuple(localize_text(x, locale) for x in _collect_limitations(main_intervals)),
    )


def build_executive_summary_from_dataframe(df: pd.DataFrame, *, depth_column: str = "depth", locale: str = "ru") -> ExecutiveSummary:
    """Convenience wrapper for report builders that start from calculated rows."""

    return build_executive_summary(detect_hydrocarbon_intervals(df, depth_column=depth_column), locale=locale)


def executive_summary_table(summary: ExecutiveSummary, *, locale: str = "ru") -> HtmlReportTable:
    """Render summary items as a compact first-page table."""

    rows = tuple((item.title, item.value, item.note) for item in summary.items)
    return HtmlReportTable(
        title=summary.title,
        headers=(generated(locale, "table.metric"), generated(locale, "table.value"), generated(locale, "table.comment")),
        rows=rows,
    )


def main_intervals_table(summary: ExecutiveSummary, *, locale: str = "ru") -> HtmlReportTable | None:
    """Render the most important intervals for the first report pages."""

    if not summary.main_intervals:
        return None
    rows = []
    for index, interval in enumerate(summary.main_intervals, start=1):
        explanation_summary = interval.explanation.summary if interval.explanation is not None else interval.engineering_note
        rows.append(
            (
                str(index),
                f"{interval.top:g}",
                f"{interval.base:g}",
                f"{interval.thickness:g}",
                _fluid_label(interval.fluid_type, locale),
                _decision_label(interval.decision_level, locale),
                _confidence_label(interval),
                str(explanation_summary or "").strip(),
            )
        )
    return HtmlReportTable(
        title=generated(locale, "table.priority_intervals"),
        headers=("№", "Кровля, м", "Подошва, м", "Мощность, м", "Флюид", "Решение", "Достоверность", "Инженерный вывод"),
        rows=tuple(rows),
    )


def executive_recommendations_table(summary: ExecutiveSummary, *, locale: str = "ru") -> HtmlReportTable | None:
    """Render recommendations and limitations without exposing debug details."""

    rows: list[tuple[str, str]] = []
    rows.extend(("Рекомендация", item) for item in summary.recommendations)
    rows.extend(("Ограничение", item) for item in summary.limitations)
    if not rows:
        return None
    return HtmlReportTable(
        title=generated(locale, "table.recommendations"),
        headers=(localize_text("Тип", locale), generated(locale, "table.description")),
        rows=tuple(rows),
    )
