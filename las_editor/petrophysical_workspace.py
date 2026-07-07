from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import math
import pandas as pd

from las_editor.las_creator import DEFAULT_NULL_VALUE, normalize_las_mnemonic

PETROPHYSICAL_WORKSPACE_SCHEMA = "gas-ratio-pro/petrophysical-workspace/v1"
PETROPHYSICAL_WORKSPACE_STORAGE_KEY = "petrophysical_workspace"


@dataclass(frozen=True)
class PetrophysicalCutoffSet:
    """Transparent cutoff rules for deterministic reservoir/pay evaluation."""

    shale_volume_max: float = 0.45
    effective_porosity_min: float = 0.10
    water_saturation_max: float = 0.60
    resistivity_min: float = 8.0
    net_to_gross_min: float = 0.50


@dataclass(frozen=True)
class ArchieParameters:
    """Archie water-saturation parameters.

    a: tortuosity factor, m: cementation exponent, n: saturation exponent,
    rw: formation-water resistivity.
    """

    a: float = 1.0
    m: float = 2.0
    n: float = 2.0
    rw: float = 0.10


@dataclass(frozen=True)
class PetrophysicalInputCurves:
    """Curve mnemonic mapping used by the petrophysical workspace."""

    depth_curve: str = "DEPT"
    gamma_ray_curve: str = "GR"
    porosity_curve: str = "POR"
    resistivity_curve: str = "RT"
    water_saturation_curve: str = "SW"
    net_to_gross_curve: str = "NG"


@dataclass(frozen=True)
class ShaleVolumeParameters:
    """Parameters for shale-volume calculation from Gamma Ray."""

    method: str = "linear"
    gr_clean: float = 35.0
    gr_shale: float = 120.0


@dataclass(frozen=True)
class PetrophysicalPlan:
    """Validated calculation plan for reproducible petrophysical processing."""

    input_curves: PetrophysicalInputCurves = PetrophysicalInputCurves()
    shale_volume: ShaleVolumeParameters = ShaleVolumeParameters()
    archie: ArchieParameters = ArchieParameters()
    cutoffs: PetrophysicalCutoffSet = PetrophysicalCutoffSet()
    output_prefix: str = ""
    null_value: float = DEFAULT_NULL_VALUE
    overwrite: bool = False


@dataclass(frozen=True)
class PetrophysicalIssue:
    """One issue produced by petrophysical validation or calculation."""

    severity: str
    code: str
    message: str
    curve_name: str = ""
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class PetrophysicalIntervalSummary:
    """Aggregated petrophysical summary for a depth interval."""

    name: str
    top: float
    base: float
    sample_count: int
    gross_thickness: float
    net_thickness: float
    pay_thickness: float
    net_to_gross: float | None
    pay_to_gross: float | None
    pay_to_net: float | None
    avg_vsh: float | None
    avg_phie: float | None
    avg_sw: float | None
    avg_so: float | None
    dominant_flag: str


@dataclass(frozen=True)
class PetrophysicalResult:
    """Complete result of petrophysical workspace calculations."""

    schema: str
    generated_at: str
    data: pd.DataFrame
    plan: PetrophysicalPlan
    issues: tuple[PetrophysicalIssue, ...] = ()
    intervals: tuple[PetrophysicalIntervalSummary, ...] = ()
    source_references: tuple[str, ...] = ()


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve_column(data: pd.DataFrame, mnemonic: str) -> str | None:
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


