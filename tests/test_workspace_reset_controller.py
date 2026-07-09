from core.application_state import (
    ACTIVE_LAS_ID_KEY,
    ACTIVE_PROJECT_ID_KEY,
    ACTIVE_WELL_ID_KEY,
    ACTIVE_WORKSPACE_ID_KEY,
)
from core.workspace_reset import (
    WorkspaceResetController,
    normalize_workspace_reset_mode,
    workspace_reset_options,
)


def _state():
    return {
        ACTIVE_PROJECT_ID_KEY: "project-1",
        ACTIVE_WELL_ID_KEY: "well-1",
        ACTIVE_LAS_ID_KEY: "las-1",
        ACTIVE_WORKSPACE_ID_KEY: "workspace-1",
        "theme": "dark",
        "eula_accepted": True,
        "table_interval_rows": [1, 2, 3],
        "plot_preview": object(),
        "report_html_preview": "<html></html>",
        "export_last_path": "/tmp/report.html",
    }


def test_workspace_reset_options_are_ui_ready():
    options = workspace_reset_options()

    assert [option.id for option in options] == [
        "derived",
        "las_context",
        "workspace_context",
        "full_context",
    ]
    assert options[0].requires_confirmation is False
    assert all(option.label for option in options)


def test_normalize_workspace_reset_mode_defaults_to_derived():
    assert normalize_workspace_reset_mode(None) == "derived"
    assert normalize_workspace_reset_mode("zip") == "derived"
    assert normalize_workspace_reset_mode("LAS") == "las_context"
    assert normalize_workspace_reset_mode("project") == "full_context"


def test_preview_lists_transient_keys_without_mutating_state():
    state = _state()
    controller = WorkspaceResetController(state)

    preview = controller.preview("derived")

    assert preview.mode == "derived"
    assert "table_interval_rows" in preview.affected_keys
    assert "plot_preview" in preview.affected_keys
    assert "theme" in preview.preserved_keys
    assert state[ACTIVE_LAS_ID_KEY] == "las-1"


def test_derived_reset_clears_results_and_preserves_active_context():
    cache_calls = []
    state = _state()
    controller = WorkspaceResetController(state, cache_clearer=lambda: cache_calls.append("cleared"))

    result = controller.reset("derived")

    assert result.executed is True
    assert result.cache_cleared is True
    assert cache_calls == ["cleared"]
    assert "table_interval_rows" in result.cleared_keys
    assert "report_html_preview" in result.cleared_keys
    assert ACTIVE_PROJECT_ID_KEY in state
    assert state[ACTIVE_PROJECT_ID_KEY] == "project-1"
    assert state[ACTIVE_WELL_ID_KEY] == "well-1"
    assert state[ACTIVE_LAS_ID_KEY] == "las-1"
    assert state[ACTIVE_WORKSPACE_ID_KEY] == "workspace-1"
    assert state["theme"] == "dark"


def test_las_context_reset_requires_confirmation():
    state = _state()
    controller = WorkspaceResetController(state)

    result = controller.reset("las_context", confirmed=False)

    assert result.executed is False
    assert state[ACTIVE_LAS_ID_KEY] == "las-1"
    event_names = [event.name for event in controller.state_controller.consume_events()]
    assert "workspace.reset_confirmation_required" in event_names


def test_las_context_reset_clears_active_las_after_confirmation():
    state = _state()
    controller = WorkspaceResetController(state)

    preview = controller.preview("las_context")
    result = controller.reset("las_context", confirmed=True)

    assert ACTIVE_LAS_ID_KEY in preview.affected_keys
    assert result.executed is True
    assert state[ACTIVE_PROJECT_ID_KEY] == "project-1"
    assert state[ACTIVE_WELL_ID_KEY] == "well-1"
    assert state[ACTIVE_LAS_ID_KEY] == ""
    assert state[ACTIVE_WORKSPACE_ID_KEY] == "workspace-1"
    assert "plot_preview" in result.cleared_keys


def test_full_context_reset_clears_all_active_context_but_not_user_settings():
    state = _state()
    controller = WorkspaceResetController(state)

    result = controller.reset("full_context", confirmed=True)

    assert result.executed is True
    assert state[ACTIVE_PROJECT_ID_KEY] == ""
    assert state[ACTIVE_WELL_ID_KEY] == ""
    assert state[ACTIVE_LAS_ID_KEY] == ""
    assert state[ACTIVE_WORKSPACE_ID_KEY] == ""
    assert state["theme"] == "dark"
    assert state["eula_accepted"] is True
