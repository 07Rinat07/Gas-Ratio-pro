from __future__ import annotations

from services.visualization_performance_acceptance import (
    VisualizationBenchmarkCase,
    VisualizationPerformanceGate,
    build_large_las_payload,
    evaluate_performance_result,
    run_visualization_benchmark,
)


def test_large_las_payload_is_deterministic_and_complete() -> None:
    case = VisualizationBenchmarkCase("test", point_count=1000, curve_count=3)
    first = build_large_las_payload(case)
    second = build_large_las_payload(case)

    assert first == second
    assert len(first["curves"]) == 3
    assert all(len(curve["points"]) == 1000 for curve in first["curves"])
    assert first["performance_options"]["max_points_per_pixel"] == 1.5


def test_acceptance_evaluator_reports_each_failed_gate() -> None:
    case = VisualizationBenchmarkCase("failed", point_count=100)
    result = evaluate_performance_result(
        case=case,
        gate=VisualizationPerformanceGate(
            max_cold_seconds=1.0,
            max_warm_seconds=0.1,
            max_peak_bytes=100,
            min_reduction_ratio=0.9,
        ),
        cold_seconds=2.0,
        warm_seconds=0.2,
        peak_bytes=101,
        cold_profile={
            "source_point_count": 400,
            "render_point_count": 200,
            "reduction_ratio": 0.5,
            "cache_hit": False,
        },
        warm_profile={"cache_hit": False},
    )

    assert result.passed is False
    assert set(result.issues) == {
        "cold_pipeline_time_exceeded",
        "warm_pipeline_time_exceeded",
        "peak_memory_exceeded",
        "downsampling_reduction_below_gate",
        "warm_cache_hit_missing",
    }


def test_small_real_benchmark_uses_cache_and_reduces_geometry() -> None:
    result = run_visualization_benchmark(
        VisualizationBenchmarkCase("smoke", point_count=3000, curve_count=2, plot_height=400),
        VisualizationPerformanceGate(
            max_cold_seconds=10.0,
            max_warm_seconds=5.0,
            max_peak_bytes=256 * 1024 * 1024,
            min_reduction_ratio=0.20,
        ),
    )

    assert result.passed is True
    assert result.cold_cache_hit is False
    assert result.warm_cache_hit is True
    assert result.source_points == 6000
    assert 0 < result.render_points < result.source_points
    assert result.to_dict()["passed"] is True
