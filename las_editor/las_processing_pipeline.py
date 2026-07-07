from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
import math

import pandas as pd

from las_editor.las_creator import DEFAULT_NULL_VALUE, normalize_las_mnemonic, normalize_las_unit
from las_editor.ascii_data_editor import find_depth_column

LAS_PROCESSING_PIPELINE_SCHEMA = "gas-ratio-pro/las-processing-pipeline/v1"
LAS_PROCESSING_PIPELINE_STORAGE_KEY = "las_processing_pipeline"

SUPPORTED_PROCESSING_OPERATIONS = (
    "moving_average",
    "median_filter",
    "despike",
    "fill_nulls",
    "normalize_minmax",
    "normalize_zscore",
    "clip_range",
    "resample_depth",
)


@dataclass(frozen=True)
class LasProcessingIssue:
    """Validation or execution issue produced by the LAS processing pipeline."""

    severity: str
    code: str
    message: str
    curve: str = ""
    operation: str = ""
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class LasProcessingOperation:
    """One reproducible processing step for LAS curve data."""

    operation: str
    curve: str = ""
    output_curve: str = ""
    parameters: Mapping[str, Any] | None = None
    enabled: bool = True
    description: str = ""


@dataclass(frozen=True)
class LasProcessingHistoryEntry:
    """Audit trail entry for a non-destructive processing operation."""

    action: str
    timestamp: str
    details: dict[str, Any]
    source: str = "las_editor.las_processing_pipeline"


@dataclass(frozen=True)
class LasProcessingPlan:
    """Normalized processing plan that can be previewed or executed."""

    operations: tuple[LasProcessingOperation, ...]
    issues: tuple[LasProcessingIssue, ...]
    input_rows: int
    input_curves: tuple[str, ...]
    depth_curve: str = ""


