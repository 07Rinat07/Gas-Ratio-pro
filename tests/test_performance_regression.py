from __future__ import annotations

import json

from core.performance_regression import (
    PerformanceBaseline,
    RegressionPolicy,
    build_performance_baseline,
    compare_performance_baselines,
)
import scripts.run_performance_regression as cli


def _snapshot(*, durations=(100.0, 120.0), hit_rate=80.0, measured=10, keys=20, failed=False):
    return {
        "runtime": {
            "events": [
                {
                    "stage": "correlation.total",
                    "duration_ms": duration,
                    "status": "failed" if failed and index == 0 else "success",
                }
                for index, duration in enumerate(durations)
            ]
        },
        "cache": {"summary": {"hit_rate": hit_rate, "measured": measured}},
        "session": {"total_keys": keys},
    }


def test_build_baseline_uses_p95_and_primitive_metrics() -> None:
    baseline = build_performance_baseline(_snapshot(durations=(10, 20, 30, 40, 50)))
    assert dict(baseline.stages)["correlation.total"] == 40.0
    assert baseline.cache_hit_rate == 80.0
    assert baseline.session_keys == 20


def test_comparison_detects_duration_cache_session_and_error_regression() -> None:
    baseline = build_performance_baseline(_snapshot(durations=(100,), hit_rate=90, keys=20))
    current = build_performance_baseline(_snapshot(durations=(500,), hit_rate=60, keys=50, failed=True))
    report = compare_performance_baselines(
        baseline,
        current,
        policy=RegressionPolicy(
            max_duration_growth_pct=10,
            max_duration_growth_ms=50,
            max_cache_hit_rate_drop_pct=5,
            max_session_key_growth=5,
        ),
    )
    assert report.passed is False
    assert report.status == "critical"
    assert {item.metric for item in report.findings if item.status == "critical"} == {
        "stage:correlation.total",
        "cache_hit_rate_pct",
        "session_state_keys",
        "failed_runtime_events",
    }


def test_baseline_roundtrip_and_markdown() -> None:
    baseline = build_performance_baseline(_snapshot())
    restored = PerformanceBaseline.from_dict(baseline.to_dict())
    report = compare_performance_baselines(restored, restored)
    assert report.passed is True
    assert "Status:** OK" in report.to_markdown()


def test_cli_returns_nonzero_for_regression_and_writes_reports(tmp_path) -> None:
    baseline_path = tmp_path / "baseline.json"
    current_path = tmp_path / "current.json"
    output_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    baseline_path.write_text(json.dumps(_snapshot(durations=(100,), keys=10)), encoding="utf-8")
    current_path.write_text(json.dumps(_snapshot(durations=(1000,), keys=50)), encoding="utf-8")

    exit_code = cli.main([
        "--baseline", str(baseline_path),
        "--current", str(current_path),
        "--output", str(output_path),
        "--summary-output", str(markdown_path),
        "--max-duration-growth-ms", "100",
        "--max-session-key-growth", "5",
    ])

    assert exit_code == 2
    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is False
    assert "CRITICAL" in markdown_path.read_text(encoding="utf-8")
