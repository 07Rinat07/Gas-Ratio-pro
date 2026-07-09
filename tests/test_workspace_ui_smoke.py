from __future__ import annotations

from pathlib import Path

from core.application_state import ACTIVE_WORKSPACE_ID_KEY
from projects.repository import create_project
from projects.workspace_controller import WorkspaceController

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")
PLAN = Path("docs/PROJECT_PROGRESS_NEXT_STEP.md").read_text(encoding="utf-8")


def test_project_workspace_panel_exposes_create_open_close_delete_controls():
    """Project Workspace UI must expose the full Workspace lifecycle workflow."""

    assert "def _render_project_workspace_controller_panel" in SOURCE
    assert "Workspace Framework" in SOURCE
    assert "Создать workspace" in SOURCE
    assert "Открыть существующий workspace" in SOURCE
    assert "workspace_open_button_" in SOURCE
    assert "workspace_close_button_" in SOURCE
    assert "workspace_delete_button_" in SOURCE


def test_project_workspace_panel_uses_controller_for_lifecycle_operations():
    """Lifecycle actions in UI must remain behind WorkspaceController."""

    panel_start = SOURCE.index("def _render_project_workspace_controller_panel")
    panel_end = SOURCE.index("def _render_project_workspace_loader")
    panel_source = SOURCE[panel_start:panel_end]

    assert "controller = _workspace_controller()" in panel_source
    assert "controller.create_workspace(" in panel_source
    assert "controller.open_workspace(" in panel_source
    assert "controller.close_workspace()" in panel_source
    assert "controller.delete_workspace(" in panel_source
    assert "st.session_state[" not in panel_source


def test_workspace_ui_smoke_workflow_create_open_delete_through_controller(tmp_path):
    """Smoke-test the same create/open/delete sequence used by the UI panel."""

    project = create_project(tmp_path, name="Workspace Smoke", project_id="workspace-smoke")
    state = {}
    controller = WorkspaceController(state, tmp_path)

    created = controller.create_workspace(
        project.id,
        "Project Workspace",
        kind="general",
        description="Рабочее пространство проекта",
        settings={"created_from": "project_workspace_ui"},
        activate=True,
    )
    assert created.created is True
    assert state[ACTIVE_WORKSPACE_ID_KEY] == created.workspace.id

    opened = controller.open_workspace(project.id, created.workspace.id)
    assert opened.workspace.id == created.workspace.id
    assert controller.list_project_workspaces(project.id)[0].is_active is True

    deleted = controller.delete_workspace(project.id, created.workspace.id)
    assert deleted.delete_result.deleted is True
    assert state[ACTIVE_WORKSPACE_ID_KEY] == ""
    assert controller.list_project_workspaces(project.id) == ()


def test_next_step_tracks_workspace_ui_smoke_tests():
    assert "Workspace Dashboard cards" in PLAN