@dataclass(frozen=True)
class LasProcessingResult:
    """Result of applying a LAS processing pipeline to a working table."""

    data: pd.DataFrame
    plan: LasProcessingPlan
    history: tuple[LasProcessingHistoryEntry, ...]
    issues: tuple[LasProcessingIssue, ...]
    diagnostics: tuple[str, ...]
    preview: Mapping[str, Any]


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _copy_attrs(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    target.attrs.update(source.attrs)
    return target


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _resolve_curve(df: pd.DataFrame, curve: str) -> str:
    target = normalize_las_mnemonic(curve)
    for column in df.columns:
        if normalize_las_mnemonic(str(column)) == target:
            return str(column)
    return ""


def _safe_output_curve(df: pd.DataFrame, source_curve: str, output_curve: str, operation: str) -> str:
    requested = normalize_las_mnemonic(output_curve) if output_curve else ""
    if requested:
        return requested
    base = normalize_las_mnemonic(source_curve)
    suffix = {
        "moving_average": "MA",
        "median_filter": "MED",
        "despike": "DSPK",
        "fill_nulls": "FILL",
        "normalize_minmax": "MM",
        "normalize_zscore": "ZS",
        "clip_range": "CLIP",
    }.get(operation, "PROC")
    candidate = f"{base}_{suffix}"
    if candidate not in {normalize_las_mnemonic(str(c)) for c in df.columns}:
        return candidate
    index = 2
    while f"{candidate}_{index}" in {normalize_las_mnemonic(str(c)) for c in df.columns}:
        index += 1
    return f"{candidate}_{index}"


def operation_table_rows(operations: Sequence[LasProcessingOperation]) -> list[dict[str, Any]]:
    """Convert processing operations to UI-ready rows."""

    rows: list[dict[str, Any]] = []
    for idx, operation in enumerate(operations, start=1):
        rows.append(
            {
                "#": idx,
                "enabled": bool(operation.enabled),
                "operation": operation.operation,
                "curve": operation.curve,
                "output_curve": operation.output_curve,
                "parameters": dict(operation.parameters or {}),
                "description": operation.description,
            }
        )
    return rows


def processing_issue_table_rows(issues: Sequence[LasProcessingIssue]) -> list[dict[str, Any]]:
    """Convert pipeline issues to UI-ready rows."""

    return [
        {
            "severity": issue.severity,
            "code": issue.code,
            "message": issue.message,
            "curve": issue.curve,
            "operation": issue.operation,
            "details": dict(issue.details or {}),
        }
        for issue in issues
    ]


def build_processing_plan(df: pd.DataFrame, operations: Sequence[LasProcessingOperation], *, depth_curve: str | None = None) -> LasProcessingPlan:
    """Validate and normalize a LAS processing pipeline before execution."""

    issues: list[LasProcessingIssue] = []
    normalized_operations: list[LasProcessingOperation] = []
    resolved_depth = _resolve_curve(df, depth_curve) if depth_curve else find_depth_column(df)

    for raw in operations:
        operation_name = str(raw.operation).strip().lower()
        parameters = dict(raw.parameters or {})
        curve = normalize_las_mnemonic(raw.curve) if raw.curve else ""
        output_curve = normalize_las_mnemonic(raw.output_curve) if raw.output_curve else ""

        if operation_name not in SUPPORTED_PROCESSING_OPERATIONS:
            issues.append(LasProcessingIssue("error", "unsupported_operation", f"Unsupported processing operation: {raw.operation}.", curve, operation_name))

        if operation_name == "resample_depth":
            if not resolved_depth:
                issues.append(LasProcessingIssue("error", "missing_depth_curve", "Depth curve is required for resampling.", operation=operation_name))
            if float(parameters.get("step", 0) or 0) <= 0:
                issues.append(LasProcessingIssue("error", "invalid_resample_step", "Resampling step must be greater than zero.", operation=operation_name))
        else:
            if not curve:
                issues.append(LasProcessingIssue("error", "missing_curve", "Processing operation requires a curve name.", operation=operation_name))
            elif not _resolve_curve(df, curve):
                issues.append(LasProcessingIssue("error", "curve_not_found", f"Curve '{curve}' was not found in LAS table.", curve, operation_name))

        if operation_name in {"moving_average", "median_filter"}:
            window = int(parameters.get("window", 0) or 0)
            if window < 2:
                issues.append(LasProcessingIssue("error", "invalid_window", "Filter window must be at least 2 samples.", curve, operation_name))

        if operation_name == "despike":
            threshold = float(parameters.get("threshold", 0) or 0)
            if threshold <= 0:
                issues.append(LasProcessingIssue("error", "invalid_threshold", "Despike threshold must be greater than zero.", curve, operation_name))

        if operation_name == "fill_nulls":
            method = str(parameters.get("method", "linear")).lower()
            if method not in {"linear", "nearest", "constant"}:
                issues.append(LasProcessingIssue("error", "invalid_fill_method", "Fill method must be linear, nearest or constant.", curve, operation_name))

        if operation_name == "clip_range":
            if "min" not in parameters and "max" not in parameters:
                issues.append(LasProcessingIssue("error", "missing_clip_range", "Clip operation requires min and/or max parameter.", curve, operation_name))

        normalized_operations.append(
            LasProcessingOperation(
                operation=operation_name,
                curve=curve,
                output_curve=output_curve,
                parameters=parameters,
                enabled=bool(raw.enabled),
                description=raw.description,
            )
        )

    return LasProcessingPlan(
        operations=tuple(normalized_operations),
        issues=tuple(issues),
        input_rows=len(df),
        input_curves=tuple(str(column) for column in df.columns),
        depth_curve=resolved_depth,
    )


def _moving_average(series: pd.Series, *, window: int) -> pd.Series:
    return _numeric(series).rolling(window=window, min_periods=1, center=True).mean()


def _median_filter(series: pd.Series, *, window: int) -> pd.Series:
    return _numeric(series).rolling(window=window, min_periods=1, center=True).median()


def _despike(series: pd.Series, *, threshold: float, window: int = 3) -> pd.Series:
    numeric = _numeric(series)
    baseline = numeric.rolling(window=max(window, 3), min_periods=1, center=True).median()
    diff = (numeric - baseline).abs()
    return numeric.mask(diff > threshold, baseline)


def _fill_nulls(series: pd.Series, *, method: str, null_value: float, constant: float | None = None) -> pd.Series:
    numeric = _numeric(series).replace(null_value, math.nan)
    if method == "nearest":
        return numeric.interpolate(method="nearest", limit_direction="both")
    if method == "constant":
        return numeric.fillna(null_value if constant is None else constant)
    return numeric.interpolate(method="linear", limit_direction="both")


def _normalize_minmax(series: pd.Series) -> pd.Series:
    numeric = _numeric(series)
    minimum = numeric.min(skipna=True)
    maximum = numeric.max(skipna=True)
    if pd.isna(minimum) or pd.isna(maximum) or maximum == minimum:
        return pd.Series([0.0] * len(series), index=series.index)
    return (numeric - minimum) / (maximum - minimum)


def _normalize_zscore(series: pd.Series) -> pd.Series:
    numeric = _numeric(series)
    mean = numeric.mean(skipna=True)
    std = numeric.std(skipna=True)
    if pd.isna(std) or std == 0:
        return pd.Series([0.0] * len(series), index=series.index)
    return (numeric - mean) / std


def _clip_range(series: pd.Series, *, min_value: float | None = None, max_value: float | None = None) -> pd.Series:
    numeric = _numeric(series)
    return numeric.clip(lower=min_value, upper=max_value)


def _resample_depth(df: pd.DataFrame, *, depth_curve: str, step: float, method: str = "linear") -> pd.DataFrame:
    if not depth_curve:
        return df.copy()
    working = df.copy()
    working[depth_curve] = _numeric(working[depth_curve])
    working = working.dropna(subset=[depth_curve]).sort_values(depth_curve)
    if working.empty:
        return df.copy()

    start = float(working[depth_curve].iloc[0])
    stop = float(working[depth_curve].iloc[-1])
    if step <= 0 or stop < start:
        return working

    count = int(round((stop - start) / step)) + 1
    new_depths = [start + index * step for index in range(count)]
    source = working.set_index(depth_curve)
    target_index = pd.Index(new_depths, name=depth_curve)
    resampled = pd.DataFrame(index=target_index)
    for column in source.columns:
        values = _numeric(source[column])
        combined = values.reindex(values.index.union(target_index)).sort_index()
        if method == "nearest":
            interpolated = combined.interpolate(method="nearest", limit_direction="both")
        else:
            interpolated = combined.interpolate(method="index", limit_direction="both")
        resampled[column] = interpolated.reindex(target_index).to_numpy()
    resampled.insert(0, depth_curve, target_index.to_numpy())
    return resampled.reset_index(drop=True)


def apply_processing_operation(
    df: pd.DataFrame,
    operation: LasProcessingOperation,
    *,
    depth_curve: str = "",
    null_value: float = DEFAULT_NULL_VALUE,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply one processing operation to a copy of the working DataFrame."""

    if not operation.enabled:
        return df.copy(), {"skipped": True}

    working = df.copy()
    op = operation.operation
    params = dict(operation.parameters or {})

    if op == "resample_depth":
        before_rows = len(working)
        resampled = _resample_depth(working, depth_curve=depth_curve, step=float(params.get("step", 0)), method=str(params.get("method", "linear")))
        return _copy_attrs(working, resampled), {"before_rows": before_rows, "after_rows": len(resampled), "depth_curve": depth_curve}

    source = _resolve_curve(working, operation.curve)
    if not source:
        return working, {"skipped": True, "reason": "curve_not_found", "curve": operation.curve}
    output = _safe_output_curve(working, source, operation.output_curve, op)

    if op == "moving_average":
        result = _moving_average(working[source], window=int(params.get("window", 3)))
    elif op == "median_filter":
        result = _median_filter(working[source], window=int(params.get("window", 3)))
    elif op == "despike":
        result = _despike(working[source], threshold=float(params.get("threshold", 1.0)), window=int(params.get("window", 3)))
    elif op == "fill_nulls":
        result = _fill_nulls(working[source], method=str(params.get("method", "linear")).lower(), null_value=null_value, constant=params.get("constant"))
    elif op == "normalize_minmax":
        result = _normalize_minmax(working[source])
    elif op == "normalize_zscore":
        result = _normalize_zscore(working[source])
    elif op == "clip_range":
        result = _clip_range(working[source], min_value=params.get("min"), max_value=params.get("max"))
    else:
        return working, {"skipped": True, "reason": "unsupported_operation", "operation": op}

    before = _numeric(working[source])
    working[output] = result
    changed = int((before.fillna(null_value) != _numeric(result).fillna(null_value)).sum())
    return working, {"source_curve": source, "output_curve": output, "changed_samples": changed, "parameters": params}


def preview_processing_pipeline(
    df: pd.DataFrame,
    operations: Sequence[LasProcessingOperation],
    *,
    depth_curve: str | None = None,
    null_value: float = DEFAULT_NULL_VALUE,
    sample_rows: int = 5,
) -> dict[str, Any]:
    """Build a lightweight before/after preview for the processing pipeline."""

    result = apply_processing_pipeline(df, operations, depth_curve=depth_curve, null_value=null_value, fail_on_errors=False)
    return {
        "input_shape": tuple(df.shape),
        "output_shape": tuple(result.data.shape),
        "operations": operation_table_rows(result.plan.operations),
        "issues": processing_issue_table_rows(result.issues),
        "before": df.head(sample_rows).to_dict(orient="records"),
        "after": result.data.head(sample_rows).to_dict(orient="records"),
        "diagnostics": list(result.diagnostics),
    }


def apply_processing_pipeline(
    df: pd.DataFrame,
    operations: Sequence[LasProcessingOperation],
    *,
    depth_curve: str | None = None,
    null_value: float = DEFAULT_NULL_VALUE,
    fail_on_errors: bool = True,
) -> LasProcessingResult:
    """Apply a reproducible non-destructive LAS processing pipeline."""

    plan = build_processing_plan(df, operations, depth_curve=depth_curve)
    errors = tuple(issue for issue in plan.issues if issue.severity == "error")
    if errors and fail_on_errors:
        return LasProcessingResult(
            data=df.copy(),
            plan=plan,
            history=(),
            issues=plan.issues,
            diagnostics=("Pipeline was not executed because validation errors were found.",),
            preview={"executed": False},
        )

    working = df.copy()
    history: list[LasProcessingHistoryEntry] = []
    diagnostics: list[str] = []
    runtime_issues: list[LasProcessingIssue] = []

    for operation in plan.operations:
        if not operation.enabled:
            diagnostics.append(f"Skipped disabled operation: {operation.operation}.")
            continue
        before_shape = tuple(working.shape)
        working, details = apply_processing_operation(working, operation, depth_curve=plan.depth_curve, null_value=null_value)
        after_shape = tuple(working.shape)
        details = dict(details)
        details.update({"operation": operation.operation, "before_shape": before_shape, "after_shape": after_shape})
        history.append(LasProcessingHistoryEntry("apply_processing_operation", _timestamp_utc(), details))
        diagnostics.append(f"Applied {operation.operation}: {before_shape} -> {after_shape}.")
        if details.get("skipped"):
            runtime_issues.append(LasProcessingIssue("warning", "operation_skipped", "Processing operation was skipped.", operation.curve, operation.operation, details))

    preview = {
        "input_shape": tuple(df.shape),
        "output_shape": tuple(working.shape),
        "operation_count": len([op for op in plan.operations if op.enabled]),
    }
    return LasProcessingResult(
        data=_copy_attrs(df, working),
        plan=plan,
        history=tuple(history),
        issues=tuple(plan.issues) + tuple(runtime_issues),
        diagnostics=tuple(diagnostics),
        preview=preview,
    )


def build_processing_manifest(result: LasProcessingResult) -> dict[str, Any]:
    """Create a serializable manifest for a processing run."""

    return {
        "schema": LAS_PROCESSING_PIPELINE_SCHEMA,
        "generated_at": _timestamp_utc(),
        "input_rows": result.plan.input_rows,
        "input_curves": list(result.plan.input_curves),
        "output_rows": len(result.data),
        "output_curves": [str(column) for column in result.data.columns],
        "depth_curve": result.plan.depth_curve,
        "operations": operation_table_rows(result.plan.operations),
        "issues": processing_issue_table_rows(result.issues),
        "diagnostics": list(result.diagnostics),
        "history": [
            {"action": entry.action, "timestamp": entry.timestamp, "details": entry.details, "source": entry.source}
            for entry in result.history
        ],
        "preview": dict(result.preview),
    }


def render_processing_report(result: LasProcessingResult) -> str:
    """Render a compact Markdown processing report."""

    manifest = build_processing_manifest(result)
    lines = [
        "# LAS Processing Pipeline Report",
        "",
        f"Schema: `{manifest['schema']}`",
        f"Generated: `{manifest['generated_at']}`",
        f"Input rows: **{manifest['input_rows']}**",
        f"Output rows: **{manifest['output_rows']}**",
        f"Operations: **{len(manifest['operations'])}**",
        "",
        "## Operations",
        "",
    ]
    for row in manifest["operations"]:
        lines.append(f"- `{row['operation']}` curve=`{row['curve']}` output=`{row['output_curve']}` params=`{row['parameters']}`")
    lines.extend(["", "## Issues", ""])
    if not manifest["issues"]:
        lines.append("No processing issues detected.")
    else:
        for issue in manifest["issues"]:
            lines.append(f"- **{issue['severity']}** `{issue['code']}` {issue['message']}")
    return "\n".join(lines).strip() + "\n"
