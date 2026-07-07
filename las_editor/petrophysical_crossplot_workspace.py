from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

import math
import pandas as pd

from las_editor.las_creator import normalize_las_mnemonic

PETROPHYSICAL_CROSSPLOT_SCHEMA = "gas-ratio-pro/petrophysical-crossplot-workspace/v1"
PETROPHYSICAL_CROSSPLOT_STORAGE_KEY = "petrophysical_crossplot_workspace"


@dataclass(frozen=True)
class CrossplotInputCurves:
    """Curve mnemonic mapping used by the Petrophysical Crossplot Workspace."""

    depth_curve: str = "DEPT"
    porosity_curve: str = "PHIE"
    resistivity_curve: str = "RT"
    water_saturation_curve: str = "SW_ARCHIE"
    shale_volume_curve: str = "VSH"
    density_curve: str = "RHOB"
    neutron_curve: str = "NPHI"
    sonic_curve: str = "DT"
    gamma_ray_curve: str = "GR"


@dataclass(frozen=True)
class CrossplotPlan:
    """Validated plan for deterministic crossplot specification generation."""

    input_curves: CrossplotInputCurves = CrossplotInputCurves()
    plots: tuple[str, ...] = ("pickett", "hingle", "buckles", "rhob_nphi", "dt_rhob")
    depth_top: float | None = None
    depth_base: float | None = None
    cluster_by: str = "vsh"
    low_cutoff: float = 0.25
    high_cutoff: float = 0.45
    max_points: int | None = None


@dataclass(frozen=True)
class CrossplotIssue:
    """One validation or calculation issue produced by crossplot workspace."""

    severity: str
    code: str
    message: str
    plot_name: str = ""
    curve_name: str = ""
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class CrossplotTrend:
    """Linear trend summary for one crossplot."""

    slope: float | None
    intercept: float | None
    r_squared: float | None
    sample_count: int


@dataclass(frozen=True)
class CrossplotClusterSummary:
    """Simple deterministic cluster summary prepared for UI tables."""

    cluster_name: str
    sample_count: int
    depth_top: float | None
    depth_base: float | None
    x_mean: float | None
    y_mean: float | None
    note: str


