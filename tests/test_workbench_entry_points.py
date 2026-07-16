from pathlib import Path

from core.workbench_entry_points import ENTRY_STATE_KEY, WorkbenchEntryPointService
from core.workspace_session import WorkspaceSessionManager
from projects.repository import create_project


def test_project_entry_uses_command_and_existing_navigation(tmp_path: Path):
    projects = tmp_path / "projects"
    sessions = tmp_path / "sessions"
    project = create_project(projects, name="Alpha")
    state = {}
    service = WorkbenchEntryPointService(state, projects_root=projects, sessions_dir=sessions)

    result = service.open_project(project.id)

    assert result.kind == "project"
    assert state["active_project_id"] == project.id
    assert result.active_navigation_id == "nav.dashboard"
    assert result.active_tool_id == "tool.workspace_explorer"
    assert state[ENTRY_STATE_KEY]["project_id"] == project.id
    assert service.project_entries()[0]["action"]["command_id"] == "workbench.entry.open_project"


def test_recent_session_entry_restores_lightweight_state_and_route(tmp_path: Path):
    sessions = tmp_path / "sessions"
    source = {
        "active_project_id": "project-1",
        "active_well_id": "well-1",
        "active_las_id": "las-1",
        "active_workspace_id": "workspace-1",
        "workbench_active_navigation": "nav.las_workspace",
        "current_las_data": object(),
    }
    saved = WorkspaceSessionManager(source, sessions_dir=sessions).save()
    target = {}
    service = WorkbenchEntryPointService(target, projects_root=tmp_path / "projects", sessions_dir=sessions)

    descriptor = service.recent_session_entry()
    result = service.restore_recent_session()

    assert descriptor is not None
    assert descriptor["action"]["command_id"] == "workbench.entry.restore_recent_session"
    assert result.kind == "recent_session"
    assert result.project_id == "project-1"
    assert result.active_navigation_id == "nav.las_workspace"
    assert target["active_las_id"] == "las-1"
    assert "current_las_data" not in target


def test_entry_payload_is_renderer_safe(tmp_path: Path):
    project = create_project(tmp_path / "projects", name="Safe")
    state = {}
    payload = WorkbenchEntryPointService(state, projects_root=tmp_path / "projects", sessions_dir=tmp_path / "sessions").payload()
    text = repr(payload)
    assert project.id in text
    assert "DataFrame" not in text
    assert "WorkbenchEntryPointService" not in text


def test_open_project_records_payload_free_stage_timings(tmp_path) -> None:
    from core.project_open_diagnostics import ProjectOpenDiagnostics
    from core.runtime_service_registry import runtime_service_registry

    projects = tmp_path / "projects"
    sessions = tmp_path / "sessions"
    project = create_project(projects, name="Profiled")
    state: dict[str, object] = {}

    result = WorkbenchEntryPointService(
        state, projects_root=projects, sessions_dir=sessions
    ).open_project(project.id)

    diagnostics = runtime_service_registry(state).get("project_open_diagnostics")
    assert isinstance(diagnostics, ProjectOpenDiagnostics)
    snapshot = diagnostics.snapshot()
    assert result.project_id == project.id
    assert snapshot["event_count"] == 1
    assert snapshot["latest"]["project_id"] == project.id
    assert snapshot["latest"]["total_ms"] >= 0.0
    assert set(snapshot["latest"]) == {
        "project_id", "project_load_ms", "recent_project_ms",
        "workspace_open_ms", "navigation_ms", "total_ms",
        "budget_ms", "status",
    }
