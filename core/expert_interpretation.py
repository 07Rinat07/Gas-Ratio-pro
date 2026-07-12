from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class MethodResult:
    method: str
    classification: str
    confidence: float
    support: float
    evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    explanation: str = ""
    available: bool = True


@dataclass(frozen=True, slots=True)
class MethodContribution:
    method: str
    contribution_percent: float
    classification: str
    support_percent: float


@dataclass(frozen=True, slots=True)
class QualityIssue:
    severity: str
    code: str
    message: str
    affected_methods: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CrossMethodAnalysis:
    final_classification: str
    agreement_percent: float
    agreement_matrix: tuple[tuple[str, ...], ...]
    contributions: tuple[MethodContribution, ...]
    majority_methods: tuple[str, ...]
    dissenting_methods: tuple[str, ...]
    quality_issues: tuple[QualityIssue, ...]
    disagreement_reasons: tuple[str, ...]
    confidence_breakdown: tuple[tuple[str, float], ...]
    expert_conclusion: str


def _norm(value: object) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "oil-prone": "oil", "oil": "oil", "нефть": "oil", "нефтяной": "oil",
        "gas-prone": "gas", "gas": "gas", "газ": "gas", "газовый": "gas",
        "condensate": "condensate", "gas-condensate": "condensate", "газоконденсат": "condensate",
        "water": "water", "вода": "water",
        "mixed": "mixed", "transition": "mixed", "переходный": "mixed",
    }
    for key, result in aliases.items():
        if key in text:
            return result
    return "unknown"


def _bounded(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def build_cross_method_analysis(
    methods: Sequence[MethodResult],
    *,
    data_completeness_percent: float,
    interval_confidence_percent: float,
    limitations: Iterable[str] = (),
) -> CrossMethodAnalysis:
    usable = [m for m in methods if m.available and _norm(m.classification) != "unknown" and m.support > 0]
    weighted: dict[str, float] = {}
    total_weight = 0.0
    for method in usable:
        weight = max(1.0, _bounded(method.support))
        cls = _norm(method.classification)
        weighted[cls] = weighted.get(cls, 0.0) + weight
        total_weight += weight
    final = max(weighted, key=weighted.get) if weighted else "unknown"
    agreement = round((weighted.get(final, 0.0) / total_weight * 100.0) if total_weight else 0.0, 1)

    names = tuple(m.method for m in usable)
    matrix_rows: list[tuple[str, ...]] = [("Методика", *names)]
    for left in usable:
        row = [left.method]
        for right in usable:
            row.append("✓" if _norm(left.classification) == _norm(right.classification) else "✕")
        matrix_rows.append(tuple(row))

    raw_contrib = [(m, max(1.0, _bounded(m.support)) * max(0.1, _bounded(m.confidence) / 100.0)) for m in usable]
    contrib_total = sum(value for _, value in raw_contrib) or 1.0
    sorted_contrib = sorted(raw_contrib, key=lambda item: item[1], reverse=True)
    contribution_items: list[MethodContribution] = []
    running = 0.0
    for index, (method, value) in enumerate(sorted_contrib):
        percent = round(value / contrib_total * 100.0, 1)
        if index == len(sorted_contrib) - 1:
            percent = round(100.0 - running, 1)
        running += percent
        contribution_items.append(MethodContribution(
            method.method, percent, _norm(method.classification), round(_bounded(method.support), 1)
        ))
    contributions = tuple(contribution_items)

    majority = tuple(m.method for m in usable if _norm(m.classification) == final)
    dissenting = tuple(m.method for m in usable if _norm(m.classification) != final)

    issues: list[QualityIssue] = []
    reasons: list[str] = []
    completeness = _bounded(data_completeness_percent)
    if completeness < 60:
        issues.append(QualityIssue("WARNING", "LOW_COMPLETENESS", f"Полнота C1–C5 составляет только {completeness:.1f}%.", tuple(m.method for m in usable)))
        reasons.append("Низкая полнота C1–C5 может смещать Pixler, ternary и Haworth.")
    if len(usable) < 2:
        issues.append(QualityIssue("CRITICAL", "TOO_FEW_METHODS", "Недостаточно доступных методик для устойчивого межметодического вывода.", names))
    if dissenting:
        reasons.append("Методики расходятся по типу флюида: " + ", ".join(dissenting) + ".")
    for method in usable:
        for limitation in method.limitations:
            text = str(limitation).strip()
            if text:
                issues.append(QualityIssue("WARNING", f"{method.method.upper()}_LIMITATION", text, (method.method,)))
    for limitation in limitations:
        text = str(limitation).strip()
        if text:
            issues.append(QualityIssue("WARNING", "INTERVAL_LIMITATION", text, names))

    method_stability = round(sum(_bounded(m.support) for m in usable) / len(usable), 1) if usable else 0.0
    qc_score = max(0.0, 100.0 - min(60.0, len(issues) * 10.0))
    confidence_breakdown = (
        ("Качество данных", completeness),
        ("Согласованность методик", agreement),
        ("Поддержка методик", method_stability),
        ("Интервал", _bounded(interval_confidence_percent)),
        ("QC", round(qc_score, 1)),
    )

    if final == "unknown":
        conclusion = "Доступных методик недостаточно для устойчивой классификации интервала."
    else:
        label = {"oil": "нефтяная", "gas": "газовая", "condensate": "газоконденсатная", "water": "водная", "mixed": "смешанная"}.get(final, final)
        supporting = ", ".join(majority) or "доступные методики"
        conclusion = f"Наиболее вероятна {label} характеристика интервала. Результат поддерживают: {supporting}."
        if dissenting:
            conclusion += f" Расходятся с итогом: {', '.join(dissenting)}."
        if reasons:
            conclusion += " Возможные причины расхождения: " + " ".join(reasons[:3])
        conclusion += " Вывод предварительный и требует сопоставления с ГИС, литологией, керном и испытаниями."

    return CrossMethodAnalysis(
        final_classification=final,
        agreement_percent=agreement,
        agreement_matrix=tuple(matrix_rows),
        contributions=contributions,
        majority_methods=majority,
        dissenting_methods=dissenting,
        quality_issues=tuple(issues),
        disagreement_reasons=tuple(reasons),
        confidence_breakdown=confidence_breakdown,
        expert_conclusion=conclusion,
    )
