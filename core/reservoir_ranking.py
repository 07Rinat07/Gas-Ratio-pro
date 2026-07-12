from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval
from core.reservoir_passport import ReservoirPassport, build_reservoir_passport


@dataclass(frozen=True, slots=True)
class ReservoirRankingWeights:
    confidence: float = 30.0
    agreement: float = 30.0
    completeness: float = 20.0
    thickness: float = 20.0

    def normalized(self) -> "ReservoirRankingWeights":
        values = [max(0.0, float(v)) for v in (self.confidence, self.agreement, self.completeness, self.thickness)]
        total = sum(values)
        if total <= 0:
            return ReservoirRankingWeights()
        factor = 100.0 / total
        return ReservoirRankingWeights(*(round(v * factor, 6) for v in values))

    def as_fractions(self) -> tuple[float, float, float, float]:
        value = self.normalized()
        return tuple(v / 100.0 for v in (value.confidence, value.agreement, value.completeness, value.thickness))


@dataclass(frozen=True, slots=True)
class ReservoirRankingProfile:
    profile_id: str
    name: str
    weights: ReservoirRankingWeights
    reference_thickness: float = 20.0
    description: str = ""
    built_in: bool = False


DEFAULT_RANKING_PROFILE = ReservoirRankingProfile(
    profile_id="standard",
    name="Стандартный Gas Ratio Pro",
    weights=ReservoirRankingWeights(),
    reference_thickness=20.0,
    description="Сбалансированная оценка достоверности, согласованности методик, полноты данных и мощности.",
    built_in=True,
)

BUILTIN_RANKING_PROFILES: tuple[ReservoirRankingProfile, ...] = (
    DEFAULT_RANKING_PROFILE,
    ReservoirRankingProfile(
        "oil", "Нефтяной", ReservoirRankingWeights(30, 35, 20, 15), 20.0,
        "Повышенный вес согласованности методик для отбора устойчивых нефтяных кандидатов.", True,
    ),
    ReservoirRankingProfile(
        "gas", "Газовый", ReservoirRankingWeights(35, 25, 25, 15), 15.0,
        "Повышенный вес достоверности и полноты газового состава.", True,
    ),
    ReservoirRankingProfile(
        "exploration", "Геологоразведка", ReservoirRankingWeights(25, 30, 20, 25), 25.0,
        "Больше внимания мощности объекта при сохранении контроля согласованности методик.", True,
    ),
    ReservoirRankingProfile(
        "production", "Эксплуатация", ReservoirRankingWeights(35, 30, 15, 20), 15.0,
        "Приоритет достоверности и устойчивости результата для последующего инженерного анализа.", True,
    ),
)


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
    profile_id: str = "standard"
    profile_name: str = "Стандартный Gas Ratio Pro"


@dataclass(frozen=True, slots=True)
class ReservoirRankChange:
    interval_id: str
    old_rank: int
    new_rank: int
    rank_delta: int
    old_score: float
    new_score: float
    score_delta: float
    explanation: str


def _bounded(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(high, max(low, float(value)))


def _thickness_percent(thickness: float, *, reference_thickness: float = 20.0) -> float:
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


def ranking_profile_by_id(profile_id: str, custom_profiles: Sequence[ReservoirRankingProfile] = ()) -> ReservoirRankingProfile:
    target = str(profile_id or "standard")
    for profile in (*BUILTIN_RANKING_PROFILES, *tuple(custom_profiles)):
        if profile.profile_id == target:
            return profile
    return DEFAULT_RANKING_PROFILE


def build_reservoir_rank(
    passport: ReservoirPassport,
    *,
    reference_thickness: float | None = None,
    profile: ReservoirRankingProfile | None = None,
) -> ReservoirRank:
    profile = profile or DEFAULT_RANKING_PROFILE
    weights = profile.weights.normalized()
    wc, wa, wcomp, wt = weights.as_fractions()
    thickness_reference = float(reference_thickness if reference_thickness is not None else profile.reference_thickness)
    confidence = _bounded(passport.confidence_score) * wc
    agreement = _bounded(passport.agreement_percent) * wa
    completeness = _bounded(passport.data_completeness_percent) * wcomp
    thickness = _thickness_percent(passport.thickness, reference_thickness=thickness_reference) * wt
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
        profile_id=profile.profile_id,
        profile_name=profile.name,
    )


