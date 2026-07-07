from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

import math
import pandas as pd

from las_editor.las_creator import normalize_las_mnemonic

RESERVOIR_PROPERTY_CALCULATOR_SCHEMA = "gas-ratio-pro/reservoir-property-calculator/v1"
RESERVOIR_PROPERTY_CALCULATOR_STORAGE_KEY = "reservoir_property_calculator"


@dataclass(frozen=True)
class ReservoirPropertyInputCurves:
    """Curve mnemonic mapping used by the Reservoir Property Calculator."""

    depth_curve: str = "DEPT"
    effective_porosity_curve: str = "PHIE"
    water_saturation_curve: str = "SW_ARCHIE"
    net_to_gross_curve: str = "NG"
    pay_flag_curve: str = "PAY"
    area_curve: str = ""


@dataclass(frozen=True)
class ReservoirPropertyParameters:
    """Engineering parameters for deterministic volumetric calculations.

    area_m2 is used when area_curve is not provided. Bo and Bg are intentionally
    explicit because the calculator must not hide reservoir engineering assumptions.
    """

    area_m2: float = 10000.0
    oil_formation_volume_factor: float = 1.2
    gas_formation_volume_factor: float = 0.005
    oil_recovery_factor: float = 0.30
    gas_recovery_factor: float = 0.70
    hydrocarbon_pore_volume_unit: str = "m3"


@dataclass(frozen=True)
class ReservoirPropertyPlan:
    """Validated plan for volume calculations by sample and by interval."""

    input_curves: ReservoirPropertyInputCurves = ReservoirPropertyInputCurves()
    parameters: ReservoirPropertyParameters = ReservoirPropertyParameters()
    depth_top: float | None = None
    depth_base: float | None = None
    output_prefix: str = ""
    overwrite: bool = False


@dataclass(frozen=True)
class ReservoirPropertyIssue:
    """One validation or calculation issue."""

    severity: str
    code: str
    message: str
    curve_name: str = ""
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ReservoirVolumeIntervalSummary:
    """Aggregated reservoir-property summary for one interval."""

    name: str
    top: float
    base: float
    sample_count: int
    gross_thickness: float
    net_thickness: float
    pay_thickness: float
    bulk_rock_volume_m3: float
    net_rock_volume_m3: float
    pore_volume_m3: float
    hydrocarbon_pore_volume_m3: float
    ooip_sm3: float
    recoverable_oil_sm3: float
    ogip_sm3: float
    recoverable_gas_sm3: float
    average_phie: float | None
    average_sw: float | None
    average_ng: float | None


@dataclass(frozen=True)
class ReservoirPropertyResult:
    """Complete Reservoir Property Calculator result."""

    schema: str
    generated_at: str
    data: pd.DataFrame
    plan: ReservoirPropertyPlan
    intervals: tuple[ReservoirVolumeIntervalSummary, ...]
    issues: tuple[ReservoirPropertyIssue, ...] = ()
    source_references: tuple[str, ...] = ()


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve_column(data: pd.DataFrame, mnemonic: str) -> str | None:
    if not mnemonic:
        return None
    target = normalize_las_mnemonic(mnemonic)
    for column in data.columns:
        if normalize_las_mnemonic(str(column)) == target:
            return str(column)
    return None


def _safe_series(data: pd.DataFrame, mnemonic: str) -> pd.Series | None:
    column = _resolve_column(data, mnemonic)
    if column is None:
        return None
    return pd.to_numeric(data[column], errors="coerce")


def _output_name(prefix: str, mnemonic: str) -> str:
    return normalize_las_mnemonic(f"{prefix}{mnemonic}") if prefix else normalize_las_mnemonic(mnemonic)