@dataclass(frozen=True)
class CrossplotSpec:
    """Serializable crossplot specification for future Plotly/UI rendering."""

    name: str
    title: str
    x_curve: str
    y_curve: str
    color_curve: str | None
    x_label: str
    y_label: str
    x_scale: str = "linear"
    y_scale: str = "linear"
    point_count: int = 0
    trend: CrossplotTrend | None = None
    clusters: tuple[CrossplotClusterSummary, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PetrophysicalCrossplotResult:
    """Complete Petrophysical Crossplot Workspace result."""

    schema: str
    generated_at: str
    data: pd.DataFrame
    plan: CrossplotPlan
    specs: tuple[CrossplotSpec, ...]
    issues: tuple[CrossplotIssue, ...] = ()
    source_references: tuple[str, ...] = ()


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve_column(data: pd.DataFrame, mnemonic: str) -> str | None:
    target = normalize_las_mnemonic(mnemonic)
    for column in data.columns:
        if normalize_las_mnemonic(str(column)) == target:
            return str(column)
    return None


def _numeric(data: pd.DataFrame, mnemonic: str) -> pd.Series | None:
    column = _resolve_column(data, mnemonic)
    if column is None:
        return None
    return pd.to_numeric(data[column], errors="coerce")


def _finite_pair_table(data: pd.DataFrame, x_curve: str, y_curve: str, color_curve: str | None = None, depth_curve: str | None = None) -> pd.DataFrame:
    x_col = _resolve_column(data, x_curve)
    y_col = _resolve_column(data, y_curve)
    if x_col is None or y_col is None:
        return pd.DataFrame(columns=["x", "y"])
    table = pd.DataFrame({"x": pd.to_numeric(data[x_col], errors="coerce"), "y": pd.to_numeric(data[y_col], errors="coerce")})
    if color_curve:
        c_col = _resolve_column(data, color_curve)
        if c_col is not None:
            table["color"] = pd.to_numeric(data[c_col], errors="coerce")
    if depth_curve:
        d_col = _resolve_column(data, depth_curve)
        if d_col is not None:
            table["depth"] = pd.to_numeric(data[d_col], errors="coerce")
    table = table.replace([math.inf, -math.inf], pd.NA).dropna(subset=["x", "y"])
    return table


def filter_crossplot_depth_window(data: pd.DataFrame, plan: CrossplotPlan) -> pd.DataFrame:
    """Return data filtered by optional top/base depth window."""

    depth = _numeric(data, plan.input_curves.depth_curve)
    if depth is None or (plan.depth_top is None and plan.depth_base is None):
        return data.copy()
    mask = pd.Series(True, index=data.index)
    if plan.depth_top is not None:
        mask &= depth >= float(plan.depth_top)
    if plan.depth_base is not None:
        mask &= depth <= float(plan.depth_base)
    return data.loc[mask].copy()


def validate_crossplot_plan(data: pd.DataFrame, plan: CrossplotPlan) -> tuple[CrossplotIssue, ...]:
    """Validate requested plots and available input curves."""

    issues: list[CrossplotIssue] = []
    if data.empty:
        issues.append(CrossplotIssue("error", "empty_dataframe", "Input data table is empty."))

    required_by_plot: dict[str, tuple[str, ...]] = {
        "pickett": (plan.input_curves.porosity_curve, plan.input_curves.resistivity_curve),
        "hingle": (plan.input_curves.porosity_curve, plan.input_curves.resistivity_curve),
        "buckles": (plan.input_curves.porosity_curve, plan.input_curves.water_saturation_curve),
        "rhob_nphi": (plan.input_curves.density_curve, plan.input_curves.neutron_curve),
        "dt_rhob": (plan.input_curves.sonic_curve, plan.input_curves.density_curve),
        "gr_resistivity": (plan.input_curves.gamma_ray_curve, plan.input_curves.resistivity_curve),
    }
    supported = set(required_by_plot)
    for plot in plan.plots:
        normalized_plot = str(plot).lower()
        if normalized_plot not in supported:
            issues.append(CrossplotIssue("error", "unsupported_plot", f"Unsupported crossplot `{plot}`.", str(plot)))
            continue
        for mnemonic in required_by_plot[normalized_plot]:
            if _resolve_column(data, mnemonic) is None:
                issues.append(CrossplotIssue("error", "missing_required_curve", f"Curve `{mnemonic}` is required for `{plot}`.", str(plot), mnemonic))

    if plan.depth_top is not None and plan.depth_base is not None and float(plan.depth_top) > float(plan.depth_base):
        issues.append(CrossplotIssue("error", "invalid_depth_window", "depth_top must be shallower than depth_base."))
    if not 0 <= plan.low_cutoff <= plan.high_cutoff <= 1:
        issues.append(CrossplotIssue("error", "invalid_cluster_cutoffs", "Cluster cutoffs must satisfy 0 <= low <= high <= 1."))
    if plan.max_points is not None and int(plan.max_points) <= 0:
        issues.append(CrossplotIssue("error", "invalid_max_points", "max_points must be positive when provided."))
    return tuple(issues)


def calculate_linear_trend(table: pd.DataFrame) -> CrossplotTrend:
    """Calculate a transparent ordinary least-squares trend for x/y crossplot data."""

    clean = table[["x", "y"]].dropna()
    count = int(len(clean))
    if count < 2:
        return CrossplotTrend(None, None, None, count)
    x = clean["x"].astype(float)
    y = clean["y"].astype(float)
    x_mean = float(x.mean())
    y_mean = float(y.mean())
    denominator = float(((x - x_mean) ** 2).sum())
    if denominator == 0:
        return CrossplotTrend(None, None, None, count)
    slope = float(((x - x_mean) * (y - y_mean)).sum() / denominator)
    intercept = float(y_mean - slope * x_mean)
    y_hat = slope * x + intercept
    ss_res = float(((y - y_hat) ** 2).sum())
    ss_tot = float(((y - y_mean) ** 2).sum())
    r_squared = None if ss_tot == 0 else max(0.0, min(1.0, 1.0 - ss_res / ss_tot))
    return CrossplotTrend(round(slope, 6), round(intercept, 6), None if r_squared is None else round(r_squared, 6), count)


def summarize_crossplot_clusters(table: pd.DataFrame, *, low_cutoff: float, high_cutoff: float, color_label: str = "VSH") -> tuple[CrossplotClusterSummary, ...]:
    """Build simple cluster summaries from the color column.

    The function intentionally keeps clustering deterministic and explainable. It is not
    a machine-learning classifier; it prepares engineering buckets for UI review.
    """

    if table.empty or "color" not in table.columns:
        return ()
    color = pd.to_numeric(table["color"], errors="coerce")
    labels = pd.Series("medium", index=table.index)
    labels[color <= low_cutoff] = "low"
    labels[color >= high_cutoff] = "high"
    names = {"low": f"Low {color_label}", "medium": f"Medium {color_label}", "high": f"High {color_label}"}
    notes = {"low": "cleaner/reservoir-prone points", "medium": "mixed transition points", "high": "shaly or low-quality points"}
    rows: list[CrossplotClusterSummary] = []
    for label in ("low", "medium", "high"):
        subset = table.loc[labels == label]
        if subset.empty:
            continue
        depth_top = float(subset["depth"].min()) if "depth" in subset.columns and subset["depth"].notna().any() else None
        depth_base = float(subset["depth"].max()) if "depth" in subset.columns and subset["depth"].notna().any() else None
        rows.append(
            CrossplotClusterSummary(
                cluster_name=names[label],
                sample_count=int(len(subset)),
                depth_top=depth_top,
                depth_base=depth_base,
                x_mean=round(float(subset["x"].mean()), 6),
                y_mean=round(float(subset["y"].mean()), 6),
                note=notes[label],
            )
        )
    return tuple(rows)


def build_crossplot_spec(data: pd.DataFrame, plot_name: str, plan: CrossplotPlan) -> CrossplotSpec:
    """Build one serializable crossplot specification without rendering UI."""

    curves = plan.input_curves
    plot = plot_name.lower()
    definitions: dict[str, dict[str, Any]] = {
        "pickett": {
            "title": "Pickett Plot — Resistivity vs Porosity",
            "x": curves.porosity_curve,
            "y": curves.resistivity_curve,
            "color": curves.shale_volume_curve,
            "x_label": "Porosity / Effective Porosity",
            "y_label": "Deep Resistivity",
            "x_scale": "linear",
            "y_scale": "log",
            "notes": ("Used for Archie-style water saturation review and clean reservoir screening.",),
        },
        "hingle": {
            "title": "Hingle Plot — Resistivity Porosity Transform",
            "x": curves.porosity_curve,
            "y": curves.resistivity_curve,
            "color": curves.water_saturation_curve,
            "x_label": "Porosity / Effective Porosity",
            "y_label": "Resistivity",
            "x_scale": "linear",
            "y_scale": "log",
            "notes": ("Foundation specification for Hingle-style water-resistivity trend review.",),
        },
        "buckles": {
            "title": "Buckles Plot — Water Saturation vs Porosity",
            "x": curves.porosity_curve,
            "y": curves.water_saturation_curve,
            "color": curves.shale_volume_curve,
            "x_label": "Porosity / Effective Porosity",
            "y_label": "Water Saturation",
            "x_scale": "linear",
            "y_scale": "linear",
            "notes": ("Used for bulk-volume-water and pay-zone screening.",),
        },
        "rhob_nphi": {
            "title": "Density-Neutron Crossplot",
            "x": curves.neutron_curve,
            "y": curves.density_curve,
            "color": curves.gamma_ray_curve,
            "x_label": "Neutron Porosity",
            "y_label": "Bulk Density",
            "x_scale": "linear",
            "y_scale": "linear",
            "notes": ("Used for lithology and gas-effect review.",),
        },
        "dt_rhob": {
            "title": "Sonic-Density Crossplot",
            "x": curves.sonic_curve,
            "y": curves.density_curve,
            "color": curves.gamma_ray_curve,
            "x_label": "Sonic Transit Time",
            "y_label": "Bulk Density",
            "x_scale": "linear",
            "y_scale": "linear",
            "notes": ("Used for compaction, lithology and data-quality review.",),
        },
        "gr_resistivity": {
            "title": "Gamma Ray vs Resistivity Crossplot",
            "x": curves.gamma_ray_curve,
            "y": curves.resistivity_curve,
            "color": curves.shale_volume_curve,
            "x_label": "Gamma Ray",
            "y_label": "Resistivity",
            "x_scale": "linear",
            "y_scale": "log",
            "notes": ("Used for quick shale/reservoir and hydrocarbon screening.",),
        },
    }
    definition = definitions[plot]
    table = _finite_pair_table(data, definition["x"], definition["y"], definition["color"], curves.depth_curve)
    if plan.max_points is not None and len(table) > int(plan.max_points):
        table = table.iloc[: int(plan.max_points)].copy()
    trend = calculate_linear_trend(table)
    clusters = summarize_crossplot_clusters(table, low_cutoff=plan.low_cutoff, high_cutoff=plan.high_cutoff, color_label=definition["color"] or "color")
    return CrossplotSpec(
        name=plot,
        title=definition["title"],
        x_curve=normalize_las_mnemonic(definition["x"]),
        y_curve=normalize_las_mnemonic(definition["y"]),
        color_curve=normalize_las_mnemonic(definition["color"]) if definition["color"] else None,
        x_label=definition["x_label"],
        y_label=definition["y_label"],
        x_scale=definition["x_scale"],
        y_scale=definition["y_scale"],
        point_count=int(len(table)),
        trend=trend,
        clusters=clusters,
        notes=tuple(definition["notes"]),
    )


def run_petrophysical_crossplot_workspace(
    data: pd.DataFrame,
    *,
    plan: CrossplotPlan = CrossplotPlan(),
    source_references: Sequence[str] = (),
) -> PetrophysicalCrossplotResult:
    """Generate crossplot specifications, trend summaries and UI-ready metadata."""

    issues = list(validate_crossplot_plan(data, plan))
    if any(issue.severity == "error" for issue in issues):
        return PetrophysicalCrossplotResult(
            schema=PETROPHYSICAL_CROSSPLOT_SCHEMA,
            generated_at=_timestamp_utc(),
            data=data.copy(),
            plan=plan,
            specs=(),
            issues=tuple(issues),
            source_references=tuple(source_references),
        )
    filtered = filter_crossplot_depth_window(data, plan)
    specs: list[CrossplotSpec] = []
    for plot in plan.plots:
        spec = build_crossplot_spec(filtered, str(plot), plan)
        specs.append(spec)
        if spec.point_count == 0:
            issues.append(CrossplotIssue("warning", "empty_crossplot", f"Crossplot `{plot}` has no valid x/y points after filtering.", str(plot)))
    return PetrophysicalCrossplotResult(
        schema=PETROPHYSICAL_CROSSPLOT_SCHEMA,
        generated_at=_timestamp_utc(),
        data=filtered,
        plan=plan,
        specs=tuple(specs),
        issues=tuple(issues),
        source_references=tuple(source_references),
    )


def crossplot_spec_table_rows(specs: Sequence[CrossplotSpec]) -> list[dict[str, Any]]:
    """Convert specs into rows suitable for Streamlit tables."""

    rows: list[dict[str, Any]] = []
    for spec in specs:
        rows.append(
            {
                "name": spec.name,
                "title": spec.title,
                "x_curve": spec.x_curve,
                "y_curve": spec.y_curve,
                "color_curve": spec.color_curve or "",
                "x_scale": spec.x_scale,
                "y_scale": spec.y_scale,
                "point_count": spec.point_count,
                "r_squared": None if spec.trend is None else spec.trend.r_squared,
            }
        )
    return rows


def crossplot_cluster_table_rows(specs: Sequence[CrossplotSpec]) -> list[dict[str, Any]]:
    """Flatten cluster summaries from all specs into UI table rows."""

    rows: list[dict[str, Any]] = []
    for spec in specs:
        for cluster in spec.clusters:
            row = asdict(cluster)
            row["plot"] = spec.name
            rows.append(row)
    return rows


def crossplot_issue_table_rows(issues: Sequence[CrossplotIssue]) -> list[dict[str, Any]]:
    return [asdict(issue) for issue in issues]


def build_petrophysical_crossplot_manifest(result: PetrophysicalCrossplotResult) -> dict[str, Any]:
    """Build reproducible manifest for crossplot workspace output."""

    return {
        "schema": result.schema,
        "generated_at": result.generated_at,
        "storage_key": PETROPHYSICAL_CROSSPLOT_STORAGE_KEY,
        "plan": asdict(result.plan),
        "spec_count": len(result.specs),
        "issue_count": len(result.issues),
        "source_references": list(result.source_references),
        "plots": [
            {
                "name": spec.name,
                "title": spec.title,
                "x_curve": spec.x_curve,
                "y_curve": spec.y_curve,
                "color_curve": spec.color_curve,
                "point_count": spec.point_count,
                "trend": None if spec.trend is None else asdict(spec.trend),
                "cluster_count": len(spec.clusters),
            }
            for spec in result.specs
        ],
    }


def render_petrophysical_crossplot_markdown_report(result: PetrophysicalCrossplotResult) -> str:
    """Render a concise engineering Markdown report for generated crossplots."""

    lines: list[str] = [
        "# Petrophysical Crossplot Workspace Report",
        "",
        f"Generated at: `{result.generated_at}`",
        f"Schema: `{result.schema}`",
        "",
        "## Crossplots",
        "",
        "| Plot | X | Y | Color | Points | R² |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for spec in result.specs:
        r2 = "" if spec.trend is None or spec.trend.r_squared is None else f"{spec.trend.r_squared:.3f}"
        lines.append(f"| {spec.title} | {spec.x_curve} | {spec.y_curve} | {spec.color_curve or ''} | {spec.point_count} | {r2} |")
    if not result.specs:
        lines.append("| No valid crossplots | | | | 0 | |")

    lines.extend(["", "## Cluster Summary", "", "| Plot | Cluster | Samples | Top | Base | Note |", "|---|---:|---:|---:|---:|---|"])
    cluster_rows = crossplot_cluster_table_rows(result.specs)
    if cluster_rows:
        for row in cluster_rows:
            lines.append(
                f"| {row['plot']} | {row['cluster_name']} | {row['sample_count']} | {row['depth_top']} | {row['depth_base']} | {row['note']} |"
            )
    else:
        lines.append("| No clusters | | 0 | | | |")

    if result.issues:
        lines.extend(["", "## Issues", "", "| Severity | Code | Plot | Curve | Message |", "|---|---|---|---|---|"])
        for issue in result.issues:
            lines.append(f"| {issue.severity} | {issue.code} | {issue.plot_name} | {issue.curve_name} | {issue.message} |")

    if result.source_references:
        lines.extend(["", "## Source References", ""])
        for reference in result.source_references:
            lines.append(f"- `{reference}`")

    return "\n".join(lines).strip() + "\n"
