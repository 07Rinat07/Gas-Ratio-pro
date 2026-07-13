from __future__ import annotations

from core.performance_audit import PerformanceBudget, evaluate_performance
from core.runtime_diagnostics import RuntimeDiagnostics


def test_performance_audit_reports_ok_warning_and_critical() -> None:
    diagnostics = RuntimeDiagnostics(max_events=8)
    diagnostics.record(stage="plots", duration_ms=20.0, cache_status="hit")
    diagnostics.record(stage="plots", duration_ms=70.0, cache_status="miss")
    budget = PerformanceBudget("plots", warning_ms=50.0, critical_ms=100.0)
    summary = evaluate_performance(diagnostics.snapshot(), budgets=(budget,))[0]
    assert summary.status == "warning"
    assert summary.samples == 2
    assert summary.cache_hits == 1
    assert summary.cache_misses == 1
    assert summary.maximum_ms == 70.0


def test_performance_audit_marks_failed_stage_critical() -> None:
    diagnostics = RuntimeDiagnostics(max_events=4)
    diagnostics.record(stage="plots", duration_ms=1.0, status="failed")
    budget = PerformanceBudget("plots", warning_ms=50.0, critical_ms=100.0)
    summary = evaluate_performance(diagnostics.snapshot(), budgets=(budget,))[0]
    assert summary.status == "critical"
    assert summary.failed == 1


def test_performance_audit_enforces_payload_budget() -> None:
    diagnostics = RuntimeDiagnostics(max_events=4)
    diagnostics.record(stage="frontend", duration_ms=1.0, memory_bytes=1025)
    budget = PerformanceBudget("frontend", warning_ms=50.0, critical_ms=100.0, max_payload_bytes=1024)
    summary = evaluate_performance(diagnostics.snapshot(), budgets=(budget,))[0]
    assert summary.status == "critical"
    assert summary.maximum_payload_bytes == 1025


def test_performance_audit_reports_unmeasured_stage() -> None:
    budget = PerformanceBudget("missing", warning_ms=10.0, critical_ms=20.0)
    summary = evaluate_performance((), budgets=(budget,))[0]
    assert summary.status == "not-measured"
    assert summary.samples == 0
