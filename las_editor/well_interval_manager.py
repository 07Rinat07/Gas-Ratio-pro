from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from las_editor.formation_evaluation_summary import FormationEvaluationInterval, FormationEvaluationSummary
from las_editor.las_creator import normalize_las_mnemonic

WELL_INTERVAL_MANAGER_SCHEMA = "gas-ratio-pro/well-interval-manager/v1"
WELL_INTERVAL_MANAGER_STORAGE_KEY = "well_interval_manager"

HYDROCARBON_TOKENS = (
    "нефть",
    "газ",
    "конденсат",
    "oil",
    "gas",
    "condensate",
    "gor",
    "hydrocarbon",
)
RESERVOIR_FLAGS = {"probable_reservoir", "possible_reservoir", "hydrocarbon_indication"}


@dataclass(frozen=True)
class IntervalCutoffSet:
    """Cutoff rules used to classify reservoir, net and pay intervals."""

    porosity_curve: str = "POR"
    water_saturation_curve: str = "SW"
    net_to_gross_curve: str = "NG"
    gamma_ray_curve: str = "GR"
    resistivity_curve: str = "RT"
    porosity_min: float = 0.10
    water_saturation_max: float = 0.60
    net_to_gross_min: float = 0.50
    gamma_ray_max: float = 85.0
    resistivity_min: float = 8.0
    min_pay_thickness: float = 0.0


@dataclass(frozen=True)
class WellIntervalIssue:
    """One issue produced while deriving or editing well intervals."""

    severity: str
    code: str
    message: str
    interval_name: str = ""
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class WellInterval:
    """A managed depth interval suitable for UI tables and reports."""

    name: str
    top: float
    base: float
    interval_type: str = "undefined"
    reservoir_flag: str = "unknown"
    pay_flag: str = "unknown"
    fluid_character: str = "Не определено"
    confidence: str = "unknown"
    source: str = "manual"
    sample_count: int = 0
    gross_thickness: float = 0.0
    net_thickness: float = 0.0
    pay_thickness: float = 0.0
    net_to_gross: float | None = None
    pay_to_gross: float | None = None
    pay_to_net: float | None = None
    property_averages: Mapping[str, float | None] | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class WellIntervalSet:
    """Complete interval-management result for one well."""

    schema: str
    generated_at: str
    well_name: str
    intervals: tuple[WellInterval, ...]
    issues: tuple[WellIntervalIssue, ...] = ()
    cutoffs: IntervalCutoffSet = IntervalCutoffSet()
    source_references: tuple[str, ...] = ()


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _thickness(top: float, base: float) -> float:
    return round(abs(float(base) - float(top)), 6)


def _rounded_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _normalized_average_lookup(averages: Mapping[str, float | None] | None) -> dict[str, float | None]:
    return {normalize_las_mnemonic(str(key)): value for key, value in dict(averages or {}).items()}


def _get_average(averages: Mapping[str, float | None] | None, curve: str) -> float | None:
    value = _normalized_average_lookup(averages).get(normalize_las_mnemonic(curve))
    if value is None:
        return None
    return float(value)


def _contains_hydrocarbon(fluid_character: str) -> bool:
    fluid = str(fluid_character or "").lower()
    return any(token in fluid for token in HYDROCARBON_TOKENS)


