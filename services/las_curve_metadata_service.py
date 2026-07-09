"""Lightweight LAS curve metadata summaries for Workbench views.

This service reads project LAS data through the existing LAS manager boundary and
returns small JSON-friendly summaries.  It deliberately avoids exposing full LAS
dataframes, curve samples or engineering calculations to renderer state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from services.las_manager_service import LasManagerService

DEPTH_MNEMONICS = {"DEPT", "DEPTH", "MD", "TVD"}
DEFAULT_CURVE_LIMIT = 24


@dataclass(frozen=True, slots=True)
class LasCurveSummary:
    """Small renderer-safe summary for one LAS curve."""

    mnemonic: str
    unit: str = ""
    non_null_count: int = 0
    numeric: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mnemonic": self.mnemonic,
            "unit": self.unit,
            "non_null_count": self.non_null_count,
            "numeric": self.numeric,
        }


@dataclass(frozen=True, slots=True)
class LasCurveMetadataSummary:
    """Renderer-safe LAS metadata payload used by the Workbench LAS Viewer."""

    project_id: str
    las_id: str
    well_id: str = ""
    well_name: str = ""
    original_file_name: str = ""
    version_label: str = ""
    curve_count: int = 0
    row_count: int = 0
    depth_curve: str = ""
    depth_range: dict[str, float | None] = field(default_factory=dict)
    curves: tuple[LasCurveSummary, ...] = field(default_factory=tuple)
    quality_flags: tuple[str, ...] = field(default_factory=tuple)
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "las_id": self.las_id,
            "well_id": self.well_id,
            "well_name": self.well_name,
            "original_file_name": self.original_file_name,
            "version_label": self.version_label,
            "curve_count": self.curve_count,
            "row_count": self.row_count,
            "depth_curve": self.depth_curve,
            "depth_range": dict(self.depth_range),
            "curves": [curve.to_dict() for curve in self.curves],
            "quality_flags": list(self.quality_flags),
            "truncated": self.truncated,
        }


def _clean_column_name(value: Any) -> str:
    return str(value or "").strip()


def _curve_units(frame: pd.DataFrame) -> dict[str, str]:
    return {str(key).strip(): str(value).strip() for key, value in dict(frame.attrs.get("las_units", {}) or {}).items()}


def _select_depth_curve(frame: pd.DataFrame) -> str:
    columns = [_clean_column_name(column) for column in frame.columns]
    for column in columns:
        if column.upper() in DEPTH_MNEMONICS:
            return column
    for column in columns:
        series = pd.to_numeric(frame[column], errors="coerce")
        if series.notna().any():
            return column
    return ""


def _depth_range(frame: pd.DataFrame, depth_curve: str) -> dict[str, float | None]:
    if not depth_curve or depth_curve not in frame.columns:
        return {"start": None, "stop": None, "step": None}
    series = pd.to_numeric(frame[depth_curve], errors="coerce").dropna()
    if series.empty:
        return {"start": None, "stop": None, "step": None}
    diffs = series.diff().dropna()
    non_zero_diffs = diffs[diffs != 0]
    step = float(non_zero_diffs.median()) if not non_zero_diffs.empty else None
    return {"start": float(series.min()), "stop": float(series.max()), "step": step}


def _quality_flags(frame: pd.DataFrame, depth_curve: str) -> tuple[str, ...]:
    flags: list[str] = []
    if frame.empty:
        flags.append("empty_las_data")
    if not depth_curve:
        flags.append("missing_depth_curve")
    elif depth_curve in frame.columns:
        depth = pd.to_numeric(frame[depth_curve], errors="coerce")
        if depth.isna().any():
            flags.append("depth_contains_nulls")
        if depth.dropna().duplicated().any():
            flags.append("depth_duplicates")
        if len(depth.dropna()) >= 2 and not depth.dropna().is_monotonic_increasing:
            flags.append("depth_not_monotonic")
    numeric_columns = 0
    sparse_columns = 0
    for column in frame.columns:
        series = pd.to_numeric(frame[column], errors="coerce")
        if series.notna().any():
            numeric_columns += 1
        if len(series) and (series.notna().sum() / len(series)) < 0.5:
            sparse_columns += 1
    if numeric_columns == 0:
        flags.append("no_numeric_curves")
    if sparse_columns:
        flags.append("sparse_curves_present")
    return tuple(dict.fromkeys(flags))


class LasCurveMetadataService:
    """Build lightweight curve metadata summaries from project LAS storage."""

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT, manager: LasManagerService | None = None) -> None:
        self.root = Path(root)
        self.manager = manager or LasManagerService(self.root)

    def summarize(self, project_id: str, las_id: str, *, curve_limit: int = DEFAULT_CURVE_LIMIT) -> LasCurveMetadataSummary:
        clean_project_id = safe_project_id(project_id)
        clean_las_id = str(las_id or "").strip()
        if not clean_las_id:
            raise ValueError("LAS id must not be empty.")

        records = {record.id: record for record in self.manager.list_files(clean_project_id, include_archived=True)}
        if clean_las_id not in records:
            raise FileNotFoundError(f"Project LAS file not found: {clean_las_id}")
        record = records[clean_las_id]
        frame = self.manager.read_dataframe(clean_project_id, clean_las_id)
        units = _curve_units(frame)
        depth_curve = _select_depth_curve(frame)
        curves: list[LasCurveSummary] = []
        for column in list(frame.columns)[: max(1, int(curve_limit))]:
            mnemonic = _clean_column_name(column)
            series = pd.to_numeric(frame[column], errors="coerce")
            curves.append(
                LasCurveSummary(
                    mnemonic=mnemonic,
                    unit=units.get(mnemonic, ""),
                    non_null_count=int(frame[column].notna().sum()),
                    numeric=bool(series.notna().any()),
                )
            )
        return LasCurveMetadataSummary(
            project_id=clean_project_id,
            las_id=clean_las_id,
            well_id=record.well_id,
            well_name=record.name,
            original_file_name=record.original_file_name,
            version_label=record.version_label,
            curve_count=len(frame.columns),
            row_count=len(frame.index),
            depth_curve=depth_curve,
            depth_range=_depth_range(frame, depth_curve),
            curves=tuple(curves),
            quality_flags=_quality_flags(frame, depth_curve),
            truncated=len(frame.columns) > len(curves),
        )
