from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval
from core.reservoir_passport import ReservoirPassport, build_reservoir_passport


@dataclass(frozen=True, slots=True)
class ReservoirRank:
    rank: int
    interval_id: str
    top: float
    base: float
    thickness: float
    fluid_type: str
    priority_score: float
    priority_class: str
    confidence_component: float
    agreement_component: float
    completeness_component: float
    thickness_component: float
    penalty: float
    ready_for_report: bool
    recommendation: str


def _bounded(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(high, max(low, float(value)))


def _thickness_percent(thickness: float, *, reference_thickness: float = 20.0) -> float:
    """Normalize gross interval thickness without allowing it to dominate ranking.

    The score saturates at ``reference_thickness``. This is an engineering
    prioritization aid, not net-pay or reserves estimation.
    """
    if reference_thickness <= 0:
        return 0.0
    return _bounded(float(thickness) / float(reference_thickness) * 100.0)


def _priority_class(score: float) -> str:
    if score >= 80:
        return "A — высокий приоритет"
    if score >= 65:
        return "B — приоритетный"
    if score >= 50:
        return "C — дополнительная проверка"
    return "D — низкая устойчивость"


def _recommendation(passport: ReservoirPassport, score: float) -> str:
    if passport.thickness <= 0:
        return "Не ранжировать как пласт: одиночная глубинная точка."
    if score >= 80 and passport.ready_for_report:
        return "Приоритетный объект для детального геолого-геофизического анализа и сопоставления с испытаниями."
    if score >= 65:
        return "Сопоставить с ГИС, литологией, керном и данными испытаний."
    if passport.agreement_percent < 50:
        return "Проверить противоречия Pixler, ternary и Haworth."
    if passport.data_completeness_percent < 60:
        return "Проверить полноту C1–C5 и качество исходных газовых данных."
    return "Требуется инженерная проверка устойчивости признаков и границ интервала."


def build_reservoir_rank(
    passport: ReservoirPassport,
    *,
    reference_thickness: float = 20.0,
) -> ReservoirRank:
    """Calculate a transparent 0–100 engineering priority index.

    Weights:
      * interpretation confidence: 30%
      * agreement of methods: 30%
      * C1–C5 completeness: 20%
      * gross interval thickness: 20%

    Penalties are explicit for zero-thickness point anomalies and unknown fluid
    classification. The index is not a reserves, net-pay, saturation or
    commerciality estimate.
    """
    confidence = _bounded(passport.confidence_score) * 0.30
    agreement = _bounded(passport.agreement_percent) * 0.30
    completeness = _bounded(passport.data_completeness_percent) * 0.20
    thickness = _thickness_percent(passport.thickness, reference_thickness=reference_thickness) * 0.20
    penalty = 0.0
    if passport.thickness <= 0:
        penalty += 20.0
    if str(passport.fluid_type).strip().lower() in {"", "unknown", "uncertain"}:
        penalty += 10.0
    score = round(_bounded(confidence + agreement + completeness + thickness - penalty), 1)
    return ReservoirRank(
        rank=0,
        interval_id=passport.interval_id,
        top=passport.top,
        base=passport.base,
        thickness=passport.thickness,
        fluid_type=passport.fluid_type,
        priority_score=score,
        priority_class=_priority_class(score),
        confidence_component=round(confidence, 1),
        agreement_component=round(agreement, 1),
        completeness_component=round(completeness, 1),
        thickness_component=round(thickness, 1),
        penalty=round(penalty, 1),
        ready_for_report=passport.ready_for_report,
        recommendation=_recommendation(passport, score),
    )


def rank_reservoir_intervals(
    frame: pd.DataFrame,
    intervals: Sequence[HydrocarbonInterval],
    *,
    reference_thickness: float = 20.0,
) -> tuple[ReservoirRank, ...]:
    ranked: list[ReservoirRank] = []
    for index, interval in enumerate(intervals, start=1):
        passport = build_reservoir_passport(frame, interval, interval_id=f"HC-{index:03d}")
        ranked.append(build_reservoir_rank(passport, reference_thickness=reference_thickness))
    ranked.sort(key=lambda item: (-item.priority_score, -item.confidence_component, -item.thickness, item.top))
    return tuple(
        ReservoirRank(**{**asdict(item), "rank": position})
        for position, item in enumerate(ranked, start=1)
    )


def reservoir_ranking_dataframe(ranking: Sequence[ReservoirRank]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Место": item.rank,
            "ID": item.interval_id,
            "Интервал, м": f"{item.top:g}–{item.base:g}",
            "Мощность, м": item.thickness,
            "Флюид": item.fluid_type,
            "Индекс приоритета": item.priority_score,
            "Класс": item.priority_class,
            "Достоверность, вклад": item.confidence_component,
            "Методики, вклад": item.agreement_component,
            "Полнота, вклад": item.completeness_component,
            "Мощность, вклад": item.thickness_component,
            "Штраф": item.penalty,
            "Готов к отчёту": "Да" if item.ready_for_report else "Нет",
            "Рекомендация": item.recommendation,
        }
        for item in ranking
    ])
