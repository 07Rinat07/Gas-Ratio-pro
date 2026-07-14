from __future__ import annotations

import pytest

from core.operation_tracing import (
    OperationTraceRegistry,
    current_trace_context,
    trace_context,
    trace_operation,
)
from core.runtime_diagnostics import RuntimeDiagnosticEvent


def test_trace_context_is_scoped_and_restored():
    assert current_trace_context() == {}
    with trace_context(project_id="project-a", route_id="nav.correlation"):
        assert current_trace_context()["project_id"] == "project-a"
    assert current_trace_context() == {}


def test_registry_records_bounded_serializable_events():
    registry = OperationTraceRegistry(max_events=2, slow_threshold_ms=100.0)
    registry.record(operation="one", duration_ms=10)
    registry.record(operation="two", duration_ms=200)
    registry.record(operation="three", duration_ms=20)

    events = registry.snapshot()
    assert [item.operation for item in events] == ["two", "three"]
    assert events[0].slow is True
    assert isinstance(events[0].to_dict()["details"], dict)
    assert registry.summary()["events"] == 2


def test_runtime_events_are_ingested_under_one_execution_id():
    registry = OperationTraceRegistry()
    source = (
        RuntimeDiagnosticEvent("correlation.cache_lookup", 5.0, "success", cache_status="hit"),
        RuntimeDiagnosticEvent("correlation.total", 1200.0, "success", renderer="plotly"),
    )
    events = registry.ingest_runtime_events(source, execution_id="render-1")

    assert {item.execution_id for item in events} == {"render-1"}
    assert events[0].cache_status == "hit"
    assert events[1].slow is True


def test_trace_operation_records_failure_and_reraises(tmp_path, monkeypatch):
    registry = OperationTraceRegistry()
    monkeypatch.setattr("core.operation_tracing.configure_logging", lambda: type("L", (), {"info": lambda *a, **k: None, "warning": lambda *a, **k: None})())

    with pytest.raises(RuntimeError):
        with trace_operation("failure", registry=registry):
            raise RuntimeError("boom")

    assert registry.snapshot()[-1].status == "failed"


def test_diagnostics_center_exposes_trace_summary():
    from core.diagnostics_center import build_diagnostics_center_snapshot
    from core.runtime_service_registry import RuntimeServiceRegistry

    registry = RuntimeServiceRegistry()
    traces = OperationTraceRegistry()
    traces.record(operation="slow-render", duration_ms=1500, category="performance")
    registry.set("operation_trace_registry", traces)
    state = {"runtime::services": registry}

    snapshot = build_diagnostics_center_snapshot(state)
    assert snapshot["traces"]["summary"]["events"] == 1
    assert snapshot["traces"]["summary"]["slow_events"] == 1
