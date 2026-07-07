from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import math
import pandas as pd

from las_editor.las_creator import normalize_las_mnemonic
from las_editor.petrophysical_workspace import ArchieParameters, calculate_archie_water_saturation

ADVANCED_SATURATION_SCHEMA = "gas-ratio-pro/advanced-saturation-models/v1"
ADVANCED_SATURATION_STORAGE_KEY = "advanced_saturation_models"


@dataclass(frozen=True)
class SaturationInputCurves:
    """Mnemonic mapping used by advanced saturation calculations."""

    depth_curve: str = "DEPT"
    effective_porosity_curve: str = "PHIE"
    resistivity_curve: str = "RT"
    shale_volume_curve: str = "VSH"


@dataclass(frozen=True)
class ShalySandParameters:
    """Shared parameters for Simandoux and Indonesia shaly-sand models."""

    rw: float = 0.10
    rsh: float = 2.0
    a: float = 1.0
    m: float = 2.0
    n: float = 2.0


@dataclass(frozen=True)
class DualWaterParameters:
    """Foundation-level Dual Water parameters.

    The implementation is intentionally transparent and conservative: Archie free-water
    saturation is blended with a bound-water contribution driven by shale volume.
    """

    rw_free: float = 0.10
    bound_water_saturation: float = 0.35
    bound_water_weight: float = 0.50
    a: float = 1.0
    m: float = 2.0
    n: float = 2.0


@dataclass(frozen=True)
class AdvancedSaturationPlan:
    """Validated plan for reproducible advanced saturation modeling."""

    input_curves: SaturationInputCurves = SaturationInputCurves()
    archie: ArchieParameters = ArchieParameters()
    shaly_sand: ShalySandParameters = ShalySandParameters()
    dual_water: DualWaterParameters = DualWaterParameters()
    output_prefix: str = ""
    overwrite: bool = False


@dataclass(frozen=True)
class SaturationModelIssue:
    """One validation/calculation issue produced by the saturation module."""

    severity: str
    code: str
    message: str
    curve_name: str = ""
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class SaturationModelComparison:
    """Summary comparison for one interval or the full logged section."""

    name: str
    top: float | None
    base: float | None
    sample_count: int
    avg_vsh: float | None
    avg_sw_archie: float | None
    avg_sw_simandoux: float | None
    avg_sw_indonesia: float | None
    avg_sw_dual_water: float | None
    max_model_spread: float | None
    recommended_model: str
    confidence: str
    note: str


@dataclass(frozen=True)
class AdvancedSaturationResult:
    """Complete output of advanced saturation modeling."""

    schema: str
    generated_at: str
    data: pd.DataFrame
    plan: AdvancedSaturationPlan
    issues: tuple[SaturationModelIssue, ...] = ()
    comparisons: tuple[SaturationModelComparison, ...] = ()
    source_references: tuple[str, ...] = ()


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve_column(data: pd.DataFrame, mnemonic: str) -> str | None:
    target = normalize_las_mnemonic(mnemonic)
    for column in data.columns:
        if normalize_las_mnemonic(str(column)) == target:
            return str(column)
    return None


def _series(data: pd.DataFrame, mnemonic: str) -> pd.Series | None:
    column = _resolve_column(data, mnemonic)
    if column is None:
        return None
    return pd.to_numeric(data[column], errors="coerce")


def _out(plan: AdvancedSaturationPlan, mnemonic: str) -> str:
    return normalize_las_mnemonic(f"{plan.output_prefix}{mnemonic}") if plan.output_prefix else normalize_las_mnemonic(mnemonic)


def _positive(value: float) -> bool:
    try:
        return float(value) > 0
    except Exception:
        return False