def rank_reservoir_intervals(
    frame: pd.DataFrame,
    intervals: Sequence[HydrocarbonInterval],
    *,
    reference_thickness: float | None = None,
    profile: ReservoirRankingProfile | None = None,
) -> tuple[ReservoirRank, ...]:
    profile = profile or DEFAULT_RANKING_PROFILE
    ranked: list[ReservoirRank] = []
    for index, interval in enumerate(intervals, start=1):
        passport = build_reservoir_passport(frame, interval, interval_id=f"HC-{index:03d}")
        ranked.append(build_reservoir_rank(passport, reference_thickness=reference_thickness, profile=profile))
    ranked.sort(key=lambda item: (-item.priority_score, -item.confidence_component, -item.thickness, item.top))
    return tuple(ReservoirRank(**{**asdict(item), "rank": position}) for position, item in enumerate(ranked, start=1))


def compare_reservoir_rankings(
    previous: Sequence[ReservoirRank],
    current: Sequence[ReservoirRank],
    *,
    previous_profile: ReservoirRankingProfile | None = None,
    current_profile: ReservoirRankingProfile | None = None,
) -> tuple[ReservoirRankChange, ...]:
    old = {item.interval_id: item for item in previous}
    changes: list[ReservoirRankChange] = []
    weight_note = ""
    if previous_profile and current_profile:
        a = previous_profile.weights.normalized()
        b = current_profile.weights.normalized()
        deltas = []
        for label, old_w, new_w in (
            ("достоверности", a.confidence, b.confidence),
            ("согласованности", a.agreement, b.agreement),
            ("полноты", a.completeness, b.completeness),
            ("мощности", a.thickness, b.thickness),
        ):
            diff = new_w - old_w
            if abs(diff) >= 0.05:
                deltas.append(f"{label}: {diff:+.1f} п.п.")
        weight_note = "; ".join(deltas)
    for item in current:
        prior = old.get(item.interval_id)
        if prior is None:
            continue
        rank_delta = prior.rank - item.rank
        score_delta = round(item.priority_score - prior.priority_score, 1)
        direction = "позиция не изменилась"
        if rank_delta > 0:
            direction = f"поднялся на {rank_delta}"
        elif rank_delta < 0:
            direction = f"опустился на {abs(rank_delta)}"
        explanation = f"{direction}; изменение индекса {score_delta:+.1f}"
        if weight_note:
            explanation += f". Изменение весов: {weight_note}"
        changes.append(ReservoirRankChange(
            interval_id=item.interval_id,
            old_rank=prior.rank,
            new_rank=item.rank,
            rank_delta=rank_delta,
            old_score=prior.priority_score,
            new_score=item.priority_score,
            score_delta=score_delta,
            explanation=explanation,
        ))
    return tuple(changes)


def reservoir_ranking_dataframe(
    ranking: Sequence[ReservoirRank],
    changes: Sequence[ReservoirRankChange] = (),
) -> pd.DataFrame:
    change_map: Mapping[str, ReservoirRankChange] = {item.interval_id: item for item in changes}
    return pd.DataFrame([
        {
            "Место": item.rank,
            "Δ места": change_map[item.interval_id].rank_delta if item.interval_id in change_map else 0,
            "ID": item.interval_id,
            "Интервал, м": f"{item.top:g}–{item.base:g}",
            "Мощность, м": item.thickness,
            "Флюид": item.fluid_type,
            "Индекс приоритета": item.priority_score,
            "Δ индекса": change_map[item.interval_id].score_delta if item.interval_id in change_map else 0.0,
            "Класс": item.priority_class,
            "Достоверность, вклад": item.confidence_component,
            "Методики, вклад": item.agreement_component,
            "Полнота, вклад": item.completeness_component,
            "Мощность, вклад": item.thickness_component,
            "Штраф": item.penalty,
            "Готов к отчёту": "Да" if item.ready_for_report else "Нет",
            "Почему изменилось": change_map[item.interval_id].explanation if item.interval_id in change_map else "",
            "Рекомендация": item.recommendation,
        }
        for item in ranking
    ])
