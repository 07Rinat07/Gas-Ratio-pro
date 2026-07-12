from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval
from palettes.config import DEFAULT_PIXLER_ZONES, PixlerZone, TernaryRegion
from core.expert_interpretation import CrossMethodAnalysis, build_cross_method_analysis
from core.methods import MethodContext, build_default_method_registry

GAS_COMPONENTS: tuple[str, ...] = ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5")
DERIVED_METRICS: tuple[str, ...] = (
    "wh", "bh", "ch", "bar2", "oil_indicator", "inverse_oil_indicator",
    "c1_c2", "c1_c3", "c1_c4", "c1_c5",
)


@dataclass(frozen=True, slots=True)
class ReservoirMethodResult:
    method: str
    classification: str
    support_percent: float
    status: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class ReservoirPassport:
    interval_id: str
    top: float
    base: float
    thickness: float
    fluid_type: str
    confidence_score: int
    data_confidence_score: int
    geological_confidence_score: int
    decision_level: str
    gas_composition: tuple[tuple[str, float | None], ...]
    derived_metrics: tuple[tuple[str, float | None], ...]
    methods: tuple[ReservoirMethodResult, ...]
    agreement_percent: float
    data_completeness_percent: float
    limitations: tuple[str, ...]
    recommendations: tuple[str, ...]
    engineering_conclusion: str
    ready_for_report: bool
    readiness_label: str
    cross_method_analysis: CrossMethodAnalysis | None = None


def _safe_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _median_values(frame: pd.DataFrame, columns: Sequence[str]) -> tuple[tuple[str, float | None], ...]:
    values: list[tuple[str, float | None]] = []
    for column in columns:
        if column not in frame.columns:
            values.append((column, None))
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce").dropna()
        values.append((column, _safe_number(numeric.median()) if not numeric.empty else None))
    return tuple(values)


def _normalize_fluid(text: object) -> str:
    value = str(text or "").strip().lower()
    if any(token in value for token in ("condens", "конденсат")):
        return "condensate"
    if any(token in value for token in ("oil", "нефт")):
        return "oil"
    if any(token in value for token in ("dry gas", "сух")):
        return "dry_gas"
    if any(token in value for token in ("gas", "газ")):
        return "gas"
    if any(token in value for token in ("water", "вод")):
        return "water"
    if any(token in value for token in ("mixed", "смеш", "transition", "переход")):
        return "mixed"
    return "unknown"


def _agreement(methods: Sequence[ReservoirMethodResult]) -> float:
    usable = [result for result in methods if result.classification not in {"unknown", ""} and result.support_percent > 0]
    if not usable:
        return 0.0
    weighted: dict[str, float] = {}
    total = 0.0
    for result in usable:
        weight = max(1.0, float(result.support_percent))
        weighted[result.classification] = weighted.get(result.classification, 0.0) + weight
        total += weight
    return round(max(weighted.values()) / total * 100.0, 1) if total else 0.0


def build_reservoir_passport(
    frame: pd.DataFrame,
    interval: HydrocarbonInterval,
    *,
    interval_id: str,
    selected_row: pd.Series | Mapping[str, object] | None = None,
    pixler_zones: tuple[PixlerZone, ...] = DEFAULT_PIXLER_ZONES,
    ternary_regions: tuple[TernaryRegion, ...] = (),
) -> ReservoirPassport:
    depth = pd.to_numeric(frame.get("depth"), errors="coerce") if "depth" in frame.columns else pd.Series(index=frame.index, dtype=float)
    interval_frame = frame.loc[depth.between(float(interval.top), float(interval.base), inclusive="both")].copy()
    if selected_row is None:
        selected_row = interval_frame.iloc[len(interval_frame) // 2] if not interval_frame.empty else {}

    gas_composition = _median_values(interval_frame, GAS_COMPONENTS)
    derived_metrics = _median_values(interval_frame, DERIVED_METRICS)
    effective_pixler_zones = pixler_zones or DEFAULT_PIXLER_ZONES
    method_context = MethodContext(
        frame=interval_frame,
        interval=interval,
        interval_id=str(interval_id),
        selected_row=selected_row,
        pixler_zones=effective_pixler_zones,
        ternary_regions=ternary_regions,
    )
    method_results = build_default_method_registry().analyze_all(method_context)
    methods = tuple(
        ReservoirMethodResult(
            result.method,
            _normalize_fluid(result.classification),
            float(result.support),
            "Доступно" if result.available else "Недостаточно данных",
            str(result.explanation or "; ".join(result.limitations)),
        )
        for result in method_results
    )

    available = sum(1 for _, value in gas_composition if value is not None)
    completeness = round(available / len(GAS_COMPONENTS) * 100.0, 1) if GAS_COMPONENTS else 0.0
    explanation = interval.explanation
    cross_method = build_cross_method_analysis(
        method_results,
        data_completeness_percent=completeness,
        interval_confidence_percent=float(interval.confidence_score),
        limitations=tuple(explanation.limitations if explanation else ()) or tuple(interval.warnings) or tuple(interval.quality_flags),
    )
    agreement = cross_method.agreement_percent
    limitations = tuple(explanation.limitations if explanation else ()) or tuple(interval.warnings) or tuple(interval.quality_flags)
    recommendations = tuple(explanation.recommendations if explanation else ())
    conclusion = (explanation.summary if explanation and explanation.summary else interval.interpretation) or interval.engineering_note
    ready = bool(interval.confidence_score >= 70 and completeness >= 60 and agreement >= 50 and interval.thickness > 0)
    readiness = "Готов к инженерному отчёту" if ready else "Требует инженерной проверки"

    return ReservoirPassport(
        interval_id=str(interval_id), top=float(interval.top), base=float(interval.base), thickness=float(interval.thickness),
        fluid_type=str(interval.fluid_type), confidence_score=int(interval.confidence_score),
        data_confidence_score=int(interval.data_confidence_score), geological_confidence_score=int(interval.geological_confidence_score),
        decision_level=str(interval.decision_level), gas_composition=gas_composition, derived_metrics=derived_metrics,
        methods=methods, agreement_percent=agreement, data_completeness_percent=completeness,
        limitations=tuple(str(item) for item in limitations if str(item).strip()),
        recommendations=tuple(str(item) for item in recommendations if str(item).strip()),
        engineering_conclusion=str(cross_method.expert_conclusion or conclusion or ""), ready_for_report=ready, readiness_label=readiness,
        cross_method_analysis=cross_method,
    )


def passport_summary_rows(passport: ReservoirPassport) -> tuple[tuple[str, str], ...]:
    return (
        ("Интервал", passport.interval_id),
        ("Глубина", f"{passport.top:g}–{passport.base:g} м"),
        ("Мощность", f"{passport.thickness:g} м"),
        ("Вероятный флюид", passport.fluid_type),
        ("Достоверность", f"{passport.confidence_score}%"),
        ("Полнота C1–C5", f"{passport.data_completeness_percent:g}%"),
        ("Согласованность методик", f"{passport.agreement_percent:g}%"),
        ("Готовность", passport.readiness_label),
    )
