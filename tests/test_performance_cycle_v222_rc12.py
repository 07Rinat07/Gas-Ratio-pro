from __future__ import annotations

from core.performance_audit import (
    PerformanceBudget,
    build_workspace_performance_gate,
    evaluate_performance,
)
from core.runtime_diagnostics import RuntimeDiagnostics


def test_snapshot_since_excludes_stale_events() -> None:
    diagnostics = RuntimeDiagnostics(max_events=8)
    diagnostics.record(stage="plots", duration_ms=9000.0)
    marker = diagnostics.mark()
    diagnostics.record(stage="plots", duration_ms=25.0, cache_status="hit")
    events = diagnostics.snapshot_since(marker)
    assert len(events) == 1
    assert events[0].duration_ms == 25.0


def test_performance_summary_reports_p95() -> None:
    diagnostics = RuntimeDiagnostics(max_events=16)
    for duration in (10.0, 20.0, 30.0, 40.0, 50.0):
        diagnostics.record(stage="plots", duration_ms=duration)
    budget = PerformanceBudget("plots", warning_ms=100.0, critical_ms=200.0)
    summary = evaluate_performance(diagnostics.snapshot(), budgets=(budget,))[0]
    assert summary.p95_ms == 40.0
    assert summary.maximum_ms == 50.0


def test_workspace_gate_collapses_stage_statuses() -> None:
    diagnostics = RuntimeDiagnostics(max_events=8)
    diagnostics.record(stage="plots", duration_ms=150.0)
    diagnostics.record(stage="frontend", duration_ms=10.0, status="failed")
    summaries = evaluate_performance(
        diagnostics.snapshot(),
        budgets=(
            PerformanceBudget("plots", warning_ms=100.0, critical_ms=200.0),
            PerformanceBudget("frontend", warning_ms=100.0, critical_ms=200.0),
        ),
    )
    gate = build_workspace_performance_gate(summaries)
    assert gate.status == "critical"
    assert gate.warning_stages == ("plots",)
    assert gate.critical_stages == ("frontend",)
