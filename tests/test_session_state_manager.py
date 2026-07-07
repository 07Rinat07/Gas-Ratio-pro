from core.session_state_manager import (
    clear_on_las_change,
    clear_on_project_change,
    clear_on_workspace_change,
    clear_transient_session_state,
    ensure_session_context,
    is_transient_session_key,
)


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
    assert result.active_context["project_id"] == "p1"
    assert result.active_context["well_id"] == "w1"
    assert result.active_context["las_id"] == "l1"
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


def test_tables_statistics_and_dashboard_state_are_transient() -> None:
    assert is_transient_session_key("table_curve_statistics")
    assert is_transient_session_key("stats_quality_summary")
    assert is_transient_session_key("statistics_by_curve")
    assert is_transient_session_key("dashboard_recent_las_metrics")
    assert is_transient_session_key("active_validation_table")
    assert is_transient_session_key("project_session_sheets")
    assert not is_transient_session_key("user_settings")


def test_clear_removes_stale_tables_statistics_and_project_sheets() -> None:
    state = {
        "table_curve_statistics": "old-table",
        "stats_quality_summary": {"old": True},
        "dashboard_recent_las_metrics": [1, 2, 3],
        "project_session_sheets": {"old-project": []},
        "project_session_project_id": "project-old",
        "active_validation_table": ["old issue"],
        "theme": "dark",
    }

    result = clear_on_project_change(state, "project-new")

    assert result.reason == "project_changed"
    assert "table_curve_statistics" not in state
    assert "stats_quality_summary" not in state
    assert "dashboard_recent_las_metrics" not in state
    assert "project_session_sheets" not in state
    assert "project_session_project_id" not in state
    assert "active_validation_table" not in state
    assert state["theme"] == "dark"
    assert state["active_project_id"] == "project-new"


def test_workspace_change_clears_workspace_local_tables() -> None:
    state = {
        "active_project_id": "p1",
        "active_well_id": "w1",
        "active_las_id": "l1",
        "active_workspace_id": "las",
        "workspace_local_table": ["old"],
        "report_preview": "old report",
    }

    result = clear_on_workspace_change(state, "p1", "w1", "l1", "plot")

    assert result.reason == "workspace_changed"
    assert "workspace_local_table" not in state
    assert "report_preview" not in state
    assert state["active_workspace_id"] == "plot"


def test_ensure_session_context_does_not_clear_when_context_is_unchanged() -> None:
    state = {
        "active_project_id": "p1",
        "active_well_id": "w1",
        "active_las_id": "l1",
        "active_workspace_id": "las",
        "table_curve_statistics": "keep until context changes",
    }

    result = ensure_session_context(state, project_id="p1", well_id="w1", las_id="l1", workspace_id="las")

    assert result is None
    assert state["table_curve_statistics"] == "keep until context changes"


def test_ensure_session_context_clears_when_las_changes() -> None:
    state = {
        "active_project_id": "p1",
        "active_well_id": "w1",
        "active_las_id": "old-las",
        "active_workspace_id": "las",
        "table_curve_statistics": "old",
        "stats_quality_summary": "old",
    }

    result = ensure_session_context(state, project_id="p1", well_id="w1", las_id="new-las", workspace_id="las")

    assert result is not None
    assert result.reason == "las_changed"
    assert "table_curve_statistics" not in state
    assert "stats_quality_summary" not in state
    assert state["active_las_id"] == "new-las"
