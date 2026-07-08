from __future__ import annotations

from pathlib import Path

from projects.repository import create_project
from las_editor.las_workspace_controller import LAS_WORKSPACE_DEFAULT_ID, LasWorkspaceController

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")
PLAN = Path("PROJECT_PROGRESS_NEXT_STEP.md").read_text(encoding="utf-8")


def test_las_workspace_ui_entry_uses_controller_boundary():
    assert "def _render_las_workspace_controller_entry" in SOURCE
    assert "_las_workspace_controller()" in SOURCE
    assert "LasWorkspaceController" in SOURCE
    assert "data-las-workspace-entry='3.0'" in SOURCE
    assert "Открыть LAS Workspace 3.0" in SOURCE

    start = SOURCE.index("def _render_las_workspace_controller_entry")
    end = SOURCE.index("def _render_project_workspace_controller_panel")
    entry_source = SOURCE[start:end]

    assert "controller.ensure_project_las_workspace(" in entry_source
    assert "controller.open_project_las_workspace(" in entry_source
    assert "st.session_state[" not in entry_source


def test_las_workspace_ui_entry_actions_are_renderer_independent(tmp_path):
    project = create_project(tmp_path, name="LAS UI", project_id="las-ui")
    state = {}
    controller = LasWorkspaceController(state, tmp_path)

    prepared = controller.ensure_project_las_workspace(project.id, activate=False)
    assert prepared.workspace.id == LAS_WORKSPACE_DEFAULT_ID
    assert prepared.is_active is False
    assert {action.action_id for action in prepared.home.actions} >= {"create_las", "open_las", "validator"}

    opened = controller.open_project_las_workspace(project.id)
    assert opened.is_active is True
    assert state["active_workspace_id"] == LAS_WORKSPACE_DEFAULT_ID


def test_next_step_tracks_las_workspace_ui_entry():
    assert "LAS Workspace 3.0 UI entry point" in PLAN
