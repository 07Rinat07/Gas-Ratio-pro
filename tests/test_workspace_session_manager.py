from pathlib import Path

from core.application_state import (
    ACTIVE_LAS_ID_KEY,
    ACTIVE_PROJECT_ID_KEY,
    ACTIVE_WELL_ID_KEY,
    ACTIVE_WORKSPACE_ID_KEY,
)
from core.workspace_session import (
    SESSION_ACTIVE_PLOT_KEY,
    SESSION_ACTIVE_REPORT_KEY,
    SESSION_OPENED_FILES_KEY,
    SESSION_RECENT_EXPORTS_KEY,
    SESSION_SELECTED_INTERVALS_KEY,
    SESSION_USER_PROFILE_KEY,
    SESSION_WINDOW_LAYOUT_KEY,
    WorkspaceSession,
    WorkspaceSessionManager,
    WORKSPACE_SESSION_SCHEMA,
    workspace_session_keys,
)


def _state():
    return {
        ACTIVE_PROJECT_ID_KEY: "project-1",
        ACTIVE_WELL_ID_KEY: "well-1",
        ACTIVE_LAS_ID_KEY: "las-1",
        ACTIVE_WORKSPACE_ID_KEY: "workspace-1",
        SESSION_OPENED_FILES_KEY: ["well-1.las", "report.html"],
        SESSION_SELECTED_INTERVALS_KEY: ["2148.2-2150.0", "2151.0-2153.4"],
        SESSION_ACTIVE_REPORT_KEY: "engineering_report",
        SESSION_ACTIVE_PLOT_KEY: "main_tablet",
        SESSION_USER_PROFILE_KEY: "engineering",
        SESSION_RECENT_EXPORTS_KEY: ["out/report.pdf"],
        SESSION_WINDOW_LAYOUT_KEY: {"left": "project", "center": "tablet", "right": "interval_card"},
        "current_las_data": object(),
        "active_dataframe": object(),
    }


def test_workspace_session_capture_ignores_heavy_transient_data():
    session = WorkspaceSession.from_state(_state())

    assert session.schema == WORKSPACE_SESSION_SCHEMA
    assert session.project_id == "project-1"
    assert session.opened_files == ("well-1.las", "report.html")
    assert session.selected_intervals == ("2148.2-2150.0", "2151.0-2153.4")
    payload = session.to_dict()
    assert "current_las_data" not in payload
    assert "active_dataframe" not in payload


def test_workspace_session_roundtrip_to_json(tmp_path: Path):
    state = _state()
    manager = WorkspaceSessionManager(state, sessions_dir=tmp_path)

    saved = manager.save()
    assert saved.executed is True
    assert Path(saved.path).exists()
    assert saved.session.project_id == "project-1"

    restored_session = manager.load(saved.path)
    assert restored_session.project_id == "project-1"
    assert restored_session.window_layout["center"] == "tablet"


def test_workspace_session_restore_overwrites_context_and_ui_state(tmp_path: Path):
    target_state = {
        ACTIVE_PROJECT_ID_KEY: "old-project",
        ACTIVE_WELL_ID_KEY: "old-well",
        ACTIVE_LAS_ID_KEY: "old-las",
        ACTIVE_WORKSPACE_ID_KEY: "old-workspace",
        SESSION_ACTIVE_REPORT_KEY: "old-report",
    }
    session = WorkspaceSession.from_state(_state())
    manager = WorkspaceSessionManager(target_state, sessions_dir=tmp_path)

    result = manager.restore(session)

    assert result.executed is True
    assert target_state[ACTIVE_PROJECT_ID_KEY] == "project-1"
    assert target_state[ACTIVE_WELL_ID_KEY] == "well-1"
    assert target_state[ACTIVE_LAS_ID_KEY] == "las-1"
    assert target_state[ACTIVE_WORKSPACE_ID_KEY] == "workspace-1"
    assert target_state[SESSION_ACTIVE_REPORT_KEY] == "engineering_report"
    assert SESSION_WINDOW_LAYOUT_KEY in result.affected_keys
    assert "workspace.session.restored" in [event.name for event in manager.state_controller.consume_events()]


def test_workspace_session_restore_preserve_policy_keeps_existing_context(tmp_path: Path):
    target_state = {
        ACTIVE_PROJECT_ID_KEY: "already-open",
        SESSION_ACTIVE_REPORT_KEY: "existing-report",
    }
    session = WorkspaceSession.from_state(_state())
    manager = WorkspaceSessionManager(target_state, sessions_dir=tmp_path)

    result = manager.restore(session, conflict_policy="preserve")

    assert result.executed is True
    assert target_state[ACTIVE_PROJECT_ID_KEY] == "already-open"
    assert target_state[SESSION_ACTIVE_REPORT_KEY] == "existing-report"
    assert target_state[ACTIVE_WELL_ID_KEY] == "well-1"
    assert target_state[SESSION_ACTIVE_PLOT_KEY] == "main_tablet"


def test_workspace_session_keys_are_declared_for_ui_boundary():
    keys = workspace_session_keys()

    assert SESSION_OPENED_FILES_KEY in keys
    assert SESSION_RECENT_EXPORTS_KEY in keys
    assert SESSION_WINDOW_LAYOUT_KEY in keys