def validate_petrophysical_plan(data: pd.DataFrame, plan: PetrophysicalPlan) -> tuple[PetrophysicalIssue, ...]:
    """Validate inputs before any petrophysical curve is written."""

    issues: list[PetrophysicalIssue] = []
    if data.empty:
        issues.append(PetrophysicalIssue("error", "empty_dataframe", "Input data table is empty."))

    required = {
        "gamma_ray": plan.input_curves.gamma_ray_curve,
        "porosity": plan.input_curves.porosity_curve,
        "resistivity": plan.input_curves.resistivity_curve,
    }
    for role, mnemonic in required.items():
        if _resolve_column(data, mnemonic) is None:
            issues.append(
                PetrophysicalIssue(
                    "error",
                    "missing_required_curve",
                    f"Required {role} curve `{mnemonic}` was not found in data.",
                    mnemonic,
                )
            )

    if plan.shale_volume.gr_shale == plan.shale_volume.gr_clean:
        issues.append(PetrophysicalIssue("error", "invalid_gr_endpoints", "GR shale and GR clean must be different."))
    if plan.archie.rw <= 0 or plan.archie.a <= 0 or plan.archie.m <= 0 or plan.archie.n <= 0:
        issues.append(PetrophysicalIssue("error", "invalid_archie_parameters", "Archie parameters a, m, n and rw must be positive."))
    if not 0 <= plan.cutoffs.shale_volume_max <= 1:
        issues.append(PetrophysicalIssue("error", "invalid_vsh_cutoff", "Vsh cutoff must be inside 0..1."))
    if not 0 <= plan.cutoffs.effective_porosity_min <= 1:
        issues.append(PetrophysicalIssue("error", "invalid_phie_cutoff", "Effective porosity cutoff must be inside 0..1."))
    if not 0 <= plan.cutoffs.water_saturation_max <= 1:
        issues.append(PetrophysicalIssue("error", "invalid_sw_cutoff", "Water saturation cutoff must be inside 0..1."))

    output_curves = [_output_name(plan.output_prefix, name) for name in ("VSH", "PHIE", "SW_ARCHIE", "SO", "NET", "PAY")]
    if not plan.overwrite:
        existing = {_resolve_column(data, name) for name in output_curves}
        for name, column in zip(output_curves, existing):
            if column is not None:
                issues.append(
                    PetrophysicalIssue(
                        "error",
                        "output_curve_exists",
                        f"Output curve `{name}` already exists. Enable overwrite or use output_prefix.",
                        name,
                    )
                )
    return tuple(issues)


def calculate_shale_volume(gr: pd.Series, params: ShaleVolumeParameters) -> pd.Series:
    """Calculate shale volume from Gamma Ray using transparent deterministic methods."""

    igr = (pd.to_numeric(gr, errors="coerce") - float(params.gr_clean)) / (float(params.gr_shale) - float(params.gr_clean))
    igr = igr.clip(lower=0.0, upper=1.0)
    method = str(params.method or "linear").lower()
    if method in {"linear", "larionov_tertiary"}:
        if method == "larionov_tertiary":
            return (0.083 * ((2 ** (3.7 * igr)) - 1)).clip(lower=0.0, upper=1.0)
        return igr
    if method == "larionov_old_rocks":
        return (0.33 * ((2 ** (2 * igr)) - 1)).clip(lower=0.0, upper=1.0)
    if method == "clavier":
        return (1.7 - (3.38 - (igr + 0.7) ** 2) ** 0.5).clip(lower=0.0, upper=1.0)
    raise ValueError(f"Unsupported shale volume method: {params.method}")


def calculate_effective_porosity(total_porosity: pd.Series, shale_volume: pd.Series) -> pd.Series:
    """Calculate effective porosity as total porosity corrected by shale volume."""

    por = pd.to_numeric(total_porosity, errors="coerce")
    vsh = pd.to_numeric(shale_volume, errors="coerce").clip(lower=0.0, upper=1.0)
    return (por * (1.0 - vsh)).clip(lower=0.0)


def calculate_archie_water_saturation(phie: pd.Series, rt: pd.Series, params: ArchieParameters) -> pd.Series:
    """Calculate water saturation by Archie equation and clamp to 0..1."""

    phie_numeric = pd.to_numeric(phie, errors="coerce")
    rt_numeric = pd.to_numeric(rt, errors="coerce")
    denominator = ((phie_numeric ** float(params.m)) * rt_numeric).replace(0, pd.NA)
    sw = ((float(params.a) * float(params.rw)) / denominator) ** (1.0 / float(params.n))
    return sw.replace([math.inf, -math.inf], pd.NA).clip(lower=0.0, upper=1.0)