def validate_advanced_saturation_plan(data: pd.DataFrame, plan: AdvancedSaturationPlan) -> tuple[SaturationModelIssue, ...]:
    """Validate required input curves, numeric parameters and output conflicts."""

    issues: list[SaturationModelIssue] = []
    if data.empty:
        issues.append(SaturationModelIssue("error", "empty_dataframe", "Input data table is empty."))

    required = {
        "effective_porosity": plan.input_curves.effective_porosity_curve,
        "resistivity": plan.input_curves.resistivity_curve,
        "shale_volume": plan.input_curves.shale_volume_curve,
    }
    for role, mnemonic in required.items():
        if _resolve_column(data, mnemonic) is None:
            issues.append(
                SaturationModelIssue(
                    "error",
                    "missing_required_curve",
                    f"Required {role} curve `{mnemonic}` was not found in data.",
                    mnemonic,
                )
            )

    numeric_parameters = {
        "archie.rw": plan.archie.rw,
        "archie.a": plan.archie.a,
        "archie.m": plan.archie.m,
        "archie.n": plan.archie.n,
        "shaly_sand.rw": plan.shaly_sand.rw,
        "shaly_sand.rsh": plan.shaly_sand.rsh,
        "shaly_sand.a": plan.shaly_sand.a,
        "shaly_sand.m": plan.shaly_sand.m,
        "shaly_sand.n": plan.shaly_sand.n,
        "dual_water.rw_free": plan.dual_water.rw_free,
        "dual_water.a": plan.dual_water.a,
        "dual_water.m": plan.dual_water.m,
        "dual_water.n": plan.dual_water.n,
    }
    for name, value in numeric_parameters.items():
        if not _positive(value):
            issues.append(SaturationModelIssue("error", "invalid_parameter", f"Parameter `{name}` must be positive.", details={"value": value}))

    if not 0 <= plan.dual_water.bound_water_saturation <= 1:
        issues.append(SaturationModelIssue("error", "invalid_parameter", "Dual Water bound_water_saturation must be inside 0..1."))
    if not 0 <= plan.dual_water.bound_water_weight <= 1:
        issues.append(SaturationModelIssue("error", "invalid_parameter", "Dual Water bound_water_weight must be inside 0..1."))

    outputs = [_out(plan, name) for name in ("SW_ARCHIE", "SW_SIMANDOUX", "SW_INDONESIA", "SW_DUAL_WATER", "SW_MODEL_SPREAD")]
    if not plan.overwrite:
        for output in outputs:
            if _resolve_column(data, output) is not None:
                issues.append(SaturationModelIssue("error", "output_curve_exists", f"Output curve `{output}` already exists.", output))

    return tuple(issues)


def calculate_simandoux_water_saturation(
    phie: pd.Series,
    rt: pd.Series,
    vsh: pd.Series,
    params: ShalySandParameters = ShalySandParameters(),
) -> pd.Series:
    """Calculate water saturation using a quadratic Simandoux form.

    The equation is solved as: A*Sw^2 + B*Sw - C = 0, where
    A = phi^m/(a*Rw), B = Vsh/Rsh, C = 1/Rt.
    """

    phi = pd.to_numeric(phie, errors="coerce").clip(lower=0)
    rt_numeric = pd.to_numeric(rt, errors="coerce")
    clay = pd.to_numeric(vsh, errors="coerce").clip(lower=0, upper=1)
    a = float(params.a)
    rw = float(params.rw)
    rsh = float(params.rsh)
    m = float(params.m)

    coefficient_a = (phi ** m) / (a * rw)
    coefficient_b = clay / rsh
    coefficient_c = 1.0 / rt_numeric.replace(0, pd.NA)
    discriminant = (coefficient_b ** 2) + (4.0 * coefficient_a * coefficient_c)
    sw = (-coefficient_b + discriminant.pow(0.5)) / (2.0 * coefficient_a.replace(0, pd.NA))
    return sw.replace([math.inf, -math.inf], pd.NA).clip(lower=0.0, upper=1.0)