def classify_interval(
    formation_interval: FormationEvaluationInterval,
    *,
    cutoffs: IntervalCutoffSet = IntervalCutoffSet(),
) -> tuple[str, str, str, tuple[str, ...]]:
    """Classify one formation-evaluation interval as gross/net/pay.

    The function intentionally uses transparent deterministic rules instead of a
    black-box model. That makes the interval classification reproducible and easy to
    explain in engineering reports.
    """

    averages = formation_interval.property_averages or {}
    porosity = _get_average(averages, cutoffs.porosity_curve)
    sw = _get_average(averages, cutoffs.water_saturation_curve)
    ng = _get_average(averages, cutoffs.net_to_gross_curve)
    gr = _get_average(averages, cutoffs.gamma_ray_curve)
    rt = _get_average(averages, cutoffs.resistivity_curve)
    hydrocarbon = _contains_hydrocarbon(formation_interval.fluid_character)

    reservoir_score = 0
    notes: list[str] = []
    if formation_interval.reservoir_flag in RESERVOIR_FLAGS:
        reservoir_score += 2
    if porosity is not None and porosity >= cutoffs.porosity_min:
        reservoir_score += 1
    if ng is not None and ng >= cutoffs.net_to_gross_min:
        reservoir_score += 1
    if gr is not None and gr <= cutoffs.gamma_ray_max:
        reservoir_score += 1
    if rt is not None and rt >= cutoffs.resistivity_min:
        reservoir_score += 1
    if hydrocarbon:
        reservoir_score += 1

    is_gross = formation_interval.sample_count > 0 and reservoir_score >= 1
    is_net = is_gross and (
        (ng is not None and ng >= cutoffs.net_to_gross_min)
        or (porosity is not None and porosity >= cutoffs.porosity_min)
        or formation_interval.reservoir_flag in RESERVOIR_FLAGS
    )
    is_pay = is_net and hydrocarbon
    if sw is not None:
        is_pay = is_pay and sw <= cutoffs.water_saturation_max
    if porosity is not None:
        is_pay = is_pay and porosity >= cutoffs.porosity_min
    if formation_interval.thickness < cutoffs.min_pay_thickness:
        is_pay = False
        notes.append("Interval is thinner than the configured minimum pay thickness.")

    if is_pay:
        return "pay", "pay", "probable_pay", tuple(notes)
    if is_net:
        return "net", "non_pay", "probable_reservoir", tuple(notes)
    if is_gross:
        return "gross", "non_pay", "possible_reservoir", tuple(notes)
    return "non_reservoir", "non_pay", "non_reservoir_or_uncertain", tuple(notes)


def build_well_intervals_from_summary(
    summary: FormationEvaluationSummary,
    *,
    cutoffs: IntervalCutoffSet = IntervalCutoffSet(),
) -> WellIntervalSet:
    """Build managed reservoir/pay intervals from a formation-evaluation summary."""

    issues: list[WellIntervalIssue] = []
    intervals: list[WellInterval] = []
    for index, formation_interval in enumerate(summary.intervals, start=1):
        interval_type, pay_flag, reservoir_flag, notes = classify_interval(formation_interval, cutoffs=cutoffs)
        thickness = _thickness(formation_interval.top, formation_interval.base)
        gross = thickness if interval_type in {"gross", "net", "pay"} else 0.0
        net = thickness if interval_type in {"net", "pay"} else 0.0
        pay = thickness if interval_type == "pay" else 0.0
        all_notes = tuple(formation_interval.notes) + notes
        if formation_interval.qc_error_count:
            issues.append(
                WellIntervalIssue(
                    "warning",
                    "interval_has_qc_errors",
                    "Interval contains QC errors and should be reviewed before final pay-zone reporting.",
                    formation_interval.name,
                    {"qc_errors": formation_interval.qc_error_count},
                )
            )
        intervals.append(
            WellInterval(
                name=formation_interval.name or f"Interval {index}",
                top=float(formation_interval.top),
                base=float(formation_interval.base),
                interval_type=interval_type,
                reservoir_flag=reservoir_flag,
                pay_flag=pay_flag,
                fluid_character=formation_interval.fluid_character,
                confidence=formation_interval.confidence,
                source="formation_evaluation_summary",
                sample_count=formation_interval.sample_count,
                gross_thickness=gross,
                net_thickness=net,
                pay_thickness=pay,
                net_to_gross=_rounded_ratio(net, gross) if gross else None,
                pay_to_gross=_rounded_ratio(pay, gross) if gross else None,
                pay_to_net=_rounded_ratio(pay, net) if net else None,
                property_averages=dict(formation_interval.property_averages or {}),
                notes=all_notes,
            )
        )

    if not intervals:
        issues.append(WellIntervalIssue("warning", "no_intervals", "No intervals were available in the formation summary."))

    return WellIntervalSet(
        schema=WELL_INTERVAL_MANAGER_SCHEMA,
        generated_at=_timestamp_utc(),
        well_name=summary.well_name,
        intervals=tuple(intervals),
        issues=tuple(issues),
        cutoffs=cutoffs,
        source_references=summary.source_references,
    )


