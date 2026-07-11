"""LAS Viewer curve validation and normalization.

This module is the renderer-neutral boundary that classifies malformed curve
payloads before they enter the viewer layout/render pipeline.  It deliberately
keeps recoverable data, records null intervals, and normalizes units without
retaining a DataFrame.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping, Sequence

from las_editor.curve_units import CURVE_UNIT_LABELS, normalize_curve_unit


@dataclass(frozen=True, slots=True)
class LasViewerCurveDiagnostic:
    code: str
    severity: str
    curve_id: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "curve_id": self.curve_id,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class LasViewerCurveValidationResult:
    curves: tuple[Mapping[str, Any], ...]
    excluded_curves: tuple[str, ...]
    diagnostics: tuple[LasViewerCurveDiagnostic, ...]
    null_intervals: Mapping[str, tuple[Mapping[str, float], ...]]

    @property
    def has_errors(self) -> bool:
        return any(item.severity == "error" for item in self.diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.curve.validation",
            "version": "1.0",
            "curves": [dict(item) for item in self.curves],
            "excluded_curves": list(self.excluded_curves),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "null_intervals": {
                key: [dict(interval) for interval in value]
                for key, value in self.null_intervals.items()
            },
            "has_errors": self.has_errors,
            "renderer_neutral": True,
            "raw_dataframe_included": False,
        }


def _point_parts(point: Any) -> tuple[Any, Any] | None:
    if isinstance(point, Mapping):
        return point.get("depth"), point.get("value")
    if isinstance(point, (list, tuple)) and len(point) >= 2:
        return point[0], point[1]
    return None


def _finite(value: Any) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _null_intervals(points: Sequence[Any]) -> tuple[dict[str, float], ...]:
    intervals: list[dict[str, float]] = []
    start: float | None = None
    stop: float | None = None
    count = 0
    for point in points:
        parts = _point_parts(point)
        if parts is None or not _finite(parts[0]):
            continue
        depth = float(parts[0])
        is_null = not _finite(parts[1])
        if is_null:
            if start is None:
                start = depth
            stop = depth
            count += 1
        elif start is not None and stop is not None:
            intervals.append({"start": start, "stop": stop, "sample_count": float(count)})
            start = stop = None
            count = 0
    if start is not None and stop is not None:
        intervals.append({"start": start, "stop": stop, "sample_count": float(count)})
    return tuple(intervals)


class LasViewerCurveValidator:
    """Normalize curve points/units and classify recoverable viewer errors."""

    def validate(self, curves: Sequence[Mapping[str, Any]]) -> LasViewerCurveValidationResult:
        normalized_curves: list[dict[str, Any]] = []
        excluded: list[str] = []
        diagnostics: list[LasViewerCurveDiagnostic] = []
        null_intervals: dict[str, tuple[Mapping[str, float], ...]] = {}

        for source in curves:
            curve = dict(source)
            curve_id = str(curve.get("mnemonic") or curve.get("id") or "").strip()
            if not curve_id:
                curve_id = "<unnamed>"
                excluded.append(curve_id)
                diagnostics.append(LasViewerCurveDiagnostic(
                    "curve_missing_identifier", "error", curve_id,
                    "Curve has no mnemonic or identifier and was excluded.",
                ))
                continue

            points = list(curve.get("points") or ())
            if not points:
                excluded.append(curve_id)
                diagnostics.append(LasViewerCurveDiagnostic(
                    "curve_empty", "warning", curve_id,
                    "Curve contains no samples and was excluded.",
                ))
                continue

            intervals = _null_intervals(points)
            if intervals:
                null_intervals[curve_id] = intervals

            valid_points: list[Any] = []
            invalid_depth_count = 0
            null_value_count = 0
            for point in points:
                parts = _point_parts(point)
                if parts is None or not _finite(parts[0]):
                    invalid_depth_count += 1
                    continue
                if not _finite(parts[1]):
                    null_value_count += 1
                    continue
                valid_points.append(point)

            if not valid_points:
                excluded.append(curve_id)
                diagnostics.append(LasViewerCurveDiagnostic(
                    "curve_all_null", "warning", curve_id,
                    "Curve has no finite values and was excluded.",
                    {"sample_count": len(points), "null_value_count": null_value_count},
                ))
                continue

            if invalid_depth_count:
                diagnostics.append(LasViewerCurveDiagnostic(
                    "curve_invalid_depth_samples", "warning", curve_id,
                    "Samples with invalid depth were removed.",
                    {"count": invalid_depth_count},
                ))
            if null_value_count:
                diagnostics.append(LasViewerCurveDiagnostic(
                    "curve_partial_null", "warning", curve_id,
                    "Null samples were omitted while preserving valid intervals.",
                    {"count": null_value_count, "interval_count": len(intervals)},
                ))

            raw_unit = str(curve.get("unit") or "").strip()
            normalized_unit = normalize_curve_unit(raw_unit)
            if normalized_unit not in CURVE_UNIT_LABELS:
                diagnostics.append(LasViewerCurveDiagnostic(
                    "curve_unit_unsupported", "warning", curve_id,
                    "Unsupported curve unit was normalized to unknown.",
                    {"source_unit": raw_unit, "normalized_unit": normalized_unit},
                ))
                normalized_unit = "unknown"
            elif normalized_unit == "unknown" and raw_unit:
                diagnostics.append(LasViewerCurveDiagnostic(
                    "curve_unit_unknown", "warning", curve_id,
                    "Curve unit is unknown.", {"source_unit": raw_unit},
                ))

            curve["mnemonic"] = curve_id
            curve["unit"] = normalized_unit
            curve["points"] = valid_points
            quality = dict(curve.get("quality") or {})
            quality.update({
                "source_sample_count": len(points),
                "renderable_sample_count": len(valid_points),
                "null_sample_count": null_value_count,
                "invalid_depth_sample_count": invalid_depth_count,
                "null_intervals": [dict(item) for item in intervals],
                "unit_status": "unknown" if normalized_unit == "unknown" else "supported",
            })
            curve["quality"] = quality
            normalized_curves.append(curve)

        return LasViewerCurveValidationResult(
            curves=tuple(normalized_curves),
            excluded_curves=tuple(excluded),
            diagnostics=tuple(diagnostics),
            null_intervals=null_intervals,
        )