def calculate_indonesia_water_saturation(
    phie: pd.Series,
    rt: pd.Series,
    vsh: pd.Series,
    params: ShalySandParameters = ShalySandParameters(),
) -> pd.Series:
    """Calculate water saturation using an Indonesia shaly-sand approximation."""

    phi = pd.to_numeric(phie, errors="coerce").clip(lower=0)
    rt_numeric = pd.to_numeric(rt, errors="coerce")
    clay = pd.to_numeric(vsh, errors="coerce").clip(lower=0, upper=1)
    a = float(params.a)
    rw = float(params.rw)
    rsh = float(params.rsh)
    m = float(params.m)
    n = float(params.n)

    total_conductivity_root = (1.0 / rt_numeric.replace(0, pd.NA)).pow(0.5)
    shale_term = (clay ** (1.0 - clay / 2.0)) / (rsh ** 0.5)
    porosity_term = (phi ** (m / 2.0)).replace(0, pd.NA)
    sw_root = ((total_conductivity_root - shale_term) * ((a * rw) ** 0.5)) / porosity_term
    sw = sw_root.clip(lower=0.0) ** (2.0 / n)
    return sw.replace([math.inf, -math.inf], pd.NA).clip(lower=0.0, upper=1.0)


def calculate_dual_water_saturation(
    phie: pd.Series,
    rt: pd.Series,
    vsh: pd.Series,
    params: DualWaterParameters = DualWaterParameters(),
) -> pd.Series:
    """Calculate a conservative Dual Water foundation curve.

    The free-water saturation is calculated by Archie and then blended with a
    shale-bound-water component. This gives a stable first implementation while keeping
    the model transparent and testable until full Dual Water calibration is introduced.
    """

    archie = calculate_archie_water_saturation(
        phie,
        rt,
        ArchieParameters(a=params.a, m=params.m, n=params.n, rw=params.rw_free),
    )
    clay = pd.to_numeric(vsh, errors="coerce").clip(lower=0.0, upper=1.0)
    bound = float(params.bound_water_saturation) * clay * float(params.bound_water_weight)
    free = archie * (1.0 - clay * float(params.bound_water_weight))
    return (free + bound).replace([math.inf, -math.inf], pd.NA).clip(lower=0.0, upper=1.0)


def compare_saturation_models(
    data: pd.DataFrame,
    *,
    plan: AdvancedSaturationPlan = AdvancedSaturationPlan(),
    intervals: Sequence[Mapping[str, Any]] = (),
) -> tuple[SaturationModelComparison, ...]:
    """Aggregate model differences for the full well or named intervals."""

    depth_col = _resolve_column(data, plan.input_curves.depth_curve) or _resolve_column(data, "DEPTH") or _resolve_column(data, "MD")
    depth = pd.to_numeric(data[depth_col], errors="coerce") if depth_col else None
    if not intervals:
        if depth is not None and not depth.dropna().empty:
            intervals = ({"name": "Full logged interval", "top": float(depth.min()), "base": float(depth.max())},)
        else:
            intervals = ({"name": "Full table", "top": None, "base": None},)

    sw_cols = {
        "archie": _resolve_column(data, _out(plan, "SW_ARCHIE")),
        "simandoux": _resolve_column(data, _out(plan, "SW_SIMANDOUX")),
        "indonesia": _resolve_column(data, _out(plan, "SW_INDONESIA")),
        "dual_water": _resolve_column(data, _out(plan, "SW_DUAL_WATER")),
    }
    vsh_col = _resolve_column(data, plan.input_curves.shale_volume_curve)
    spread_col = _resolve_column(data, _out(plan, "SW_MODEL_SPREAD"))

    comparisons: list[SaturationModelComparison] = []
    for idx, interval in enumerate(intervals, start=1):
        top_raw = interval.get("top", interval.get("start"))
        base_raw = interval.get("base", interval.get("stop"))
        if depth is not None and top_raw is not None and base_raw is not None:
            top = float(top_raw)
            base = float(base_raw)
            low, high = sorted((top, base))
            subset = data.loc[(depth >= low) & (depth <= high)]
        else:
            top = float(top_raw) if top_raw is not None else None
            base = float(base_raw) if base_raw is not None else None
            subset = data

        avg_vsh = _mean(subset[vsh_col]) if vsh_col and not subset.empty else None
        avg_archie = _mean(subset[sw_cols["archie"]]) if sw_cols["archie"] and not subset.empty else None
        avg_simandoux = _mean(subset[sw_cols["simandoux"]]) if sw_cols["simandoux"] and not subset.empty else None
        avg_indonesia = _mean(subset[sw_cols["indonesia"]]) if sw_cols["indonesia"] and not subset.empty else None
        avg_dual = _mean(subset[sw_cols["dual_water"]]) if sw_cols["dual_water"] and not subset.empty else None
        max_spread = _max(subset[spread_col]) if spread_col and not subset.empty else None
        recommendation, confidence, note = recommend_saturation_model(avg_vsh, max_spread)
        comparisons.append(
            SaturationModelComparison(
                name=str(interval.get("name") or f"Interval {idx}"),
                top=top,
                base=base,
                sample_count=int(len(subset)),
                avg_vsh=avg_vsh,
                avg_sw_archie=avg_archie,
                avg_sw_simandoux=avg_simandoux,
                avg_sw_indonesia=avg_indonesia,
                avg_sw_dual_water=avg_dual,
                max_model_spread=max_spread,
                recommended_model=recommendation,
                confidence=confidence,
                note=note,
            )
        )
    return tuple(comparisons)


