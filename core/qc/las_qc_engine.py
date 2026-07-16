from __future__ import annotations

from typing import Mapping
import math
import pandas as pd

from las_editor.las_creator import DEFAULT_NULL_VALUE
from las_editor.las_quality_control import run_las_quality_control
from .models import CurveQCStatistics, QCFinding, QCReport

_CODE_MAP = {
    "missing_depth_curve": "QC-DEPTH-001",
    "null_depth": "QC-DEPTH-002",
    "empty_depth": "QC-DEPTH-003",
    "duplicate_depth": "QC-DEPTH-004",
    "non_monotonic_depth": "QC-DEPTH-005",
    "missing_depth_interval": "QC-DEPTH-006",
    "irregular_depth_step": "QC-DEPTH-007",
    "missing_values": "QC-NULL-001",
    "negative_value": "QC-RANGE-001",
    "below_expected_range": "QC-RANGE-002",
    "above_expected_range": "QC-RANGE-003",
    "curve_outlier": "QC-RANGE-004",
    "curve_spike": "QC-CURVE-001",
    "flat_line": "QC-CURVE-002",
    "unit_mismatch": "QC-UNITS-002",
}


def _message_key(code: str) -> str:
    return f"qc.finding.{code.lower().replace('-', '_')}"


def _number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _curve_statistics(df: pd.DataFrame, *, null_value: float) -> tuple[CurveQCStatistics, ...]:
    result: list[CurveQCStatistics] = []
    for column in df.columns:
        numeric = pd.to_numeric(df[column], errors="coerce")
        null_mask = numeric.isna() | numeric.eq(null_value)
        valid = numeric[~null_mask]
        result.append(CurveQCStatistics(
            curve=str(column),
            count=int(len(numeric)),
            valid_count=int(valid.count()),
            null_count=int(null_mask.sum()),
            null_fraction=round(float(null_mask.mean()) if len(numeric) else 0.0, 6),
            minimum=_number(valid.min()) if not valid.empty else None,
            maximum=_number(valid.max()) if not valid.empty else None,
            mean=_number(valid.mean()) if not valid.empty else None,
            standard_deviation=_number(valid.std(ddof=0)) if not valid.empty else None,
            unique_count=int(valid.nunique(dropna=True)),
        ))
    return tuple(result)


class LasQCEngine:
    """Stable platform facade over the professional LAS QC implementation."""

    def run(self, df: pd.DataFrame, *, depth_curve: str | None = None, expected_step: float | None = None,
            null_value: float = DEFAULT_NULL_VALUE, units: Mapping[str, str] | None = None) -> QCReport:
        legacy = run_las_quality_control(df, depth_curve=depth_curve, expected_step=expected_step,
                                         null_value=null_value, units=units)
        findings: list[QCFinding] = []
        for issue in legacy.issues:
            stable_code = _CODE_MAP.get(issue.code, f"QC-OTHER-{issue.code.upper().replace('_', '-')}")
            findings.append(QCFinding(
                code=stable_code,
                severity=issue.severity,
                message_key=_message_key(stable_code),
                curve=issue.curve,
                row=issue.row,
                depth=issue.depth,
                value=issue.value,
                details=dict(issue.details or {}),
            ))
        status = "failed" if any(item.severity == "error" for item in findings) else (
            "warning" if findings else "passed"
        )
        return QCReport.create(
            dataset_kind="las",
            row_count=int(len(df)),
            curve_count=int(len(df.columns)),
            depth_curve=legacy.depth_curve,
            status=status,
            findings=tuple(findings),
            curve_statistics=_curve_statistics(df, null_value=null_value),
        )