def validate_reservoir_property_plan(data: pd.DataFrame, plan: ReservoirPropertyPlan) -> tuple[ReservoirPropertyIssue, ...]:
    """Validate the volumetric calculation plan before writing output curves."""

    issues: list[ReservoirPropertyIssue] = []
    if data.empty:
        issues.append(ReservoirPropertyIssue("error", "empty_dataframe", "Input data table is empty."))

    required = {
        "depth": plan.input_curves.depth_curve,
        "effective_porosity": plan.input_curves.effective_porosity_curve,
        "water_saturation": plan.input_curves.water_saturation_curve,
    }
    for role, mnemonic in required.items():
        if _resolve_column(data, mnemonic) is None:
            issues.append(
                ReservoirPropertyIssue(
                    "error",
                    "missing_required_curve",
                    f"Required {role} curve `{mnemonic}` was not found in data.",
                    mnemonic,
                )
            )

    if plan.input_curves.net_to_gross_curve and _resolve_column(data, plan.input_curves.net_to_gross_curve) is None:
        issues.append(
            ReservoirPropertyIssue(
                "warning",
                "missing_net_to_gross_curve",
                f"Net/Gross curve `{plan.input_curves.net_to_gross_curve}` was not found; NG=1.0 will be used.",
                plan.input_curves.net_to_gross_curve,
            )
        )

    if plan.input_curves.area_curve and _resolve_column(data, plan.input_curves.area_curve) is None:
        issues.append(
            ReservoirPropertyIssue(
                "warning",
                "missing_area_curve",
                f"Area curve `{plan.input_curves.area_curve}` was not found; scalar area_m2 will be used.",
                plan.input_curves.area_curve,
            )
        )

    params = plan.parameters
    if params.area_m2 <= 0:
        issues.append(ReservoirPropertyIssue("error", "invalid_area", "area_m2 must be positive."))
    if params.oil_formation_volume_factor <= 0:
        issues.append(ReservoirPropertyIssue("error", "invalid_bo", "Oil formation volume factor Bo must be positive."))
    if params.gas_formation_volume_factor <= 0:
        issues.append(ReservoirPropertyIssue("error", "invalid_bg", "Gas formation volume factor Bg must be positive."))
    if not 0 <= params.oil_recovery_factor <= 1:
        issues.append(ReservoirPropertyIssue("error", "invalid_oil_recovery", "Oil recovery factor must be inside 0..1."))
    if not 0 <= params.gas_recovery_factor <= 1:
        issues.append(ReservoirPropertyIssue("error", "invalid_gas_recovery", "Gas recovery factor must be inside 0..1."))

    if plan.depth_top is not None and plan.depth_base is not None and plan.depth_top > plan.depth_base:
        issues.append(ReservoirPropertyIssue("error", "invalid_depth_window", "depth_top must be <= depth_base."))

    output_curves = [_output_name(plan.output_prefix, name) for name in ("BRV", "NRV", "PV", "HCPV", "OOIP", "OGIP")]
    if not plan.overwrite:
        for name in output_curves:
            if _resolve_column(data, name) is not None:
                issues.append(
                    ReservoirPropertyIssue(
                        "error",
                        "output_curve_exists",
                        f"Output curve `{name}` already exists. Enable overwrite or use output_prefix.",
                        name,
                    )
                )
    return tuple(issues)


def calculate_sample_thickness(depth: pd.Series) -> pd.Series:
    """Calculate representative sample thickness from a depth index.

    The last sample receives the median positive depth step to avoid silently losing
    the final interval contribution.
    """

    depth_numeric = pd.to_numeric(depth, errors="coerce")
    diffs = depth_numeric.shift(-1) - depth_numeric
    positive = diffs[diffs > 0]
    fallback = float(positive.median()) if not positive.empty else 0.0
    return diffs.where(diffs > 0, fallback).fillna(fallback).clip(lower=0.0)


def calculate_bulk_rock_volume(depth: pd.Series, area: pd.Series | float) -> pd.Series:
    """Calculate sample bulk rock volume in cubic metres."""

    thickness = calculate_sample_thickness(depth)
    if isinstance(area, pd.Series):
        area_values = pd.to_numeric(area, errors="coerce").fillna(0.0).clip(lower=0.0)
    else:
        area_values = float(area)
    return thickness * area_values


