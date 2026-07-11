from __future__ import annotations

from core.command_framework import WorkbenchCommand, WorkbenchCommandRegistry
from core.workbench_runtime_diagnostics import (
    DIAGNOSTIC_BINDING_KEY,
    DIAGNOSTIC_INCIDENTS_KEY,
    diagnostics_enabled,
    diagnostics_snapshot,
    record_binding_state,
    record_runtime_exception,
)


def test_diagnostics_feature_flag() -> None:
    assert diagnostics_enabled({"GAS_RATIO_PRO_DIAGNOSTICS": "1"}) is True
    assert diagnostics_enabled({"GAS_RATIO_PRO_DIAGNOSTICS": "true"}) is True
    assert diagnostics_enabled({}) is False


def test_runtime_incident_is_compact_and_serializable() -> None:
    state: dict[str, object] = {}
    try:
        raise ValueError("broken module")
    except ValueError as exc:
        incident = record_runtime_exception(
            state,
            exc,
            boundary="workspace_renderer",
            operation="nav.las_workspace",
            context={"project": "default"},
            correlation_id="err-test123",
        )
    assert incident["correlation_id"] == "err-test123"
    assert incident["exception_type"] == "ValueError"
    assert state[DIAGNOSTIC_INCIDENTS_KEY][-1]["message"] == "broken module"


def test_binding_state_exposes_route_renderer_provider_and_loaded_status() -> None:
    state: dict[str, object] = {}
    record_binding_state(
        state,
        route_id="nav.las_workspace",
        renderer="render_modern_workbench_workspace",
        provider="existing-production-workflow",
        module_loaded=True,
        project_id="default",
    )
    snapshot = diagnostics_snapshot(state)
    assert snapshot["binding"]["route_id"] == "nav.las_workspace"
    assert snapshot["binding"]["module_loaded"] is True
    assert state[DIAGNOSTIC_BINDING_KEY]["provider"] == "existing-production-workflow"


def test_command_failure_returns_error_id_and_records_incident() -> None:
    state: dict[str, object] = {}
    registry = WorkbenchCommandRegistry(state)

    def fail(_payload: dict[str, object]) -> None:
        raise RuntimeError("handler failed")

    registry.register(WorkbenchCommand("test.fail", "Fail"), fail)
    result = registry.execute("test.fail")
    assert result.executed is False
    assert "Error ID:" in result.message
    assert state[DIAGNOSTIC_INCIDENTS_KEY][-1]["operation"] == "test.fail"
