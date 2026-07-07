from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import math
import pandas as pd

from las_editor.ascii_data_editor import find_depth_column
from las_editor.las_creator import DEFAULT_NULL_VALUE, LasCurveSpec, normalize_las_mnemonic, normalize_las_unit


CURVE_IMPORT_STORAGE_KEY = "las_curve_import"
SUPPORTED_CONFLICT_POLICIES: tuple[str, ...] = ("skip", "suffix", "replace")
SUPPORTED_MATCH_POLICIES: tuple[str, ...] = ("exact", "nearest", "interpolate")


@dataclass(frozen=True)
class CurveImportIssue:
    """One validation or merge issue produced by Curve Import."""

    severity: str
    code: str
    message: str
    curve_name: str = ""
    row: int | None = None


@dataclass(frozen=True)
class CurveImportHistoryEntry:
    """Audit trail entry for a non-destructive curve import operation."""

    action: str
    timestamp: str
    details: dict[str, Any]
    reason: str = "manual"
    source: str = "las_editor.curve_importer"


@dataclass(frozen=True)
class CurveImportPlan:
    """Normalized plan describing how incoming tabular curves will be merged."""

    target_depth_column: str
    incoming_depth_column: str
    curves: tuple[str, ...]
    rename_map: dict[str, str]
    units: dict[str, str]
    conflict_policy: str
    match_policy: str
    tolerance: float | None
    null_value: float
    issues: tuple[CurveImportIssue, ...] = ()


