"""Curve quality preparation for renderer-neutral visualization primitives.

This module separates curve segmentation and viewport clipping from concrete
renderers.  Missing values, invalid logarithmic values and excessive depth gaps
produce independent segments instead of accidental bridge lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite, log10
from statistics import median
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class CurveSegment:
    id: str
    points: tuple[dict[str, float], ...] = field(default_factory=tuple)
    source_point_count: int = 0
    clipped_point_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "points": [dict(point) for point in self.points],
            "source_point_count": self.source_point_count,
            "clipped_point_count": self.clipped_point_count,
        }


@dataclass(frozen=True, slots=True)
class CurveQualityResult:
    segments: tuple[CurveSegment, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.segments) and not any(issue.startswith("curve_quality_error:") for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "segments": [segment.to_dict() for segment in self.segments],
            "issues": list(self.issues),
            "metadata": dict(self.metadata),
            "ok": self.ok,
            "renderer_neutral": True,
        }


class VisualizationCurveQualityEngine:
    """Convert raw curve points into clipped, gap-aware pixel segments."""

    def build(
        self,
        *,
        layer_id: str,
        points: Sequence[Mapping[str, Any]],
        axis_min: float,
        axis_max: float,
        scale: str,
        depth_start: float,
        depth_stop: float,
        plot_x: float,
        plot_y: float,
        plot_width: float,
        plot_height: float,
        depth_gap_factor: float = 6.0,
        max_points_per_pixel: float = 1.5,
        minimum_render_points: int = 64,
    ) -> CurveQualityResult:
        issues: list[str] = []
        if depth_stop <= depth_start or axis_max <= axis_min or plot_width <= 0 or plot_height <= 0:
            return CurveQualityResult(issues=(f"curve_quality_error:invalid_domain:{layer_id}",))

        valid_depths = [
            depth for depth in (_finite(point.get("depth")) for point in points) if depth is not None
        ]
        spacings = [b - a for a, b in zip(valid_depths, valid_depths[1:]) if b > a]
        typical_spacing = median(spacings) if spacings else 0.0
        max_gap = typical_spacing * max(depth_gap_factor, 1.0) if typical_spacing > 0 else float("inf")

        raw_segments: list[list[dict[str, float]]] = []
        current: list[dict[str, float]] = []
        previous_depth: float | None = None
        invalid_point_count = 0
        gap_break_count = 0
        clipped_point_count = 0

        def flush() -> None:
            nonlocal current
            if len(current) >= 2:
                raw_segments.append(current)
            current = []

        for point in points:
            depth = _finite(point.get("depth"))
            value = _finite(point.get("value"))
            normalized = None if value is None else _normalize(value, axis_min, axis_max, scale)
            if depth is None or normalized is None:
                invalid_point_count += 1
                flush()
                previous_depth = None
                continue
            if previous_depth is not None and (depth <= previous_depth or depth - previous_depth > max_gap):
                gap_break_count += 1
                flush()
            previous_depth = depth
            if depth < depth_start or depth > depth_stop:
                clipped_point_count += 1
                flush()
                continue
            x = plot_x + 8.0 + normalized * max(plot_width - 16.0, 1.0)
            y = plot_y + ((depth - depth_start) / (depth_stop - depth_start)) * plot_height
            current.append({"x": x, "y": y, "depth": depth, "value": value})
        flush()

        point_budget = max(
            2,
            int(max(float(minimum_render_points), plot_height * max(float(max_points_per_pixel), 0.1))),
        )
        sampled_segments: list[CurveSegment] = []
        downsampled_point_count = 0
        for index, segment in enumerate(raw_segments):
            sampled = _downsample_extrema(segment, point_budget)
            downsampled_point_count += max(0, len(segment) - len(sampled))
            sampled_segments.append(
                CurveSegment(
                    id=f"{layer_id}.segment.{index}",
                    points=tuple({"x": point["x"], "y": point["y"]} for point in sampled),
                    source_point_count=len(segment),
                    clipped_point_count=0,
                )
            )
        segments = tuple(sampled_segments)
        if not segments:
            issues.append(f"curve_quality_error:no_renderable_segments:{layer_id}")
        if invalid_point_count:
            issues.append(f"curve_quality_invalid_points:{layer_id}:{invalid_point_count}")
        if gap_break_count:
            issues.append(f"curve_quality_gap_breaks:{layer_id}:{gap_break_count}")

        return CurveQualityResult(
            segments=segments,
            issues=tuple(issues),
            metadata={
                "source_point_count": len(points),
                "segment_count": len(segments),
                "invalid_point_count": invalid_point_count,
                "gap_break_count": gap_break_count,
                "clipped_point_count": clipped_point_count,
                "typical_depth_spacing": typical_spacing,
                "maximum_continuous_depth_gap": max_gap if isfinite(max_gap) else None,
                "scale": scale,
                "sampling_strategy": "viewport_extrema",
                "point_budget": point_budget,
                "downsampled_point_count": downsampled_point_count,
                "render_point_count": sum(len(segment.points) for segment in segments),
                "max_points_per_pixel": float(max_points_per_pixel),
            },
        )


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _normalize(value: float, minimum: float, maximum: float, scale: str) -> float | None:
    if scale.lower() == "log":
        if value <= 0 or minimum <= 0 or maximum <= 0:
            return None
        low, high = log10(minimum), log10(maximum)
        if high <= low:
            return None
        normalized = (log10(value) - low) / (high - low)
    else:
        normalized = (value - minimum) / (maximum - minimum)
    return min(1.0, max(0.0, normalized))


def _downsample_extrema(points: Sequence[Mapping[str, float]], budget: int) -> list[dict[str, float]]:
    """Reduce a monotonic-depth segment while preserving local extrema and endpoints."""
    prepared = [dict(point) for point in points]
    if len(prepared) <= budget or budget < 4:
        return prepared

    interior = prepared[1:-1]
    bucket_count = max(1, (budget - 2) // 2)
    bucket_size = max(1, (len(interior) + bucket_count - 1) // bucket_count)
    selected: list[dict[str, float]] = [prepared[0]]
    for start in range(0, len(interior), bucket_size):
        bucket = interior[start:start + bucket_size]
        if not bucket:
            continue
        low = min(bucket, key=lambda point: (point["x"], point["y"]))
        high = max(bucket, key=lambda point: (point["x"], -point["y"]))
        ordered = sorted((low, high), key=lambda point: point["y"])
        for point in ordered:
            if point != selected[-1]:
                selected.append(point)
    if prepared[-1] != selected[-1]:
        selected.append(prepared[-1])
    if len(selected) > budget:
        stride = (len(selected) - 1) / (budget - 1)
        selected = [selected[round(index * stride)] for index in range(budget)]
        selected[0] = prepared[0]
        selected[-1] = prepared[-1]
    return selected
