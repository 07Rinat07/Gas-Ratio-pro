from core.application_runtime import ApplicationRuntimeController
from core.application_state import (
    ACTIVE_PROJECT_ID_KEY,
    ACTIVE_WELL_ID_KEY,
    ACTIVE_LAS_ID_KEY,
    ACTIVE_WORKSPACE_ID_KEY,
)


def test_runtime_processes_pending_context_transitions_in_order():
    state = {
        ACTIVE_PROJECT_ID_KEY: "old-project",
        ACTIVE_WELL_ID_KEY: "old-well",
        ACTIVE_LAS_ID_KEY: "old-las",
        ACTIVE_WORKSPACE_ID_KEY: "old-workspace",
        "plot_table_rows": [{"x": 1}],
        "diagnostics_table": [{"bad": True}],
    }
    runtime = ApplicationRuntimeController(state)

    runtime.state_controller.request_project_activation("new-project")
    runtime.state_controller.request_well_activation("new-well")
    runtime.state_controller.request_las_activation("new-las")
    runtime.state_controller.request_workspace_activation("new-workspace")

    result = runtime.run_cycle()

    assert result.changed is True
    assert state[ACTIVE_PROJECT_ID_KEY] == "new-project"
    assert state[ACTIVE_WELL_ID_KEY] == "new-well"
    assert state[ACTIVE_LAS_ID_KEY] == "new-las"
    assert state[ACTIVE_WORKSPACE_ID_KEY] == "new-workspace"
    assert "plot_table_rows" not in state
    assert "diagnostics_table" not in state


def test_runtime_centralizes_refresh_request():
    state = {}
    runtime = ApplicationRuntimeController(state)

    runtime.request_refresh("project_deleted", source="test")
    result = runtime.run_cycle()

    assert result.refresh_requested is True
    assert result.refresh_reason == "project_deleted"
    assert runtime.consume_refresh_request() is None