def split_well_interval(interval: WellInterval, split_depth: float) -> tuple[WellInterval, WellInterval]:
    """Split one interval by depth while preserving classification metadata."""

    low, high = sorted((float(interval.top), float(interval.base)))
    split = float(split_depth)
    if not (low < split < high):
        raise ValueError("split_depth must be inside interval boundaries")
    first = replace(
        interval,
        name=f"{interval.name} A",
        base=split if interval.top <= interval.base else interval.base,
        top=interval.top if interval.top <= interval.base else split,
        gross_thickness=_thickness(interval.top, split),
        net_thickness=_thickness(interval.top, split) if interval.interval_type in {"net", "pay"} else 0.0,
        pay_thickness=_thickness(interval.top, split) if interval.interval_type == "pay" else 0.0,
    )
    second = replace(
        interval,
        name=f"{interval.name} B",
        top=split if interval.top <= interval.base else interval.top,
        base=interval.base if interval.top <= interval.base else split,
        gross_thickness=_thickness(split, interval.base),
        net_thickness=_thickness(split, interval.base) if interval.interval_type in {"net", "pay"} else 0.0,
        pay_thickness=_thickness(split, interval.base) if interval.interval_type == "pay" else 0.0,
    )
    return (_refresh_interval_ratios(first), _refresh_interval_ratios(second))


def _refresh_interval_ratios(interval: WellInterval) -> WellInterval:
    return replace(
        interval,
        net_to_gross=_rounded_ratio(interval.net_thickness, interval.gross_thickness) if interval.gross_thickness else None,
        pay_to_gross=_rounded_ratio(interval.pay_thickness, interval.gross_thickness) if interval.gross_thickness else None,
        pay_to_net=_rounded_ratio(interval.pay_thickness, interval.net_thickness) if interval.net_thickness else None,
    )


def merge_adjacent_intervals(
    intervals: Sequence[WellInterval],
    *,
    max_gap: float = 0.0,
    group_by: Sequence[str] = ("interval_type", "fluid_character"),
) -> tuple[WellInterval, ...]:
    """Merge adjacent intervals with matching selected attributes."""

    if not intervals:
        return ()
    sorted_intervals = sorted(intervals, key=lambda item: min(item.top, item.base))
    merged: list[WellInterval] = []
    current = sorted_intervals[0]
    for candidate in sorted_intervals[1:]:
        current_low, current_high = sorted((current.top, current.base))
        candidate_low, candidate_high = sorted((candidate.top, candidate.base))
        same_group = all(getattr(current, key) == getattr(candidate, key) for key in group_by)
        gap = candidate_low - current_high
        if same_group and gap <= max_gap:
            gross = current.gross_thickness + candidate.gross_thickness + max(0.0, gap if current.interval_type in {"gross", "net", "pay"} else 0.0)
            net = current.net_thickness + candidate.net_thickness + max(0.0, gap if current.interval_type in {"net", "pay"} else 0.0)
            pay = current.pay_thickness + candidate.pay_thickness + max(0.0, gap if current.interval_type == "pay" else 0.0)
            current = replace(
                current,
                name=f"{current.name} + {candidate.name}",
                top=current_low,
                base=candidate_high,
                sample_count=current.sample_count + candidate.sample_count,
                gross_thickness=round(gross, 6),
                net_thickness=round(net, 6),
                pay_thickness=round(pay, 6),
                notes=current.notes + candidate.notes,
            )
            current = _refresh_interval_ratios(current)
        else:
            merged.append(current)
            current = candidate
    merged.append(current)
    return tuple(merged)


def calculate_interval_thickness_summary(intervals: Iterable[WellInterval]) -> dict[str, Any]:
    """Calculate gross/net/pay thickness totals and ratios."""

    interval_tuple = tuple(intervals)
    gross = round(sum(item.gross_thickness for item in interval_tuple), 6)
    net = round(sum(item.net_thickness for item in interval_tuple), 6)
    pay = round(sum(item.pay_thickness for item in interval_tuple), 6)
    return {
        "interval_count": len(interval_tuple),
        "gross_thickness": gross,
        "net_thickness": net,
        "pay_thickness": pay,
        "net_to_gross": _rounded_ratio(net, gross),
        "pay_to_gross": _rounded_ratio(pay, gross),
        "pay_to_net": _rounded_ratio(pay, net),
    }