def calculate_net_pay_flags(
    *,
    vsh: pd.Series,
    phie: pd.Series,
    sw: pd.Series,
    rt: pd.Series,
    cutoffs: PetrophysicalCutoffSet,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return reservoir, net and pay flags from explicit engineering cutoffs."""

    reservoir = (pd.to_numeric(vsh, errors="coerce") <= cutoffs.shale_volume_max).astype(int)
    net = (
        (reservoir == 1)
        & (pd.to_numeric(phie, errors="coerce") >= cutoffs.effective_porosity_min)
    ).astype(int)
    pay = (
        (net == 1)
        & (pd.to_numeric(sw, errors="coerce") <= cutoffs.water_saturation_max)
        & (pd.to_numeric(rt, errors="coerce") >= cutoffs.resistivity_min)
    ).astype(int)
    return reservoir, net, pay


def run_petrophysical_workspace(
    data: pd.DataFrame,
    *,
    plan: PetrophysicalPlan = PetrophysicalPlan(),
    intervals: Sequence[Mapping[str, Any]] | None = None,
    source_references: Sequence[str] = (),
) -> PetrophysicalResult:
    """Run foundation petrophysical calculations on a LAS-like table."""

    issues = list(validate_petrophysical_plan(data, plan))
    if any(issue.severity == "error" for issue in issues):
        return PetrophysicalResult(
            schema=PETROPHYSICAL_WORKSPACE_SCHEMA,
            generated_at=_timestamp_utc(),
            data=data.copy(),
            plan=plan,
            issues=tuple(issues),
            intervals=(),
            source_references=tuple(source_references),
        )

    result = data.copy()
    gr = _safe_series(result, plan.input_curves.gamma_ray_curve)
    por = _safe_series(result, plan.input_curves.porosity_curve)
    rt = _safe_series(result, plan.input_curves.resistivity_curve)
    assert gr is not None and por is not None and rt is not None

    vsh = calculate_shale_volume(gr, plan.shale_volume)
    phie = calculate_effective_porosity(por, vsh)
    sw_existing = _safe_series(result, plan.input_curves.water_saturation_curve)
    sw = sw_existing.clip(lower=0.0, upper=1.0) if sw_existing is not None else calculate_archie_water_saturation(phie, rt, plan.archie)
    so = (1.0 - sw).clip(lower=0.0, upper=1.0)
    reservoir, net, pay = calculate_net_pay_flags(vsh=vsh, phie=phie, sw=sw, rt=rt, cutoffs=plan.cutoffs)

    output_map = {
        "VSH": vsh,
        "PHIE": phie,
        "SW_ARCHIE": sw,
        "SO": so,
        "RES": reservoir,
        "NET": net,
        "PAY": pay,
        "NG": net.astype(float),
    }
    for mnemonic, values in output_map.items():
        result[_output_name(plan.output_prefix, mnemonic)] = values

    interval_summaries = summarize_petrophysical_intervals(result, plan=plan, intervals=intervals or ())
    return PetrophysicalResult(
        schema=PETROPHYSICAL_WORKSPACE_SCHEMA,
        generated_at=_timestamp_utc(),
        data=result,
        plan=plan,
        issues=tuple(issues),
        intervals=interval_summaries,
        source_references=tuple(source_references),
    )


def summarize_petrophysical_intervals(
    data: pd.DataFrame,
    *,
    plan: PetrophysicalPlan = PetrophysicalPlan(),
    intervals: Sequence[Mapping[str, Any]] = (),
) -> tuple[PetrophysicalIntervalSummary, ...]:
    """Aggregate calculated petrophysical curves over named intervals."""

    depth_col = _resolve_column(data, plan.input_curves.depth_curve) or _resolve_column(data, "DEPTH") or _resolve_column(data, "MD")
    if depth_col is None:
        return ()
    depth = pd.to_numeric(data[depth_col], errors="coerce")
    vsh_col = _resolve_column(data, _output_name(plan.output_prefix, "VSH"))
    phie_col = _resolve_column(data, _output_name(plan.output_prefix, "PHIE"))
    sw_col = _resolve_column(data, _output_name(plan.output_prefix, "SW_ARCHIE"))
    so_col = _resolve_column(data, _output_name(plan.output_prefix, "SO"))
    net_col = _resolve_column(data, _output_name(plan.output_prefix, "NET"))
    pay_col = _resolve_column(data, _output_name(plan.output_prefix, "PAY"))
    if not intervals:
        clean_depth = depth.dropna()
        if clean_depth.empty:
            return ()
        intervals = ({"name": "Full logged interval", "top": float(clean_depth.min()), "base": float(clean_depth.max())},)

    summaries: list[PetrophysicalIntervalSummary] = []
    for index, interval in enumerate(intervals, start=1):
        top = float(interval.get("top", interval.get("start", 0.0)))
        base = float(interval.get("base", interval.get("stop", top)))
        low, high = sorted((top, base))
        mask = (depth >= low) & (depth <= high)
        subset = data.loc[mask]
        sample_count = int(len(subset))
        gross_thickness = round(abs(base - top), 6)
        net_fraction = float(pd.to_numeric(subset[net_col], errors="coerce").mean()) if net_col and sample_count else 0.0
        pay_fraction = float(pd.to_numeric(subset[pay_col], errors="coerce").mean()) if pay_col and sample_count else 0.0
        net_thickness = round(gross_thickness * net_fraction, 6)
        pay_thickness = round(gross_thickness * pay_fraction, 6)
        dominant_flag = "pay" if pay_fraction >= 0.5 else "net" if net_fraction >= 0.5 else "non_reservoir"
        summaries.append(
            PetrophysicalIntervalSummary(
                name=str(interval.get("name") or f"Interval {index}"),
                top=top,
                base=base,
                sample_count=sample_count,
                gross_thickness=gross_thickness,
                net_thickness=net_thickness,
                pay_thickness=pay_thickness,
                net_to_gross=_ratio(net_thickness, gross_thickness),
                pay_to_gross=_ratio(pay_thickness, gross_thickness),
                pay_to_net=_ratio(pay_thickness, net_thickness),
                avg_vsh=_mean_or_none(subset[vsh_col]) if vsh_col and sample_count else None,
                avg_phie=_mean_or_none(subset[phie_col]) if phie_col and sample_count else None,
                avg_sw=_mean_or_none(subset[sw_col]) if sw_col and sample_count else None,
                avg_so=_mean_or_none(subset[so_col]) if so_col and sample_count else None,
                dominant_flag=dominant_flag,
            )
        )
    return tuple(summaries)


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _mean_or_none(values: pd.Series) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    return round(float(numeric.mean()), 6)


def petrophysical_issue_table_rows(issues: Iterable[PetrophysicalIssue]) -> list[dict[str, Any]]:
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


def petrophysical_interval_table_rows(intervals: Iterable[PetrophysicalIntervalSummary]) -> list[dict[str, Any]]:
    return [asdict(interval) for interval in intervals]


def build_petrophysical_manifest(result: PetrophysicalResult) -> dict[str, Any]:
    return {
        "schema": result.schema,
        "generated_at": result.generated_at,
        "row_count": int(len(result.data)),
        "curve_count": int(len(result.data.columns)),
        "issue_count": len(result.issues),
        "interval_count": len(result.intervals),
        "plan": {
            "input_curves": asdict(result.plan.input_curves),
            "shale_volume": asdict(result.plan.shale_volume),
            "archie": asdict(result.plan.archie),
            "cutoffs": asdict(result.plan.cutoffs),
            "output_prefix": result.plan.output_prefix,
            "overwrite": result.plan.overwrite,
        },
        "outputs": [_output_name(result.plan.output_prefix, name) for name in ("VSH", "PHIE", "SW_ARCHIE", "SO", "RES", "NET", "PAY", "NG")],
        "source_references": list(result.source_references),
    }


def render_petrophysical_markdown_report(result: PetrophysicalResult) -> str:
    manifest = build_petrophysical_manifest(result)
    lines = [
        "# Petrophysical Workspace Summary",
        "",
        f"- Schema: `{result.schema}`",
        f"- Generated at: `{result.generated_at}`",
        f"- Rows: {manifest['row_count']}",
        f"- Curves: {manifest['curve_count']}",
        f"- Issues: {len(result.issues)}",
        f"- Intervals: {len(result.intervals)}",
        "",
        "## Output curves",
        "",
    ]
    for output in manifest["outputs"]:
        lines.append(f"- `{output}`")
    if result.intervals:
        lines.extend([
            "",
            "## Interval summary",
            "",
            "| Interval | Top | Base | Gross | Net | Pay | N/G | Pay/Net | Avg Vsh | Avg PHIE | Avg Sw | Flag |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ])
        for interval in result.intervals:
            lines.append(
                f"| {interval.name} | {interval.top} | {interval.base} | {interval.gross_thickness} | "
                f"{interval.net_thickness} | {interval.pay_thickness} | {interval.net_to_gross} | "
                f"{interval.pay_to_net} | {interval.avg_vsh} | {interval.avg_phie} | {interval.avg_sw} | {interval.dominant_flag} |"
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
