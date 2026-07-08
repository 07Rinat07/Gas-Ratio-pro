from core.application_cleanup import ApplicationCleanupController
from core.application_state import ACTIVE_PROJECT_ID_KEY, ACTIVE_WELL_ID_KEY, ACTIVE_LAS_ID_KEY


def test_cleanup_controller_clears_transient_state_and_preserves_context():
    cache_calls = []
    state = {
        ACTIVE_PROJECT_ID_KEY: "project-1",
        ACTIVE_WELL_ID_KEY: "well-1",
        ACTIVE_LAS_ID_KEY: "las-1",
        "theme": "dark",
        "las_editor_table": [1, 2, 3],
        "dashboard_metrics": {"rows": 10},
        "plot_preview": object(),
    }

    controller = ApplicationCleanupController(state, cache_clearer=lambda: cache_calls.append("cleared"))
    result = controller.clear_workspace_state("manual_cleanup", source="test")

    assert result.cache_cleared is True
    assert result.refresh_requested is True
    assert cache_calls == ["cleared"]
    assert state[ACTIVE_PROJECT_ID_KEY] == "project-1"
    assert state[ACTIVE_WELL_ID_KEY] == "well-1"
    assert state[ACTIVE_LAS_ID_KEY] == "las-1"
    assert state["theme"] == "dark"
    assert "las_editor_table" not in state
    assert "dashboard_metrics" not in state
    assert "plot_preview" not in state
    assert "las_editor_table" in result.cleared_keys


def test_cleanup_controller_records_events_and_refresh_request():
    state = {"table_rows": [1]}
    controller = ApplicationCleanupController(state)

    controller.clear_workspace_state("table_cleanup", source="test_source")
    event_names = [event.name for event in controller.state_controller.consume_events()]

    assert "session.cleared" in event_names
    assert "workspace.cleanup_completed" in event_names
    assert "ui.refresh_requested" in event_names
    assert controller.state_controller.consume_refresh_request()["reason"] == "table_cleanup"


def test_cleanup_controller_can_skip_refresh_request():
    state = {"table_rows": [1]}
    controller = ApplicationCleanupController(state)

    result = controller.clear_workspace_state("silent_cleanup", request_refresh=False)

    assert result.refresh_requested is False
    assert controller.state_controller.consume_refresh_request() is None