def well_interval_table_rows(intervals: Iterable[WellInterval]) -> list[dict[str, Any]]:
    """Return serializable rows for Streamlit tables."""

    rows: list[dict[str, Any]] = []
    for interval in intervals:
        rows.append(
            {
                "name": interval.name,
                "top": interval.top,
                "base": interval.base,
                "type": interval.interval_type,
                "reservoir_flag": interval.reservoir_flag,
                "pay_flag": interval.pay_flag,
                "fluid_character": interval.fluid_character,
                "confidence": interval.confidence,
                "samples": interval.sample_count,
                "gross_thickness": interval.gross_thickness,
                "net_thickness": interval.net_thickness,
                "pay_thickness": interval.pay_thickness,
                "net_to_gross": interval.net_to_gross,
                "pay_to_gross": interval.pay_to_gross,
                "pay_to_net": interval.pay_to_net,
                "source": interval.source,
            }
        )
    return rows


def well_interval_issue_table_rows(issues: Iterable[WellIntervalIssue]) -> list[dict[str, Any]]:
    return [
        {
            "severity": issue.severity,
            "code": issue.code,
            "message": issue.message,
            "interval_name": issue.interval_name,
            "details": dict(issue.details or {}),
        }
        for issue in issues
    ]


def build_well_interval_manifest(interval_set: WellIntervalSet) -> dict[str, Any]:
    thickness = calculate_interval_thickness_summary(interval_set.intervals)
    type_counts: dict[str, int] = {}
    fluid_counts: dict[str, int] = {}
    for interval in interval_set.intervals:
        type_counts[interval.interval_type] = type_counts.get(interval.interval_type, 0) + 1
        fluid_counts[interval.fluid_character] = fluid_counts.get(interval.fluid_character, 0) + 1
    return {
        "schema": interval_set.schema,
        "generated_at": interval_set.generated_at,
        "well_name": interval_set.well_name,
        "interval_count": len(interval_set.intervals),
        "issue_count": len(interval_set.issues),
        "type_counts": type_counts,
        "fluid_counts": fluid_counts,
        "thickness": thickness,
        "cutoffs": interval_set.cutoffs.__dict__,
        "source_references": list(interval_set.source_references),
    }


def render_well_interval_markdown_report(interval_set: WellIntervalSet) -> str:
    """Render a compact Markdown report for pay-zone review."""

    thickness = calculate_interval_thickness_summary(interval_set.intervals)
    lines = [
        "# Well Interval & Pay Zone Summary",
        "",
        f"- Schema: `{interval_set.schema}`",
        f"- Generated at: `{interval_set.generated_at}`",
        f"- Well: {interval_set.well_name or 'N/A'}",
        f"- Intervals: {len(interval_set.intervals)}",
        f"- Gross thickness: {thickness['gross_thickness']}",
        f"- Net thickness: {thickness['net_thickness']}",
        f"- Pay thickness: {thickness['pay_thickness']}",
        f"- Net/Gross: {thickness['net_to_gross']}",
        f"- Pay/Net: {thickness['pay_to_net']}",
        "",
        "## Intervals",
        "",
        "| Interval | Top | Base | Type | Fluid | Gross | Net | Pay | Confidence |",
        "|---|---:|---:|---|---|---:|---:|---:|---|",
    ]
    for interval in interval_set.intervals:
        lines.append(
            f"| {interval.name} | {interval.top} | {interval.base} | {interval.interval_type} | "
            f"{interval.fluid_character} | {interval.gross_thickness} | {interval.net_thickness} | "
            f"{interval.pay_thickness} | {interval.confidence} |"
        )
    if interval_set.issues:
        lines.extend(["", "## Issues", ""])
        for issue in interval_set.issues:
            lines.append(f"- **{issue.severity.upper()}** `{issue.code}`: {issue.message}")
    if interval_set.source_references:
        lines.extend(["", "## Source references", ""])
        for source in interval_set.source_references:
            lines.append(f"- {source}")
    return "\n".join(lines) + "\n"
