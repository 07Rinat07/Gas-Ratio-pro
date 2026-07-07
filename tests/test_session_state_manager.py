from core.session_state_manager import clear_on_las_change, clear_on_project_change, clear_transient_session_state


def test_clear_transient_session_state_preserves_global_settings() -> None:
    state = {
        "user_settings": {"theme": "dark"},
        "las_dataframe": object(),
        "plot_zoom": {"x": [1, 2]},
        "marker_top": 1000.0,
        "custom_persistent_note": "keep",
    }

    result = clear_transient_session_state(state, reason="manual", project_id="p1", well_id="w1", las_id="l1")

    assert "las_dataframe" not in state
    assert "plot_zoom" not in state
    assert "marker_top" not in state
    assert state["user_settings"] == {"theme": "dark"}
    assert state["custom_persistent_note"] == "keep"
    assert state["active_project_id"] == "p1"
    assert result.active_context == {"project_id": "p1", "well_id": "w1", "las_id": "l1"}
    assert set(result.cleared_keys) == {"las_dataframe", "plot_zoom", "marker_top"}


def test_clear_on_project_change_resets_context_and_las_temp_data() -> None:
    state = {"current_las_data": "old", "calculation_result": 42, "workspace_settings": {}}

    result = clear_on_project_change(state, "project-2")

    assert "current_las_data" not in state
    assert "calculation_result" not in state
    assert state["active_project_id"] == "project-2"
    assert state["active_well_id"] == ""
    assert state["active_las_id"] == ""
    assert result.reason == "project_changed"


def test_clear_on_las_change_keeps_new_context() -> None:
    state = {"ascii_edit_buffer": [1, 2], "validator_issues": ["bad"], "theme": "dark"}

    result = clear_on_las_change(state, "p", "w", "las-new")

    assert "ascii_edit_buffer" not in state
    assert "validator_issues" not in state
    assert state["theme"] == "dark"
    assert state["active_las_id"] == "las-new"
    assert result.reason == "las_changed"
