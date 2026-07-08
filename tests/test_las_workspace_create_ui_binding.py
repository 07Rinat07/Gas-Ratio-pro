from __future__ import annotations

from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")
PLAN = Path("PROJECT_PROGRESS_NEXT_STEP.md").read_text(encoding="utf-8")


def test_new_las_creator_panel_receives_active_project_context():
    assert "def _render_new_las_creator_panel(logger, active_project: ProjectRecord)" in SOURCE
    assert "_render_new_las_creator_panel(logger, active_project)" in SOURCE


def test_new_las_creator_ui_saves_through_las_workspace_controller():
    assert "Сохранить в LAS Workspace" in SOURCE
    assert "create_las_working_copy(" in SOURCE
    assert "new_las_workspace_saved" in SOURCE


def test_las_workspace_plan_tracks_ui_binding_step():
    assert "LAS creation wizard UI" in PLAN
    assert "LasWorkspaceController.create_las_working_copy" in PLAN