@dataclass(frozen=True)
class CurveImportResult:
    """Result of merging imported curves into a LAS working copy."""

    data: pd.DataFrame
    plan: CurveImportPlan
    imported_curves: tuple[str, ...]
    skipped_curves: tuple[str, ...]
    history: tuple[CurveImportHistoryEntry, ...]
    issues: tuple[CurveImportIssue, ...] = ()
    diagnostics: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _copy_attrs(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    target.attrs.update(source.attrs)
    return target


def _history(
    history: Sequence[CurveImportHistoryEntry],
    *,
    action: str,
    details: Mapping[str, Any],
    reason: str = "manual",
    source: str = "las_editor.curve_importer",
) -> tuple[CurveImportHistoryEntry, ...]:
    return tuple(history) + (
        CurveImportHistoryEntry(
            action=action,
            timestamp=_timestamp_utc(),
            details=dict(details),
            reason=reason or "manual",
            source=source or "las_editor.curve_importer",
        ),
    )


def read_curve_import_csv(path: str | Path, **read_csv_kwargs: Any) -> pd.DataFrame:
    """Read a CSV curve table for later safe import.

    The function intentionally only reads the external file and normalizes column
    names. It does not merge values into an existing LAS table and therefore never
    overwrites the source LAS file.
    """

    df = pd.read_csv(path, **read_csv_kwargs)
    return normalize_curve_import_table(df)


def read_curve_import_xlsx(path: str | Path, *, sheet_name: str | int = 0, **read_excel_kwargs: Any) -> pd.DataFrame:
    """Read an Excel curve table for later safe import."""

    df = pd.read_excel(path, sheet_name=sheet_name, **read_excel_kwargs)
    return normalize_curve_import_table(df)


def normalize_curve_import_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return a table with LAS-safe, unique column names.

    Imported CSV/XLSX files often contain spaces, mixed case, duplicated names or
    vendor-specific symbols. This helper converts them to safe LAS mnemonics while
    preserving values and DataFrame attrs.
    """

    result = df.copy()
    used: dict[str, int] = {}
    columns: list[str] = []
    for column in result.columns:
        base = normalize_las_mnemonic(str(column), fallback="CURVE")
        count = used.get(base, 0)
        used[base] = count + 1
        columns.append(base if count == 0 else f"{base}_{count + 1}")
    result.columns = columns
    result.attrs.update(df.attrs)
    return result


def _normalize_policy(value: str, supported: tuple[str, ...], *, policy_name: str) -> str:
    policy = str(value or "").strip().lower()
    if policy not in supported:
        raise ValueError(f"Unsupported {policy_name}: {value!r}. Supported: {supported!r}")
    return policy


def _unique_curve_name(existing: Iterable[str], desired: str) -> str:
    used = {normalize_las_mnemonic(name) for name in existing}
    base = normalize_las_mnemonic(desired)
    if base not in used:
        return base
    index = 2
    while f"{base}_{index}" in used:
        index += 1
    return f"{base}_{index}"


def build_curve_import_plan(
    target_df: pd.DataFrame,
    incoming_df: pd.DataFrame,
    *,
    target_depth_column: str | None = None,
    incoming_depth_column: str | None = None,
    curves: Iterable[str] | None = None,
    rename_map: Mapping[str, str] | None = None,
    units: Mapping[str, str] | None = None,
    conflict_policy: str = "suffix",
    match_policy: str = "interpolate",
    tolerance: float | None = None,
    null_value: float | None = None,
) -> CurveImportPlan:
    """Build a deterministic import plan before changing the working copy."""

    target_depth = target_depth_column or find_depth_column(target_df)
    incoming_depth = incoming_depth_column or find_depth_column(incoming_df)
    conflict = _normalize_policy(conflict_policy, SUPPORTED_CONFLICT_POLICIES, policy_name="conflict_policy")
    match = _normalize_policy(match_policy, SUPPORTED_MATCH_POLICIES, policy_name="match_policy")
    issues: list[CurveImportIssue] = []

    if curves is None:
        selected = [str(column) for column in incoming_df.columns if str(column) != incoming_depth]
    else:
        selected = [normalize_las_mnemonic(str(column)) for column in curves]

    incoming_columns = {normalize_las_mnemonic(str(column)): str(column) for column in incoming_df.columns}
    normalized_selected: list[str] = []
    for curve in selected:
        normalized = normalize_las_mnemonic(curve)
        if normalized == normalize_las_mnemonic(incoming_depth):
            continue
        if normalized not in incoming_columns:
            issues.append(CurveImportIssue("error", "missing_import_curve", f"Incoming curve {curve!r} was not found.", normalized))
            continue
        normalized_selected.append(incoming_columns[normalized])

    if not normalized_selected:
        issues.append(CurveImportIssue("error", "no_curves", "No importable curves were selected."))

    sanitized_rename: dict[str, str] = {}
    for source_name, target_name in dict(rename_map or {}).items():
        source = normalize_las_mnemonic(str(source_name))
        target = normalize_las_mnemonic(str(target_name))
        if source:
            sanitized_rename[source] = target

    sanitized_units = {normalize_las_mnemonic(str(k)): normalize_las_unit(str(v)) for k, v in dict(units or {}).items()}
    return CurveImportPlan(
        target_depth_column=str(target_depth),
        incoming_depth_column=str(incoming_depth),
        curves=tuple(normalized_selected),
        rename_map=sanitized_rename,
        units=sanitized_units,
        conflict_policy=conflict,
        match_policy=match,
        tolerance=None if tolerance is None else float(tolerance),
        null_value=float(DEFAULT_NULL_VALUE if null_value is None else null_value),
        issues=tuple(issues),
    )


def _numeric_series(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce")


def _align_curve_values(
    target_depths: pd.Series,
    incoming_depths: pd.Series,
    incoming_values: pd.Series,
    *,
    match_policy: str,
    tolerance: float | None,
    null_value: float,
) -> tuple[pd.Series, tuple[CurveImportIssue, ...]]:
    issues: list[CurveImportIssue] = []
    target = _numeric_series(target_depths)
    source_depth = _numeric_series(incoming_depths)
    source_values = _numeric_series(incoming_values)
    valid = source_depth.notna() & source_values.notna()
    source = pd.DataFrame({"depth": source_depth[valid], "value": source_values[valid]}).sort_values("depth")
    source = source.drop_duplicates(subset=["depth"], keep="last")

    if source.empty:
        return pd.Series([null_value] * len(target), index=target_depths.index), (
            CurveImportIssue("error", "empty_curve", "Incoming curve has no numeric samples."),
        )

    if match_policy == "exact":
        value_map = dict(zip(source["depth"].tolist(), source["value"].tolist()))
        aligned = target.map(value_map)
        return aligned.fillna(null_value), tuple(issues)

    if match_policy == "nearest":
        rows: list[float] = []
        source_depth_list = source["depth"].tolist()
        source_value_list = source["value"].tolist()
        for depth in target.tolist():
            if pd.isna(depth):
                rows.append(null_value)
                continue
            nearest_index = min(range(len(source_depth_list)), key=lambda idx: abs(source_depth_list[idx] - depth))
            distance = abs(source_depth_list[nearest_index] - depth)
            if tolerance is not None and distance > tolerance:
                rows.append(null_value)
            else:
                rows.append(source_value_list[nearest_index])
        return pd.Series(rows, index=target_depths.index), tuple(issues)

    # interpolate
    interpolated = pd.Series(index=target_depths.index, dtype="float64")
    x = source["depth"].astype(float).tolist()
    y = source["value"].astype(float).tolist()
    if len(x) == 1:
        interpolated.loc[:] = y[0]
    else:
        interpolated.loc[:] = pd.Series(target).interpolate().values
        # numpy is deliberately avoided here; pandas interpolation over a joined
        # depth index keeps dependencies minimal and works well for small/medium LAS tables.
        combined = pd.Series(y, index=x)
        all_depths = sorted(set(x) | {float(v) for v in target.dropna().tolist()})
        combined = combined.reindex(all_depths).interpolate(method="index")
        interpolated = target.map(combined.to_dict())
    return interpolated.fillna(null_value), tuple(issues)


def merge_imported_curves(
    target_df: pd.DataFrame,
    incoming_df: pd.DataFrame,
    plan: CurveImportPlan,
    *,
    history: Sequence[CurveImportHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.curve_importer",
) -> CurveImportResult:
    """Merge imported curves into a LAS working copy without touching the source file."""

    fatal = [issue for issue in plan.issues if issue.severity == "error"]
    if fatal:
        return CurveImportResult(
            data=target_df.copy(),
            plan=plan,
            imported_curves=(),
            skipped_curves=(),
            history=tuple(history),
            issues=plan.issues,
            warnings=("Импорт кривых не выполнен из-за ошибок плана.",),
        )

    result = target_df.copy()
    result = _copy_attrs(target_df, result)
    target_depth = result[plan.target_depth_column]
    incoming_depth = incoming_df[plan.incoming_depth_column]
    imported: list[str] = []
    skipped: list[str] = []
    issues: list[CurveImportIssue] = list(plan.issues)
    units = dict(result.attrs.get("las_units", {}))

    for incoming_curve in plan.curves:
        incoming_name = normalize_las_mnemonic(str(incoming_curve))
        desired = plan.rename_map.get(incoming_name, incoming_name)
        if desired in result.columns and plan.conflict_policy == "skip":
            skipped.append(desired)
            issues.append(CurveImportIssue("warning", "curve_exists_skipped", f"Curve {desired} already exists and was skipped.", desired))
            continue
        if desired in result.columns and plan.conflict_policy == "suffix":
            output_name = _unique_curve_name(result.columns, desired)
        else:
            output_name = desired

        values, align_issues = _align_curve_values(
            target_depth,
            incoming_depth,
            incoming_df[incoming_curve],
            match_policy=plan.match_policy,
            tolerance=plan.tolerance,
            null_value=plan.null_value,
        )
        issues.extend(CurveImportIssue(issue.severity, issue.code, issue.message, output_name, issue.row) for issue in align_issues)
        if any(issue.severity == "error" for issue in align_issues):
            skipped.append(output_name)
            continue

        result[output_name] = values.values
        unit = plan.units.get(incoming_name) or str(incoming_df.attrs.get("las_units", {}).get(incoming_name, ""))
        units[output_name] = normalize_las_unit(unit)
        imported.append(output_name)

    result.attrs["las_units"] = units
    new_history = _history(
        history,
        action="import_curves",
        details={
            "imported_curves": imported,
            "skipped_curves": skipped,
            "conflict_policy": plan.conflict_policy,
            "match_policy": plan.match_policy,
        },
        reason=reason,
        source=source,
    )
    return CurveImportResult(
        data=result,
        plan=plan,
        imported_curves=tuple(imported),
        skipped_curves=tuple(skipped),
        history=new_history,
        issues=tuple(issues),
        diagnostics=(
            f"Импортировано кривых: {len(imported)}.",
            "Изменения внесены только в рабочую копию LAS-таблицы.",
            "Исходный LAS-файл не перезаписывается.",
        ),
        warnings=tuple(issue.message for issue in issues if issue.severity == "warning"),
    )


def import_curve_specs_from_table(df: pd.DataFrame, *, depth_column: str | None = None, units: Mapping[str, str] | None = None) -> tuple[LasCurveSpec, ...]:
    """Build curve specs from an import table for headers or export preview."""

    depth = depth_column or find_depth_column(df)
    unit_map = {normalize_las_mnemonic(str(k)): normalize_las_unit(str(v)) for k, v in dict(units or df.attrs.get("las_units", {})).items()}
    specs: list[LasCurveSpec] = []
    for column in df.columns:
        curve = normalize_las_mnemonic(str(column))
        if column == depth or curve == normalize_las_mnemonic(depth):
            continue
        specs.append(LasCurveSpec(curve, unit_map.get(curve, ""), f"Imported curve {curve}"))
    return tuple(specs)


def curve_import_table_rows(plan: CurveImportPlan) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for curve in plan.curves:
        normalized = normalize_las_mnemonic(curve)
        rows.append({
            "source_curve": normalized,
            "target_curve": plan.rename_map.get(normalized, normalized),
            "unit": plan.units.get(normalized, ""),
            "match_policy": plan.match_policy,
            "conflict_policy": plan.conflict_policy,
        })
    return tuple(rows)


def curve_import_issue_table_rows(issues: Iterable[CurveImportIssue]) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "severity": issue.severity,
            "code": issue.code,
            "curve_name": issue.curve_name,
            "row": "" if issue.row is None else str(issue.row),
            "message": issue.message,
        }
        for issue in issues
    )


def build_curve_import_manifest(result: CurveImportResult) -> dict[str, Any]:
    return {
        "schema": "gas-ratio-pro/las-curve-import-manifest/v1",
        "generated_at": _timestamp_utc(),
        "storage_key": CURVE_IMPORT_STORAGE_KEY,
        "target_depth_column": result.plan.target_depth_column,
        "incoming_depth_column": result.plan.incoming_depth_column,
        "match_policy": result.plan.match_policy,
        "conflict_policy": result.plan.conflict_policy,
        "imported_curves": list(result.imported_curves),
        "skipped_curves": list(result.skipped_curves),
        "issue_count": len(result.issues),
        "issues": [issue.__dict__ for issue in result.issues],
    }
