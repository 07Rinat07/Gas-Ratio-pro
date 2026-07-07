from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from las_editor.las_creator import DEFAULT_NULL_VALUE, normalize_las_mnemonic
from las_editor.las_quality_control import LasQualityIssue, LasQualityReport, run_las_quality_control
from las_editor.mud_gas_interpretation import (
    MudGasIntervalSummary,
    MudGasInterpretationResult,
    build_mud_gas_source_columns,
    interpret_mud_gas_dataframe,
)

FORMATION_EVALUATION_SCHEMA = "gas-ratio-pro/formation-evaluation-summary/v1"
FORMATION_EVALUATION_STORAGE_KEY = "formation_evaluation_summary"
DEFAULT_DEPTH_CURVES = ("DEPT", "DEPTH", "MD", "TVD")
DEFAULT_PROPERTY_CURVES = (
    "GR",
    "RT",
    "RHOB",
    "NPHI",
    "POR",
    "PHI",
    "PERM",
    "SW",
    "SO",
    "SG",
    "NG",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
)


@dataclass(frozen=True)
class FormationEvaluationIssue:
    """One issue produced while building a formation-evaluation summary."""

    severity: str
    code: str
    message: str
    interval_name: str = ""
    curve: str = ""
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class FormationEvaluationInterval:
    """Engineering summary for one depth interval."""

    name: str
    top: float
    base: float
    sample_count: int
    thickness: float
    fluid_character: str = "Не определено"
    confidence: str = "unknown"
    reservoir_flag: str = "unknown"
    qc_error_count: int = 0
    qc_warning_count: int = 0
    property_averages: Mapping[str, float | None] | None = None
    property_min: Mapping[str, float | None] | None = None
    property_max: Mapping[str, float | None] | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class FormationEvaluationSummary:
    """Full formation-evaluation summary for UI, export and reports."""

    schema: str
    generated_at: str
    well_name: str
    row_count: int
    depth_curve: str
    intervals: tuple[FormationEvaluationInterval, ...]
    issues: tuple[FormationEvaluationIssue, ...] = ()
    qc_report: LasQualityReport | None = None
    mud_gas_result: MudGasInterpretationResult | None = None
    source_references: tuple[str, ...] = ()


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _round_optional(value: Any, digits: int = 6) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _find_column(df: pd.DataFrame, candidates: Sequence[str]) -> str:
    lookup = {normalize_las_mnemonic(str(column)): str(column) for column in df.columns}
    for candidate in candidates:
        normalized = normalize_las_mnemonic(candidate)
        if normalized in lookup:
            return lookup[normalized]
    return str(df.columns[0]) if len(df.columns) else ""


def _existing_property_curves(df: pd.DataFrame, property_curves: Iterable[str] | None = None) -> tuple[str, ...]:
    requested = tuple(property_curves or DEFAULT_PROPERTY_CURVES)
    lookup = {normalize_las_mnemonic(str(column)): str(column) for column in df.columns}
    result: list[str] = []
    for mnemonic in requested:
        normalized = normalize_las_mnemonic(mnemonic)
        if normalized in lookup and lookup[normalized] not in result:
            result.append(lookup[normalized])
    return tuple(result)


