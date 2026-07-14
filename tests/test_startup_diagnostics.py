from core.startup_diagnostics import StartupDiagnostics, StartupTimer
from core.diagnostics_center import build_diagnostics_center_snapshot
from core.runtime_service_registry import runtime_service_registry


def test_startup_diagnostics_records_bounded_primitive_cycles():
    diagnostics = StartupDiagnostics(max_cycles=2, budgets_ms={"total": 10.0})
    diagnostics.record_cycle({"page_config": 1.0, "total": 9.0}, route_id="nav.dashboard", project_id="p1")
    diagnostics.record_cycle({"page_config": 2.0, "total": 11.0}, route_id="nav.data", project_id="p1")
    diagnostics.record_cycle({"page_config": 3.0, "total": 8.0}, route_id="nav.correlation", project_id="p1")

    snapshot = diagnostics.snapshot(limit=10)
    assert snapshot["cycle_count"] == 2
    assert snapshot["cycles"][0]["route_id"] == "nav.data"
    assert snapshot["latest"]["route_id"] == "nav.correlation"
    assert snapshot["latest"]["status"] == "ok"


def test_startup_timer_returns_stage_and_total_durations():
    timer = StartupTimer()
    assert timer.mark("page_config") >= 0.0
    result = timer.finish()
    assert result["page_config"] >= 0.0
    assert result["total"] >= result["page_config"]


def test_diagnostics_center_includes_startup_snapshot():
    state = {}
    registry = runtime_service_registry(state)
    service = registry.ensure("startup_diagnostics", StartupDiagnostics, expected_type=StartupDiagnostics, scope="session")
    service.record_cycle({"workbench_render": 10.0, "total": 20.0}, route_id="nav.dashboard", project_id="default")

    snapshot = build_diagnostics_center_snapshot(state)
    assert snapshot["startup"]["latest"]["route_id"] == "nav.dashboard"
    assert snapshot["startup"]["latest"]["total_ms"] == 20.0