def recommend_saturation_model(avg_vsh: float | None, max_model_spread: float | None) -> tuple[str, str, str]:
    """Return deterministic model recommendation from shale volume and model spread."""

    if avg_vsh is None:
        return "review_required", "low", "Average Vsh is unavailable."
    spread = max_model_spread if max_model_spread is not None else 0.0
    if avg_vsh <= 0.15:
        model = "archie"
        note = "Clean formation; Archie is acceptable as a first-pass model."
    elif avg_vsh <= 0.45:
        model = "indonesia"
        note = "Shaly sand; Indonesia model is recommended for comparison with Simandoux."
    else:
        model = "dual_water_review"
        note = "High shale volume; advanced calibration and Dual Water review are recommended."
    confidence = "high" if spread <= 0.15 else "medium" if spread <= 0.30 else "low"
    return model, confidence, note


def run_advanced_saturation_models(
    data: pd.DataFrame,
    *,
    plan: AdvancedSaturationPlan = AdvancedSaturationPlan(),
    intervals: Sequence[Mapping[str, Any]] | None = None,
    source_references: Sequence[str] = (),
) -> AdvancedSaturationResult:
    """Run Archie, Simandoux, Indonesia and Dual Water foundation saturation models."""

    issues = list(validate_advanced_saturation_plan(data, plan))
    if any(issue.severity == "error" for issue in issues):
        return AdvancedSaturationResult(
            schema=ADVANCED_SATURATION_SCHEMA,
            generated_at=_timestamp_utc(),
            data=data.copy(),
            plan=plan,
            issues=tuple(issues),
            comparisons=(),
            source_references=tuple(source_references),
        )

    result = data.copy()
    phie = _series(result, plan.input_curves.effective_porosity_curve)
    rt = _series(result, plan.input_curves.resistivity_curve)
    vsh = _series(result, plan.input_curves.shale_volume_curve)
    assert phie is not None and rt is not None and vsh is not None

    sw_archie = calculate_archie_water_saturation(phie, rt, plan.archie)
    sw_simandoux = calculate_simandoux_water_saturation(phie, rt, vsh, plan.shaly_sand)
    sw_indonesia = calculate_indonesia_water_saturation(phie, rt, vsh, plan.shaly_sand)
    sw_dual = calculate_dual_water_saturation(phie, rt, vsh, plan.dual_water)
    model_stack = pd.concat([sw_archie, sw_simandoux, sw_indonesia, sw_dual], axis=1)
    spread = model_stack.max(axis=1, skipna=True) - model_stack.min(axis=1, skipna=True)

    result[_out(plan, "SW_ARCHIE")] = sw_archie
    result[_out(plan, "SW_SIMANDOUX")] = sw_simandoux
    result[_out(plan, "SW_INDONESIA")] = sw_indonesia
    result[_out(plan, "SW_DUAL_WATER")] = sw_dual
    result[_out(plan, "SW_MODEL_SPREAD")] = spread

    comparisons = compare_saturation_models(result, plan=plan, intervals=intervals or ())
    return AdvancedSaturationResult(
        schema=ADVANCED_SATURATION_SCHEMA,
        generated_at=_timestamp_utc(),
        data=result,
        plan=plan,
        issues=tuple(issues),
        comparisons=comparisons,
        source_references=tuple(source_references),
    )