def _dominant(values: Iterable[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return "Не определено"
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _confidence(values: Iterable[str]) -> str:
    ranking = {"high": 3, "medium": 2, "low": 1, "unknown": 0, "": 0}
    best = 0
    for value in values:
        best = max(best, ranking.get(str(value).lower(), 0))
    for name, rank in ranking.items():
        if rank == best and name:
            return name
    return "unknown"


def _reservoir_flag(interval_df: pd.DataFrame, averages: Mapping[str, float | None], fluid_character: str) -> str:
    normalized_averages = {normalize_las_mnemonic(key): value for key, value in averages.items()}
    por = normalized_averages.get("POR") or normalized_averages.get("PHI")
    sw = normalized_averages.get("SW")
    rt = normalized_averages.get("RT")
    ng = normalized_averages.get("NG")
    fluid = fluid_character.lower()

    hydrocarbon_by_fluid = any(token in fluid for token in ("нефть", "газ", "конденсат", "oil", "gas", "condensate"))
    reservoir_by_props = False
    if por is not None and por >= 0.08:
        reservoir_by_props = True
    if ng is not None and ng >= 0.5:
        reservoir_by_props = True
    if rt is not None and rt >= 10:
        reservoir_by_props = True
    if sw is not None and sw <= 0.6:
        reservoir_by_props = True

    if hydrocarbon_by_fluid and reservoir_by_props:
        return "probable_reservoir"
    if hydrocarbon_by_fluid:
        return "hydrocarbon_indication"
    if reservoir_by_props:
        return "possible_reservoir"
    if len(interval_df) == 0:
        return "no_data"
    return "non_reservoir_or_uncertain"


def _qc_counts_for_interval(issues: Sequence[LasQualityIssue], top: float, base: float) -> tuple[int, int]:
    errors = 0
    warnings = 0
    low, high = sorted((top, base))
    for issue in issues:
        depth = issue.depth
        if depth is not None and not (low <= float(depth) <= high):
            continue
        if issue.severity == "error":
            errors += 1
        elif issue.severity == "warning":
            warnings += 1
    return errors, warnings


def _default_intervals_from_depths(depths: pd.Series, *, interval_count: int = 3) -> tuple[tuple[str, float, float], ...]:
    numeric = _numeric(depths).dropna()
    if numeric.empty:
        return ()
    top = float(numeric.min())
    base = float(numeric.max())
    if top == base or interval_count <= 1:
        return (("Full interval", top, base),)
    step = (base - top) / interval_count
    intervals: list[tuple[str, float, float]] = []
    for index in range(interval_count):
        interval_top = top + step * index
        interval_base = base if index == interval_count - 1 else top + step * (index + 1)
        intervals.append((f"Interval {index + 1}", round(interval_top, 6), round(interval_base, 6)))
    return tuple(intervals)


def _intervals_from_mud_gas(mud_gas_result: MudGasInterpretationResult | None) -> tuple[tuple[str, float, float], ...]:
    if not mud_gas_result or not mud_gas_result.intervals:
        return ()
    return tuple((f"Mud gas interval {index + 1}", interval.top, interval.base) for index, interval in enumerate(mud_gas_result.intervals))


def build_formation_evaluation_summary(
    df: pd.DataFrame,
    *,
    well_name: str = "",
    depth_curve: str | None = None,
    intervals: Sequence[tuple[str, float, float]] | None = None,
    property_curves: Iterable[str] | None = None,
    qc_report: LasQualityReport | None = None,
    mud_gas_result: MudGasInterpretationResult | None = None,
    source_references: Iterable[str] | None = None,
) -> FormationEvaluationSummary:
    """Build a compact engineering summary from LAS-like data and optional analyses.

    The function is intentionally backend-only and UI-ready: Streamlit can render the
    returned table helpers without knowing how QC or mud-gas interpretation works.
    """

    issues: list[FormationEvaluationIssue] = []
    if df.empty:
        issues.append(FormationEvaluationIssue("error", "empty_dataframe", "Input LAS table is empty."))
        return FormationEvaluationSummary(
            schema=FORMATION_EVALUATION_SCHEMA,
            generated_at=_timestamp_utc(),
            well_name=well_name,
            row_count=0,
            depth_curve="",
            intervals=(),
            issues=tuple(issues),
            qc_report=qc_report,
            mud_gas_result=mud_gas_result,
            source_references=tuple(source_references or ()),
        )

    resolved_depth = _find_column(df, (depth_curve,) if depth_curve else DEFAULT_DEPTH_CURVES)
    if not resolved_depth:
        issues.append(FormationEvaluationIssue("error", "missing_depth", "Depth curve is missing."))

    if qc_report is None:
        qc_report = run_las_quality_control(df, depth_curve=resolved_depth or None)
    if mud_gas_result is None:
        source_columns, gas_issues = build_mud_gas_source_columns(df, depth_curve=resolved_depth or "DEPT")
        if not any(issue.severity == "error" for issue in gas_issues):
            mud_gas_result = interpret_mud_gas_dataframe(df, source_columns=source_columns)

    selected_intervals = tuple(intervals or ())
    if not selected_intervals:
        selected_intervals = _intervals_from_mud_gas(mud_gas_result)
    if not selected_intervals and resolved_depth:
        selected_intervals = _default_intervals_from_depths(df[resolved_depth])

    property_names = _existing_property_curves(df, property_curves)
    depth_values = _numeric(df[resolved_depth]) if resolved_depth else pd.Series(dtype=float)
    summary_intervals: list[FormationEvaluationInterval] = []

    for interval_index, (name, top, base) in enumerate(selected_intervals, start=1):
        low, high = sorted((float(top), float(base)))
        mask = depth_values.between(low, high, inclusive="both") if resolved_depth else pd.Series(False, index=df.index)
        interval_df = df.loc[mask]
        averages: dict[str, float | None] = {}
        mins: dict[str, float | None] = {}
        maxs: dict[str, float | None] = {}
        for curve in property_names:
            values = _numeric(interval_df[curve]).replace(float(DEFAULT_NULL_VALUE), pd.NA).dropna()
            averages[curve] = _round_optional(values.mean()) if not values.empty else None
            mins[curve] = _round_optional(values.min()) if not values.empty else None
            maxs[curve] = _round_optional(values.max()) if not values.empty else None

        mud_rows = []
        if mud_gas_result:
            mud_rows = [row for row in mud_gas_result.rows if low <= row.depth <= high]
        fluid_character = _dominant(row.fluid_character for row in mud_rows)
        confidence = _confidence(row.confidence for row in mud_rows)
        qc_errors, qc_warnings = _qc_counts_for_interval(qc_report.issues if qc_report else (), low, high)
        reservoir_flag = _reservoir_flag(interval_df, averages, fluid_character)
        notes: list[str] = []
        if not mud_rows:
            notes.append("Mud gas interpretation is unavailable for this interval.")
        if qc_errors:
            notes.append(f"QC has {qc_errors} error(s) inside interval.")
        if qc_warnings:
            notes.append(f"QC has {qc_warnings} warning(s) inside interval.")

        summary_intervals.append(
            FormationEvaluationInterval(
                name=name or f"Interval {interval_index}",
                top=float(top),
                base=float(base),
                sample_count=int(len(interval_df)),
                thickness=round(abs(float(base) - float(top)), 6),
                fluid_character=fluid_character,
                confidence=confidence,
                reservoir_flag=reservoir_flag,
                qc_error_count=qc_errors,
                qc_warning_count=qc_warnings,
                property_averages=averages,
                property_min=mins,
                property_max=maxs,
                notes=tuple(notes),
            )
        )

    if not summary_intervals:
        issues.append(FormationEvaluationIssue("warning", "no_intervals", "No depth intervals were available for summary."))

    return FormationEvaluationSummary(
        schema=FORMATION_EVALUATION_SCHEMA,
        generated_at=_timestamp_utc(),
        well_name=well_name,
        row_count=int(len(df)),
        depth_curve=resolved_depth,
        intervals=tuple(summary_intervals),
        issues=tuple(issues),
        qc_report=qc_report,
        mud_gas_result=mud_gas_result,
        source_references=tuple(source_references or ()),
    )


def formation_evaluation_interval_table_rows(intervals: Iterable[FormationEvaluationInterval]) -> list[dict[str, Any]]:
    """Return serializable interval rows for Streamlit tables."""

    rows: list[dict[str, Any]] = []
    for interval in intervals:
        averages = dict(interval.property_averages or {})
        row: dict[str, Any] = {
            "name": interval.name,
            "top": interval.top,
            "base": interval.base,
            "thickness": interval.thickness,
            "sample_count": interval.sample_count,
            "fluid_character": interval.fluid_character,
            "confidence": interval.confidence,
            "reservoir_flag": interval.reservoir_flag,
            "qc_errors": interval.qc_error_count,
            "qc_warnings": interval.qc_warning_count,
        }
        for curve, value in averages.items():
            row[f"avg_{normalize_las_mnemonic(curve).lower()}"] = value
        rows.append(row)
    return rows


def formation_evaluation_issue_table_rows(issues: Iterable[FormationEvaluationIssue]) -> list[dict[str, Any]]:
    return [
        {
            "severity": issue.severity,
            "code": issue.code,
            "message": issue.message,
            "interval_name": issue.interval_name,
            "curve": issue.curve,
            "details": dict(issue.details or {}),
        }
        for issue in issues
    ]


def build_formation_evaluation_manifest(summary: FormationEvaluationSummary) -> dict[str, Any]:
    """Build an audit/export manifest for a formation-evaluation summary."""

    reservoir_counts: dict[str, int] = {}
    fluid_counts: dict[str, int] = {}
    for interval in summary.intervals:
        reservoir_counts[interval.reservoir_flag] = reservoir_counts.get(interval.reservoir_flag, 0) + 1
        fluid_counts[interval.fluid_character] = fluid_counts.get(interval.fluid_character, 0) + 1
    return {
        "schema": summary.schema,
        "generated_at": summary.generated_at,
        "well_name": summary.well_name,
        "row_count": summary.row_count,
        "depth_curve": summary.depth_curve,
        "interval_count": len(summary.intervals),
        "issue_count": len(summary.issues),
        "qc_issue_count": len(summary.qc_report.issues) if summary.qc_report else 0,
        "mud_gas_row_count": len(summary.mud_gas_result.rows) if summary.mud_gas_result else 0,
        "reservoir_counts": reservoir_counts,
        "fluid_counts": fluid_counts,
        "source_references": list(summary.source_references),
    }


def render_formation_evaluation_markdown_report(summary: FormationEvaluationSummary) -> str:
    """Render a concise Markdown engineering report."""

    lines = [
        "# Formation Evaluation Summary",
        "",
        f"- Schema: `{summary.schema}`",
        f"- Generated at: `{summary.generated_at}`",
        f"- Well: {summary.well_name or 'N/A'}",
        f"- Rows: {summary.row_count}",
        f"- Depth curve: {summary.depth_curve or 'N/A'}",
        "",
        "## Interval summary",
        "",
        "| Interval | Top | Base | Samples | Fluid | Confidence | Reservoir flag | QC errors | QC warnings |",
        "|---|---:|---:|---:|---|---|---|---:|---:|",
    ]
    for interval in summary.intervals:
        lines.append(
            "| {name} | {top} | {base} | {samples} | {fluid} | {confidence} | {flag} | {errors} | {warnings} |".format(
                name=interval.name,
                top=interval.top,
                base=interval.base,
                samples=interval.sample_count,
                fluid=interval.fluid_character,
                confidence=interval.confidence,
                flag=interval.reservoir_flag,
                errors=interval.qc_error_count,
                warnings=interval.qc_warning_count,
            )
        )

    if summary.source_references:
        lines.extend(["", "## Source references", ""])
        for reference in summary.source_references:
            lines.append(f"- `{reference}`")

    if summary.issues:
        lines.extend(["", "## Issues", ""])
        for issue in summary.issues:
            lines.append(f"- **{issue.severity.upper()}** `{issue.code}`: {issue.message}")

    return "\n".join(lines).strip() + "\n"