def calculate_pore_volumes(
    bulk_rock_volume: pd.Series,
    phie: pd.Series,
    sw: pd.Series,
    ng: pd.Series | float = 1.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate net rock volume, pore volume and hydrocarbon pore volume."""

    brv = pd.to_numeric(bulk_rock_volume, errors="coerce").fillna(0.0).clip(lower=0.0)
    por = pd.to_numeric(phie, errors="coerce").fillna(0.0).clip(lower=0.0, upper=1.0)
    water = pd.to_numeric(sw, errors="coerce").fillna(1.0).clip(lower=0.0, upper=1.0)
    if isinstance(ng, pd.Series):
        net_to_gross = pd.to_numeric(ng, errors="coerce").fillna(1.0).clip(lower=0.0, upper=1.0)
    else:
        net_to_gross = float(ng)
    nrv = brv * net_to_gross
    pv = nrv * por
    hcpv = pv * (1.0 - water)
    return nrv, pv, hcpv


def filter_reservoir_depth_window(data: pd.DataFrame, plan: ReservoirPropertyPlan) -> pd.DataFrame:
    """Apply an optional depth window using the configured depth curve."""

    depth_col = _resolve_column(data, plan.input_curves.depth_curve)
    if depth_col is None:
        return data.copy()
    filtered = data.copy()
    depth = pd.to_numeric(filtered[depth_col], errors="coerce")
    if plan.depth_top is not None:
        filtered = filtered.loc[depth >= float(plan.depth_top)]
        depth = pd.to_numeric(filtered[depth_col], errors="coerce")
    if plan.depth_base is not None:
        filtered = filtered.loc[depth <= float(plan.depth_base)]
    return filtered.reset_index(drop=True)


def run_reservoir_property_calculator(
    data: pd.DataFrame,
    plan: ReservoirPropertyPlan | None = None,
    intervals: Sequence[Mapping[str, Any]] | None = None,
    source_references: Sequence[str] | None = None,
) -> ReservoirPropertyResult:
    """Run deterministic reservoir volumetric calculations."""

    plan = plan or ReservoirPropertyPlan()
    issues = list(validate_reservoir_property_plan(data, plan))
    if any(issue.severity == "error" for issue in issues):
        return ReservoirPropertyResult(
            schema=RESERVOIR_PROPERTY_CALCULATOR_SCHEMA,
            generated_at=_timestamp_utc(),
            data=data.copy(),
            plan=plan,
            intervals=(),
            issues=tuple(issues),
            source_references=tuple(source_references or ()),
        )

    working = filter_reservoir_depth_window(data, plan)
    depth = _safe_series(working, plan.input_curves.depth_curve)
    phie = _safe_series(working, plan.input_curves.effective_porosity_curve)
    sw = _safe_series(working, plan.input_curves.water_saturation_curve)
    ng = _safe_series(working, plan.input_curves.net_to_gross_curve)
    area_curve = _safe_series(working, plan.input_curves.area_curve) if plan.input_curves.area_curve else None

    if depth is None or phie is None or sw is None:
        issues.append(ReservoirPropertyIssue("error", "missing_runtime_curve", "Required runtime curve was not resolved."))
        return ReservoirPropertyResult(RESERVOIR_PROPERTY_CALCULATOR_SCHEMA, _timestamp_utc(), working, plan, (), tuple(issues), tuple(source_references or ()))

    area = area_curve if area_curve is not None else plan.parameters.area_m2
    ng_values: pd.Series | float = ng if ng is not None else 1.0

    brv = calculate_bulk_rock_volume(depth, area)
    nrv, pv, hcpv = calculate_pore_volumes(brv, phie, sw, ng_values)
    ooip = hcpv / float(plan.parameters.oil_formation_volume_factor)
    ogip = hcpv / float(plan.parameters.gas_formation_volume_factor)

    out = working.copy()
    out[_output_name(plan.output_prefix, "BRV")] = brv
    out[_output_name(plan.output_prefix, "NRV")] = nrv
    out[_output_name(plan.output_prefix, "PV")] = pv
    out[_output_name(plan.output_prefix, "HCPV")] = hcpv
    out[_output_name(plan.output_prefix, "OOIP")] = ooip
    out[_output_name(plan.output_prefix, "OGIP")] = ogip
    out[_output_name(plan.output_prefix, "REC_OIL")] = ooip * float(plan.parameters.oil_recovery_factor)
    out[_output_name(plan.output_prefix, "REC_GAS")] = ogip * float(plan.parameters.gas_recovery_factor)

    if intervals is None:
        if not depth.dropna().empty:
            intervals = [{"name": "Full evaluated interval", "top": float(depth.min()), "base": float(depth.max())}]
        else:
            intervals = []
    summaries = summarize_reservoir_volume_intervals(out, intervals, plan)

    return ReservoirPropertyResult(
        schema=RESERVOIR_PROPERTY_CALCULATOR_SCHEMA,
        generated_at=_timestamp_utc(),
        data=out,
        plan=plan,
        intervals=summaries,
        issues=tuple(issues),
        source_references=tuple(source_references or ()),
    )


def _mean_or_none(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.mean())


def summarize_reservoir_volume_intervals(
    data: pd.DataFrame,
    intervals: Sequence[Mapping[str, Any]],
    plan: ReservoirPropertyPlan | None = None,
) -> tuple[ReservoirVolumeIntervalSummary, ...]:
    """Aggregate volumetric outputs over user or auto-defined intervals."""

    plan = plan or ReservoirPropertyPlan()
    depth_col = _resolve_column(data, plan.input_curves.depth_curve)
    if depth_col is None:
        return ()

    brv_col = _resolve_column(data, _output_name(plan.output_prefix, "BRV"))
    nrv_col = _resolve_column(data, _output_name(plan.output_prefix, "NRV"))
    pv_col = _resolve_column(data, _output_name(plan.output_prefix, "PV"))
    hcpv_col = _resolve_column(data, _output_name(plan.output_prefix, "HCPV"))
    ooip_col = _resolve_column(data, _output_name(plan.output_prefix, "OOIP"))
    ogip_col = _resolve_column(data, _output_name(plan.output_prefix, "OGIP"))
    rec_oil_col = _resolve_column(data, _output_name(plan.output_prefix, "REC_OIL"))
    rec_gas_col = _resolve_column(data, _output_name(plan.output_prefix, "REC_GAS"))
    phie_col = _resolve_column(data, plan.input_curves.effective_porosity_curve)
    sw_col = _resolve_column(data, plan.input_curves.water_saturation_curve)
    ng_col = _resolve_column(data, plan.input_curves.net_to_gross_curve)
    pay_col = _resolve_column(data, plan.input_curves.pay_flag_curve)

    depth = pd.to_numeric(data[depth_col], errors="coerce")
    summaries: list[ReservoirVolumeIntervalSummary] = []
    for index, interval in enumerate(intervals, start=1):
        top = float(interval.get("top", interval.get("start", depth.min())))
        base = float(interval.get("base", interval.get("bottom", depth.max())))
        name = str(interval.get("name", f"Interval {index}"))
        subset = data.loc[(depth >= top) & (depth <= base)].copy()
        sample_count = int(len(subset))
        gross_thickness = max(0.0, base - top)
        brv_sum = float(pd.to_numeric(subset[brv_col], errors="coerce").sum()) if brv_col else 0.0
        nrv_sum = float(pd.to_numeric(subset[nrv_col], errors="coerce").sum()) if nrv_col else 0.0
        pv_sum = float(pd.to_numeric(subset[pv_col], errors="coerce").sum()) if pv_col else 0.0
        hcpv_sum = float(pd.to_numeric(subset[hcpv_col], errors="coerce").sum()) if hcpv_col else 0.0
        ooip_sum = float(pd.to_numeric(subset[ooip_col], errors="coerce").sum()) if ooip_col else 0.0
        ogip_sum = float(pd.to_numeric(subset[ogip_col], errors="coerce").sum()) if ogip_col else 0.0
        rec_oil_sum = float(pd.to_numeric(subset[rec_oil_col], errors="coerce").sum()) if rec_oil_col else 0.0
        rec_gas_sum = float(pd.to_numeric(subset[rec_gas_col], errors="coerce").sum()) if rec_gas_col else 0.0
        avg_ng = _mean_or_none(subset[ng_col]) if ng_col else 1.0
        net_thickness = gross_thickness * float(avg_ng or 0.0)
        if pay_col:
            pay_ratio = float(pd.to_numeric(subset[pay_col], errors="coerce").fillna(0.0).clip(0, 1).mean()) if sample_count else 0.0
            pay_thickness = gross_thickness * pay_ratio
        else:
            pay_thickness = net_thickness
        summaries.append(
            ReservoirVolumeIntervalSummary(
                name=name,
                top=top,
                base=base,
                sample_count=sample_count,
                gross_thickness=float(gross_thickness),
                net_thickness=float(net_thickness),
                pay_thickness=float(pay_thickness),
                bulk_rock_volume_m3=brv_sum,
                net_rock_volume_m3=nrv_sum,
                pore_volume_m3=pv_sum,
                hydrocarbon_pore_volume_m3=hcpv_sum,
                ooip_sm3=ooip_sum,
                recoverable_oil_sm3=rec_oil_sum,
                ogip_sm3=ogip_sum,
                recoverable_gas_sm3=rec_gas_sum,
                average_phie=_mean_or_none(subset[phie_col]) if phie_col else None,
                average_sw=_mean_or_none(subset[sw_col]) if sw_col else None,
                average_ng=avg_ng,
            )
        )
    return tuple(summaries)


def reservoir_volume_table_rows(intervals: Sequence[ReservoirVolumeIntervalSummary]) -> list[dict[str, Any]]:
    """Convert volume interval summaries to UI-ready rows."""

    rows: list[dict[str, Any]] = []
    for item in intervals:
        row = asdict(item)
        for key, value in list(row.items()):
            if isinstance(value, float):
                row[key] = round(value, 6)
        rows.append(row)
    return rows


def reservoir_property_issue_table_rows(issues: Sequence[ReservoirPropertyIssue]) -> list[dict[str, Any]]:
    """Convert validation issues to UI-ready rows."""

    return [asdict(issue) for issue in issues]


def build_reservoir_property_manifest(result: ReservoirPropertyResult) -> dict[str, Any]:
    """Build a serializable manifest for project history and Report Studio."""

    totals = {
        "bulk_rock_volume_m3": sum(interval.bulk_rock_volume_m3 for interval in result.intervals),
        "net_rock_volume_m3": sum(interval.net_rock_volume_m3 for interval in result.intervals),
        "pore_volume_m3": sum(interval.pore_volume_m3 for interval in result.intervals),
        "hydrocarbon_pore_volume_m3": sum(interval.hydrocarbon_pore_volume_m3 for interval in result.intervals),
        "ooip_sm3": sum(interval.ooip_sm3 for interval in result.intervals),
        "recoverable_oil_sm3": sum(interval.recoverable_oil_sm3 for interval in result.intervals),
        "ogip_sm3": sum(interval.ogip_sm3 for interval in result.intervals),
        "recoverable_gas_sm3": sum(interval.recoverable_gas_sm3 for interval in result.intervals),
    }
    return {
        "schema": result.schema,
        "generated_at": result.generated_at,
        "storage_key": RESERVOIR_PROPERTY_CALCULATOR_STORAGE_KEY,
        "plan": {
            "input_curves": asdict(result.plan.input_curves),
            "parameters": asdict(result.plan.parameters),
            "depth_top": result.plan.depth_top,
            "depth_base": result.plan.depth_base,
            "output_prefix": result.plan.output_prefix,
        },
        "sample_count": int(len(result.data)),
        "interval_count": len(result.intervals),
        "issue_count": len(result.issues),
        "totals": {key: round(value, 6) for key, value in totals.items()},
        "source_references": list(result.source_references),
    }


def render_reservoir_property_markdown_report(result: ReservoirPropertyResult) -> str:
    """Render a compact Markdown report for the Reservoir Property Calculator."""

    manifest = build_reservoir_property_manifest(result)
    lines = [
        "# Reservoir Property Calculator Report",
        "",
        f"Generated: {result.generated_at}",
        f"Samples: {len(result.data)}",
        f"Intervals: {len(result.intervals)}",
        "",
        "## Totals",
    ]
    for key, value in manifest["totals"].items():
        lines.append(f"- {key}: {value}")
    if result.intervals:
        lines.extend(["", "## Interval Summary", "", "| Interval | Top | Base | HCPV m3 | OOIP Sm3 | OGIP Sm3 |", "|---|---:|---:|---:|---:|---:|"])
        for item in result.intervals:
            lines.append(
                f"| {item.name} | {item.top:.3f} | {item.base:.3f} | {item.hydrocarbon_pore_volume_m3:.3f} | {item.ooip_sm3:.3f} | {item.ogip_sm3:.3f} |"
            )
    if result.issues:
        lines.extend(["", "## Issues"])
        for issue in result.issues:
            lines.append(f"- **{issue.severity.upper()}** `{issue.code}`: {issue.message}")
    if result.source_references:
        lines.extend(["", "## Source References"])
        for source in result.source_references:
            lines.append(f"- {source}")
    return "\n".join(lines).strip() + "\n"
