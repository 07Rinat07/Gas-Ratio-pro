"""Non-destructive LAS depth repair service.

The module implements the Roadmap v4 depth-repair rule:
when a depth curve is not monotonically increasing, only the row order is
repaired. All measurements (gas, GR, RHOB and other curves) stay attached to
their original depth values. The original DataFrame is never mutated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

import pandas as pd

from las_editor.ascii_data_editor import find_depth_column
from las_editor.las_creator import normalize_las_mnemonic

DEPTH_REPAIR_SCHEMA = "gas-ratio-pro/depth-repair/v1"


@dataclass(frozen=True)
class DepthRepairIssue:
    """Problem detected in a depth column before or after repair."""

    severity: str
    code: str
    message: str
    depth_curve: str = ""
    row_index: int | None = None
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class DepthRepairHistoryEntry:
    """Audit entry for a depth repair operation."""

    action: str
    timestamp: str
    details: Mapping[str, Any]
    source: str = "las_editor.depth_repair"


@dataclass(frozen=True)
class DepthRepairPlan:
    """Validated plan describing whether and how depth order will be repaired."""

    depth_curve: str
    input_rows: int
    input_curves: tuple[str, ...]
    required: bool
    issues: tuple[DepthRepairIssue, ...]
    duplicate_depth_count: int = 0
    null_depth_count: int = 0


@dataclass(frozen=True)
class DepthRepairResult:
    """Result of a non-destructive depth repair operation."""

    data: pd.DataFrame
    plan: DepthRepairPlan
    history: tuple[DepthRepairHistoryEntry, ...]
    issues: tuple[DepthRepairIssue, ...]
    diagnostics: tuple[str, ...]
    manifest: Mapping[str, Any]


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _copy_attrs(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    target.attrs.update(source.attrs)
    return target


def _resolve_depth_curve(df: pd.DataFrame, depth_curve: str | None = None) -> str:
    if depth_curve:
        target = normalize_las_mnemonic(depth_curve)
        for column in df.columns:
            if normalize_las_mnemonic(str(column)) == target:
                return str(column)
        raise ValueError(f"Depth curve {depth_curve!r} was not found.")
    return find_depth_column(df)


def analyze_depth_order(df: pd.DataFrame, *, depth_curve: str | None = None) -> DepthRepairPlan:
    """Inspect depth order and build a repair plan without changing data."""

    resolved_depth = _resolve_depth_curve(df, depth_curve)
    depth = pd.to_numeric(df[resolved_depth], errors="coerce")
    issues: list[DepthRepairIssue] = []

    null_count = int(depth.isna().sum())
    if null_count:
        for row_index in depth[depth.isna()].index[:20]:
            issues.append(
                DepthRepairIssue(
                    "error",
                    "NULL_DEPTH",
                    "Depth value is empty or non-numeric; automatic depth repair cannot safely sort this row.",
                    resolved_depth,
                    int(row_index) if isinstance(row_index, int) else None,
                )
            )

    duplicate_count = int(depth.duplicated(keep=False).sum())
    if duplicate_count:
        issues.append(
            DepthRepairIssue(
                "warning",
                "DUPLICATE_DEPTH",
                "Duplicate depth values were detected; stable sorting will preserve relative order inside duplicated depths.",
                resolved_depth,
                details={"duplicate_depth_count": duplicate_count},
            )
        )

    decreasing_rows: list[int] = []
    previous: float | None = None
    for positional_index, value in enumerate(depth.tolist()):
        if pd.isna(value):
            continue
        current = float(value)
        if previous is not None and current < previous:
            decreasing_rows.append(positional_index)
        previous = current

    if decreasing_rows:
        issues.append(
            DepthRepairIssue(
                "warning",
                "DEPTH_DECREASES",
                "Depth curve is not monotonically increasing; row order should be repaired on a working copy.",
                resolved_depth,
                details={"decreasing_rows": decreasing_rows[:50], "decreasing_count": len(decreasing_rows)},
            )
        )

    return DepthRepairPlan(
        depth_curve=resolved_depth,
        input_rows=len(df),
        input_curves=tuple(str(column) for column in df.columns),
        required=bool(decreasing_rows),
        issues=tuple(issues),
        duplicate_depth_count=duplicate_count,
        null_depth_count=null_count,
    )


def repair_depth_order(
    df: pd.DataFrame,
    *,
    depth_curve: str | None = None,
    fail_on_errors: bool = True,
    reset_index: bool = True,
) -> DepthRepairResult:
    """Repair decreasing depth order by stable-sorting rows on a working copy.

    Curves are never sorted independently. A complete table row is moved as a
    unit, so every measurement remains attached to the same depth value.
    """

    plan = analyze_depth_order(df, depth_curve=depth_curve)
    errors = tuple(issue for issue in plan.issues if issue.severity == "error")
    diagnostics: list[str] = []

    if errors and fail_on_errors:
        working = df.copy()
        history: tuple[DepthRepairHistoryEntry, ...] = ()
        diagnostics.append("Depth repair was not executed because unsafe depth values were found.")
    elif not plan.required:
        working = df.copy()
        history = ()
        diagnostics.append("Depth order is already valid; no repair was required.")
    else:
        before_order = pd.to_numeric(df[plan.depth_curve], errors="coerce").tolist()
        working = df.copy()
        working[plan.depth_curve] = pd.to_numeric(working[plan.depth_curve], errors="coerce")
        working = working.sort_values(plan.depth_curve, ascending=True, kind="mergesort")
        if reset_index:
            working = working.reset_index(drop=True)
        after_order = working[plan.depth_curve].tolist()
        history = (
            DepthRepairHistoryEntry(
                "repair_depth_order",
                _timestamp_utc(),
                {
                    "depth_curve": plan.depth_curve,
                    "method": "stable_row_sort",
                    "input_rows": len(df),
                    "output_rows": len(working),
                    "before_depth_order": before_order,
                    "after_depth_order": after_order,
                    "measurement_policy": "all_curves_move_with_their_original_depth_rows",
                },
            ),
        )
        diagnostics.extend(
            (
                "Depth order was repaired on a working copy only.",
                "All curve values stayed attached to their original depth rows.",
                "Original LAS/DataFrame was not mutated.",
            )
        )

    working = _copy_attrs(df, working)
    manifest = build_depth_repair_manifest(plan, working, history, diagnostics)
    return DepthRepairResult(working, plan, history, plan.issues, tuple(diagnostics), manifest)


def build_depth_repair_manifest(
    plan: DepthRepairPlan,
    output_df: pd.DataFrame,
    history: Sequence[DepthRepairHistoryEntry],
    diagnostics: Sequence[str],
) -> dict[str, Any]:
    """Create a serializable manifest for operation journal and reports."""

    return {
        "schema": DEPTH_REPAIR_SCHEMA,
        "generated_at": _timestamp_utc(),
        "depth_curve": plan.depth_curve,
        "input_rows": plan.input_rows,
        "output_rows": len(output_df),
        "input_curves": list(plan.input_curves),
        "output_curves": [str(column) for column in output_df.columns],
        "required": plan.required,
        "duplicate_depth_count": plan.duplicate_depth_count,
        "null_depth_count": plan.null_depth_count,
        "issues": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
                "depth_curve": issue.depth_curve,
                "row_index": issue.row_index,
                "details": dict(issue.details or {}),
            }
            for issue in plan.issues
        ],
        "history": [
            {
                "action": entry.action,
                "timestamp": entry.timestamp,
                "details": dict(entry.details),
                "source": entry.source,
            }
            for entry in history
        ],
        "diagnostics": list(diagnostics),
    }


def render_depth_repair_report(result: DepthRepairResult) -> str:
    """Render a compact Markdown report for documentation/export."""

    manifest = dict(result.manifest)
    lines = [
        "# Depth Repair Report",
        "",
        f"Schema: `{manifest['schema']}`",
        f"Depth curve: **{manifest['depth_curve']}**",
        f"Input rows: **{manifest['input_rows']}**",
        f"Output rows: **{manifest['output_rows']}**",
        f"Repair required: **{manifest['required']}**",
        "",
        "## Diagnostics",
        "",
    ]
    lines.extend(f"- {item}" for item in manifest["diagnostics"])
    if manifest["issues"]:
        lines.extend(["", "## Issues", ""])
        lines.extend(f"- `{issue['code']}`: {issue['message']}" for issue in manifest["issues"])
    return "\n".join(lines).strip() + "\n"


def create_depth_repair_file_copies(
    original_las_path: str | "Path",
    workspace_dir: str | "Path",
    *,
    backup_dirname: str = "backups",
    working_suffix: str = "_working_depth_repair",
) -> dict[str, Any]:
    """Create protected backup and working LAS file copies before depth repair.

    The original LAS file is copied twice:
    1. immutable backup copy for recovery;
    2. working copy that the application may later rewrite after DataFrame repair.

    The function does not parse or modify LAS content. It only guarantees the
    filesystem safety contract required by the LAS Workspace.
    """

    from pathlib import Path
    import shutil

    original = Path(original_las_path)
    workspace = Path(workspace_dir)
    if not original.exists() or not original.is_file():
        raise FileNotFoundError(f"Original LAS file does not exist: {original}")

    workspace.mkdir(parents=True, exist_ok=True)
    backup_dir = workspace / backup_dirname
    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"{original.stem}_{stamp}_original{original.suffix}"
    working_path = workspace / f"{original.stem}{working_suffix}{original.suffix}"

    shutil.copy2(original, backup_path)
    shutil.copy2(original, working_path)

    return {
        "schema": "gas-ratio-pro/depth-repair-file-safety/v1",
        "original_path": str(original),
        "backup_path": str(backup_path),
        "working_path": str(working_path),
        "original_data_mutated": False,
        "backup_created": True,
        "working_copy_created": True,
        "generated_at": _timestamp_utc(),
    }
