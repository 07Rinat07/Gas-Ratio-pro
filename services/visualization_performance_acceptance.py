"""Large-LAS visualization performance acceptance contracts.

The module provides deterministic benchmark inputs and release gates around the
renderer-neutral visualization pipeline.  It intentionally measures pipeline
construction only; browser rendering and static-export backends are separate
acceptance domains.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sin
from statistics import median
from time import perf_counter
import tracemalloc
from typing import Any, Callable, Mapping, Sequence

from services.visualization_scene_pipeline import VisualizationScenePipeline


@dataclass(frozen=True, slots=True)
class VisualizationPerformanceGate:
    max_cold_seconds: float = 2.5
    max_warm_seconds: float = 0.35
    max_peak_bytes: int = 192 * 1024 * 1024
    min_reduction_ratio: float = 0.80
    require_warm_cache_hit: bool = True


@dataclass(frozen=True, slots=True)
class VisualizationBenchmarkCase:
    name: str
    point_count: int
    curve_count: int = 4
    plot_height: int = 900
    max_points_per_pixel: float = 1.5

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Benchmark case name must not be empty")
        if self.point_count < 2:
            raise ValueError("point_count must be at least 2")
        if self.curve_count < 1:
            raise ValueError("curve_count must be positive")
        if self.plot_height < 100:
            raise ValueError("plot_height must be at least 100")
        if self.max_points_per_pixel <= 0:
            raise ValueError("max_points_per_pixel must be positive")


@dataclass(frozen=True, slots=True)
class VisualizationBenchmarkResult:
    case: VisualizationBenchmarkCase
    cold_seconds: float
    warm_seconds: float
    peak_bytes: int
    source_points: int
    render_points: int
    reduction_ratio: float
    cold_cache_hit: bool
    warm_cache_hit: bool
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.case.name,
            "point_count": self.case.point_count,
            "curve_count": self.case.curve_count,
            "cold_seconds": round(self.cold_seconds, 6),
            "warm_seconds": round(self.warm_seconds, 6),
            "peak_bytes": self.peak_bytes,
            "source_points": self.source_points,
            "render_points": self.render_points,
            "reduction_ratio": round(self.reduction_ratio, 6),
            "cold_cache_hit": self.cold_cache_hit,
            "warm_cache_hit": self.warm_cache_hit,
            "passed": self.passed,
            "issues": list(self.issues),
        }


@dataclass(frozen=True, slots=True)
class VisualizationBenchmarkReport:
    results: tuple[VisualizationBenchmarkResult, ...]

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(result.passed for result in self.results)

    @property
    def issue_count(self) -> int:
        return sum(len(result.issues) for result in self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.performance.acceptance",
            "version": "1.1",
            "passed": self.passed,
            "case_count": len(self.results),
            "issue_count": self.issue_count,
            "results": [result.to_dict() for result in self.results],
        }

    def to_markdown(self) -> str:
        """Render a compact CI/release summary without external dependencies."""
        status = "PASS" if self.passed else "FAIL"
        lines = [
            "## Large-LAS performance gates",
            "",
            f"**Status:** {status}  ",
            f"**Cases:** {len(self.results)}  ",
            f"**Issues:** {self.issue_count}",
            "",
            "| Case | Cold, s | Warm, s | Peak, MiB | Reduction | Warm cache | Result |",
            "|---|---:|---:|---:|---:|:---:|:---:|",
        ]
        for result in self.results:
            result_status = "PASS" if result.passed else "FAIL"
            lines.append(
                "| {name} | {cold:.3f} | {warm:.3f} | {peak:.1f} | {reduction:.1%} | {cache} | {status} |".format(
                    name=result.case.name,
                    cold=result.cold_seconds,
                    warm=result.warm_seconds,
                    peak=result.peak_bytes / (1024 * 1024),
                    reduction=result.reduction_ratio,
                    cache="yes" if result.warm_cache_hit else "no",
                    status=result_status,
                )
            )
        failed = [result for result in self.results if result.issues]
        if failed:
            lines.extend(["", "### Failed gates", ""] )
            for result in failed:
                lines.append(f"- `{result.case.name}`: {', '.join(result.issues)}")
        return "\n".join(lines) + "\n"


def build_large_las_payload(case: VisualizationBenchmarkCase) -> dict[str, Any]:
    """Create a deterministic synthetic LAS-like payload for benchmarking."""
    start_depth = 1000.0
    step = 0.01
    points_by_curve: list[dict[str, Any]] = []
    tracks: list[dict[str, Any]] = []
    for curve_index in range(case.curve_count):
        track_id = f"track.{curve_index}"
        tracks.append({"id": track_id, "title": f"Curve {curve_index + 1}", "width": 1.0})
        points = [
            {
                "depth": start_depth + index * step,
                "value": 75.0 + 45.0 * sin((index / 37.0) + curve_index),
            }
            for index in range(case.point_count)
        ]
        points_by_curve.append(
            {
                "id": f"curve.C{curve_index + 1}",
                "track_id": track_id,
                "mnemonic": f"C{curve_index + 1}",
                "unit": "u",
                "scale_type": "linear",
                "range": {"min": 0.0, "max": 150.0},
                "points": points,
            }
        )

    stop_depth = start_depth + (case.point_count - 1) * step
    return {
        "source_type": "las",
        "source_id": f"benchmark:{case.name}",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": start_depth, "stop": stop_depth, "step": step},
        "tracks": tracks,
        "curves": points_by_curve,
        "overlays": [],
        "viewport": {"width": 1200, "height": case.plot_height},
        "performance_options": {
            "max_points_per_pixel": case.max_points_per_pixel,
            "minimum_render_points": 64,
        },
    }


def evaluate_performance_result(
    *,
    case: VisualizationBenchmarkCase,
    gate: VisualizationPerformanceGate,
    cold_seconds: float,
    warm_seconds: float,
    peak_bytes: int,
    cold_profile: Mapping[str, Any],
    warm_profile: Mapping[str, Any],
) -> VisualizationBenchmarkResult:
    source_points = int(cold_profile.get("source_point_count") or 0)
    render_points = int(cold_profile.get("render_point_count") or 0)
    reduction_ratio = float(cold_profile.get("reduction_ratio") or 0.0)
    cold_cache_hit = bool(cold_profile.get("cache_hit"))
    warm_cache_hit = bool(warm_profile.get("cache_hit"))

    issues: list[str] = []
    if cold_seconds > gate.max_cold_seconds:
        issues.append("cold_pipeline_time_exceeded")
    if warm_seconds > gate.max_warm_seconds:
        issues.append("warm_pipeline_time_exceeded")
    if peak_bytes > gate.max_peak_bytes:
        issues.append("peak_memory_exceeded")
    if reduction_ratio < gate.min_reduction_ratio:
        issues.append("downsampling_reduction_below_gate")
    if gate.require_warm_cache_hit and not warm_cache_hit:
        issues.append("warm_cache_hit_missing")
    if cold_cache_hit:
        issues.append("cold_run_unexpected_cache_hit")
    if source_points <= 0 or render_points <= 0:
        issues.append("invalid_point_metrics")

    return VisualizationBenchmarkResult(
        case=case,
        cold_seconds=max(0.0, float(cold_seconds)),
        warm_seconds=max(0.0, float(warm_seconds)),
        peak_bytes=max(0, int(peak_bytes)),
        source_points=source_points,
        render_points=render_points,
        reduction_ratio=reduction_ratio,
        cold_cache_hit=cold_cache_hit,
        warm_cache_hit=warm_cache_hit,
        issues=tuple(issues),
    )


def run_visualization_benchmark(
    case: VisualizationBenchmarkCase,
    gate: VisualizationPerformanceGate | None = None,
    *,
    pipeline_factory: Callable[[], VisualizationScenePipeline] = VisualizationScenePipeline,
) -> VisualizationBenchmarkResult:
    """Run one cold/warm benchmark against the same pipeline instance."""
    selected_gate = gate or VisualizationPerformanceGate()
    payload = build_large_las_payload(case)
    pipeline = pipeline_factory()

    tracemalloc.start()
    try:
        started = perf_counter()
        cold = pipeline.run(payload).to_dict()
        cold_seconds = perf_counter() - started

        started = perf_counter()
        warm = pipeline.run(payload).to_dict()
        warm_seconds = perf_counter() - started
        _current, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return evaluate_performance_result(
        case=case,
        gate=selected_gate,
        cold_seconds=cold_seconds,
        warm_seconds=warm_seconds,
        peak_bytes=peak_bytes,
        cold_profile=cold.get("performance", {}),
        warm_profile=warm.get("performance", {}),
    )


def run_visualization_benchmark_suite(
    cases: Sequence[VisualizationBenchmarkCase],
    gate: VisualizationPerformanceGate | None = None,
) -> VisualizationBenchmarkReport:
    if not cases:
        raise ValueError("At least one benchmark case is required")
    results = tuple(run_visualization_benchmark(case, gate) for case in cases)
    return VisualizationBenchmarkReport(results=results)


def default_large_las_cases() -> tuple[VisualizationBenchmarkCase, ...]:
    return (
        VisualizationBenchmarkCase("las-25k", point_count=25_000, curve_count=4),
        VisualizationBenchmarkCase("las-100k", point_count=100_000, curve_count=4),
    )


__all__ = [
    "VisualizationBenchmarkCase",
    "VisualizationBenchmarkReport",
    "VisualizationBenchmarkResult",
    "VisualizationPerformanceGate",
    "build_large_las_payload",
    "default_large_las_cases",
    "evaluate_performance_result",
    "run_visualization_benchmark",
    "run_visualization_benchmark_suite",
]
