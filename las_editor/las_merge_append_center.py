"""Safe LAS Merge / Append Center.

The module provides non-destructive table-level operations used by the LAS
Workspace when a user needs to combine LAS files or insert GIS/log curves from
one LAS into another working copy. The original LAS DataFrames are never
mutated; every operation returns a new working copy plus an audit manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from las_editor.ascii_data_editor import find_depth_column
from las_editor.curve_importer import build_curve_import_plan, merge_imported_curves
from las_editor.las_creator import DEFAULT_NULL_VALUE, normalize_las_mnemonic

LAS_MERGE_APPEND_SCHEMA = "gas-ratio-pro/las-merge-append-center/v1"
LAS_MERGE_APPEND_STORAGE_KEY = "las_merge_append_center"


@dataclass(frozen=True)
class LasMergeAppendIssue:
    """Validation message produced by Merge / Append Center."""

    severity: str
    code: str
    message: str
    curve_name: str = ""


@dataclass(frozen=True)
class LasMergeAppendHistoryEntry:
    """Operation journal entry for safe merge/append actions."""

    action: str
    timestamp: str
    details: dict[str, Any]
    reason: str = "manual"
    source: str = "las_editor.las_merge_append_center"


@dataclass(frozen=True)
class LasMergeAppendResult:
    """Result of a non-destructive LAS merge/append operation."""

    data: pd.DataFrame
    operation: str
    history: tuple[LasMergeAppendHistoryEntry, ...]
    issues: tuple[LasMergeAppendIssue, ...] = ()
    diagnostics: tuple[str, ...] = ()
    manifest: dict[str, Any] | None = None


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _copy_attrs(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    target.attrs.update(source.attrs)
    return target


def _history_entry(action: str, details: Mapping[str, Any], *, reason: str = "manual") -> LasMergeAppendHistoryEntry:
    return LasMergeAppendHistoryEntry(
        action=action,
        timestamp=_timestamp_utc(),
        details=dict(details),
        reason=reason or "manual",
    )


def _normalize_selected_curves(df: pd.DataFrame, curves: Iterable[str] | None, depth_column: str) -> tuple[str, ...]:
    if curves is None:
        return tuple(str(column) for column in df.columns if str(column) != depth_column)

    lookup = {normalize_las_mnemonic(str(column)): str(column) for column in df.columns}
    result: list[str] = []
    for curve in curves:
        normalized = normalize_las_mnemonic(str(curve))
        if normalized == normalize_las_mnemonic(depth_column):
            continue
        if normalized not in lookup:
            raise ValueError(f"Curve is missing in source LAS data: {curve!r}")
        result.append(lookup[normalized])
    return tuple(dict.fromkeys(result))


def build_las_merge_append_manifest(
    *,
    operation: str,
    input_rows: Mapping[str, int],
    output_rows: int,
    output_curves: Sequence[str],
    history: Sequence[LasMergeAppendHistoryEntry],
    issues: Sequence[LasMergeAppendIssue],
    diagnostics: Sequence[str],
) -> dict[str, Any]:
    """Build a serializable manifest for Operation Journal and UI."""

    return {
        "schema": LAS_MERGE_APPEND_SCHEMA,
        "operation": operation,
        "input_rows": dict(input_rows),
        "output_rows": int(output_rows),
        "output_curves": [str(curve) for curve in output_curves],
        "issues": [issue.__dict__ for issue in issues],
        "diagnostics": list(diagnostics),
        "history": [entry.__dict__ for entry in history],
        "safety": {
            "original_data_mutated": False,
            "working_copy_created": True,
            "source_policy": "read_only",
        },
    }


def append_las_depth_intervals(
    base_df: pd.DataFrame,
    incoming_df: pd.DataFrame,
    *,
    base_depth_column: str | None = None,
    incoming_depth_column: str | None = None,
    selected_curves: Iterable[str] | None = None,
    duplicate_depth_policy: str = "keep_last",
    null_value: float = DEFAULT_NULL_VALUE,
    reason: str = "manual",
) -> LasMergeAppendResult:
    """Append another LAS table by depth into a working copy.

    The operation is intended for splicing/sращивание LAS intervals. It creates a
    union of curves, appends incoming rows, sorts by depth, and resolves duplicate
    depth rows according to ``duplicate_depth_policy``. Neither input DataFrame is
    modified.
    """

    base_depth = base_depth_column or find_depth_column(base_df)
    incoming_depth = incoming_depth_column or find_depth_column(incoming_df)
    if not base_depth:
        raise ValueError("Base LAS data must contain a depth column.")
    if not incoming_depth:
        raise ValueError("Incoming LAS data must contain a depth column.")
    if duplicate_depth_policy not in {"keep_first", "keep_last", "keep_all", "error"}:
        raise ValueError("duplicate_depth_policy must be keep_first, keep_last, keep_all or error.")

    incoming_curves = _normalize_selected_curves(incoming_df, selected_curves, incoming_depth)
    base = base_df.copy(deep=True)
    incoming = incoming_df[[incoming_depth, *incoming_curves]].copy(deep=True)
    if incoming_depth != base_depth:
        incoming = incoming.rename(columns={incoming_depth: base_depth})

    all_columns = list(dict.fromkeys([*base.columns, *incoming.columns]))
    base = base.reindex(columns=all_columns, fill_value=null_value)
    incoming = incoming.reindex(columns=all_columns, fill_value=null_value)
    combined = pd.concat([base, incoming], ignore_index=True)
    combined[base_depth] = pd.to_numeric(combined[base_depth], errors="coerce")

    issues: list[LasMergeAppendIssue] = []
    diagnostics: list[str] = [
        "LAS intervals were appended into a working copy only.",
        "Original base and incoming LAS data were not mutated.",
    ]

    duplicated = combined[base_depth].duplicated(keep=False)
    duplicate_count = int(duplicated.sum())
    if duplicate_count:
        issues.append(
            LasMergeAppendIssue(
                "warning" if duplicate_depth_policy != "error" else "error",
                "DUPLICATE_DEPTH",
                f"Duplicate depth rows detected during LAS append: {duplicate_count}.",
            )
        )
        if duplicate_depth_policy == "error":
            result = _copy_attrs(base_df, base_df.copy(deep=True))
            history = (_history_entry("append_las_depth_intervals_blocked", {"duplicate_depth_count": duplicate_count}, reason=reason),)
            diagnostics.append("Append was blocked because duplicate depth policy is error.")
            manifest = build_las_merge_append_manifest(
                operation="append_las_depth_intervals",
                input_rows={"base": len(base_df), "incoming": len(incoming_df)},
                output_rows=len(result),
                output_curves=tuple(result.columns),
                history=history,
                issues=issues,
                diagnostics=diagnostics,
            )
            return LasMergeAppendResult(result, "append_las_depth_intervals", history, tuple(issues), tuple(diagnostics), manifest)

    combined = combined.sort_values(base_depth, kind="mergesort", na_position="last").reset_index(drop=True)
    if duplicate_depth_policy in {"keep_first", "keep_last"}:
        keep = "first" if duplicate_depth_policy == "keep_first" else "last"
        combined = combined.drop_duplicates(subset=[base_depth], keep=keep).reset_index(drop=True)
        diagnostics.append(f"Duplicate depth policy applied: {duplicate_depth_policy}.")

    history = (
        _history_entry(
            "append_las_depth_intervals",
            {
                "base_depth_column": base_depth,
                "incoming_depth_column": incoming_depth,
                "selected_curves": list(incoming_curves),
                "duplicate_depth_policy": duplicate_depth_policy,
                "base_rows": len(base_df),
                "incoming_rows": len(incoming_df),
                "output_rows": len(combined),
            },
            reason=reason,
        ),
    )
    combined = _copy_attrs(base_df, combined)
    manifest = build_las_merge_append_manifest(
        operation="append_las_depth_intervals",
        input_rows={"base": len(base_df), "incoming": len(incoming_df)},
        output_rows=len(combined),
        output_curves=tuple(combined.columns),
        history=history,
        issues=issues,
        diagnostics=diagnostics,
    )
    return LasMergeAppendResult(combined, "append_las_depth_intervals", history, tuple(issues), tuple(diagnostics), manifest)


def insert_las_curves_from_las(
    target_df: pd.DataFrame,
    source_df: pd.DataFrame,
    *,
    target_depth_column: str | None = None,
    source_depth_column: str | None = None,
    curves: Iterable[str] | None = None,
    rename_map: Mapping[str, str] | None = None,
    conflict_policy: str = "suffix",
    match_policy: str = "interpolate",
    tolerance: float | None = None,
    null_value: float = DEFAULT_NULL_VALUE,
    reason: str = "manual",
) -> LasMergeAppendResult:
    """Insert GIS/log curves from one LAS table into another working copy.

    This is a LAS-to-LAS wrapper over the generic curve importer. Depth matching
    can be exact, nearest or interpolated. The target and source DataFrames remain
    unchanged.
    """

    target_depth = target_depth_column or find_depth_column(target_df)
    source_depth = source_depth_column or find_depth_column(source_df)
    if not target_depth:
        raise ValueError("Target LAS data must contain a depth column.")
    if not source_depth:
        raise ValueError("Source LAS data must contain a depth column.")

    selected = _normalize_selected_curves(source_df, curves, source_depth)
    incoming = source_df[[source_depth, *selected]].copy(deep=True)
    plan = build_curve_import_plan(
        target_df,
        incoming,
        target_depth_column=target_depth,
        incoming_depth_column=source_depth,
        curves=selected,
        rename_map=rename_map,
        conflict_policy=conflict_policy,
        match_policy=match_policy,
        tolerance=tolerance,
        null_value=null_value,
    )
    imported = merge_imported_curves(
        target_df,
        incoming,
        plan,
        reason=reason,
        source="las_editor.las_merge_append_center",
    )
    issues = tuple(LasMergeAppendIssue(issue.severity, issue.code, issue.message, issue.curve_name) for issue in imported.issues)
    diagnostics = tuple(imported.diagnostics) + (
        "GIS/log curves were inserted from source LAS into a working copy only.",
        "Original target and source LAS data were not mutated.",
    )
    history = (
        _history_entry(
            "insert_las_curves_from_las",
            {
                "target_depth_column": target_depth,
                "source_depth_column": source_depth,
                "curves": list(selected),
                "imported_curves": list(imported.imported_curves),
                "skipped_curves": list(imported.skipped_curves),
                "conflict_policy": conflict_policy,
                "match_policy": match_policy,
            },
            reason=reason,
        ),
    )
    result = _copy_attrs(target_df, imported.data.copy(deep=True))
    manifest = build_las_merge_append_manifest(
        operation="insert_las_curves_from_las",
        input_rows={"target": len(target_df), "source": len(source_df)},
        output_rows=len(result),
        output_curves=tuple(result.columns),
        history=history,
        issues=issues,
        diagnostics=diagnostics,
    )
    return LasMergeAppendResult(result, "insert_las_curves_from_las", history, issues, diagnostics, manifest)