def _mean(series: pd.Series) -> float | None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    return round(float(numeric.mean()), 6)


def _max(series: pd.Series) -> float | None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    return round(float(numeric.max()), 6)


def saturation_issue_table_rows(issues: Iterable[SaturationModelIssue]) -> list[dict[str, Any]]:
    return [
        {
            "severity": issue.severity,
            "code": issue.code,
            "message": issue.message,
            "curve_name": issue.curve_name,
            "details": dict(issue.details or {}),
        }
        for issue in issues
    ]


def saturation_comparison_table_rows(comparisons: Iterable[SaturationModelComparison]) -> list[dict[str, Any]]:
    return [asdict(comparison) for comparison in comparisons]


def build_advanced_saturation_manifest(result: AdvancedSaturationResult) -> dict[str, Any]:
    return {
        "schema": result.schema,
        "generated_at": result.generated_at,
        "row_count": int(len(result.data)),
        "curve_count": int(len(result.data.columns)),
        "issue_count": len(result.issues),
        "comparison_count": len(result.comparisons),
        "plan": {
            "input_curves": asdict(result.plan.input_curves),
            "archie": asdict(result.plan.archie),
            "shaly_sand": asdict(result.plan.shaly_sand),
            "dual_water": asdict(result.plan.dual_water),
            "output_prefix": result.plan.output_prefix,
            "overwrite": result.plan.overwrite,
        },
        "outputs": [_out(result.plan, name) for name in ("SW_ARCHIE", "SW_SIMANDOUX", "SW_INDONESIA", "SW_DUAL_WATER", "SW_MODEL_SPREAD")],
        "source_references": list(result.source_references),
    }


def render_advanced_saturation_markdown_report(result: AdvancedSaturationResult) -> str:
    manifest = build_advanced_saturation_manifest(result)
    lines = [
        "# Advanced Saturation Models Report",
        "",
        f"- Schema: `{result.schema}`",
        f"- Generated at: `{result.generated_at}`",
        f"- Rows: {manifest['row_count']}",
        f"- Curves: {manifest['curve_count']}",
        f"- Issues: {len(result.issues)}",
        f"- Comparisons: {len(result.comparisons)}",
        "",
        "## Output curves",
        "",
    ]
    for output in manifest["outputs"]:
        lines.append(f"- `{output}`")
    if result.comparisons:
        lines.extend([
            "",
            "## Model comparison",
            "",
            "| Interval | Samples | Avg Vsh | Archie | Simandoux | Indonesia | Dual Water | Max spread | Recommendation | Confidence |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ])
        for comparison in result.comparisons:
            lines.append(
                f"| {comparison.name} | {comparison.sample_count} | {comparison.avg_vsh} | {comparison.avg_sw_archie} | "
                f"{comparison.avg_sw_simandoux} | {comparison.avg_sw_indonesia} | {comparison.avg_sw_dual_water} | "
                f"{comparison.max_model_spread} | {comparison.recommended_model} | {comparison.confidence} |"
            )
    if result.issues:
        lines.extend(["", "## Issues", ""])
        for issue in result.issues:
            lines.append(f"- **{issue.severity.upper()}** `{issue.code}`: {issue.message}")
    if result.source_references:
        lines.extend(["", "## Source references", ""])
        for source in result.source_references:
            lines.append(f"- {source}")
    return "\n".join(lines) + "\n"
