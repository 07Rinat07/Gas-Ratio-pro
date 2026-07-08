from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")
PLAN = Path("PROJECT_PROGRESS_NEXT_STEP.md").read_text(encoding="utf-8")


def test_workspace_dashboard_cards_helpers_are_present():
    assert "def _workspace_dashboard_cards_html" in SOURCE
    assert "data-workspace-dashboard-cards" in SOURCE
    assert "workspace-dashboard-card" in SOURCE
    assert "_workspace_dashboard_cards_html(items)" in SOURCE


def test_workspace_project_explorer_shortcuts_helpers_are_present():
    assert "def _workspace_project_explorer_shortcuts_html" in SOURCE
    assert "data-workspace-explorer-shortcuts" in SOURCE
    assert "workspace-explorer-shortcut" in SOURCE
    assert "_workspace_project_explorer_shortcuts_html(items)" in SOURCE


def test_workspace_shortcuts_keep_controller_boundary():
    assert "WorkspaceController" in SOURCE
    assert "UI → Controller → Manager → Service → Repository → Storage" in SOURCE
    assert "The cards are pure HTML generated from manager DTOs" in SOURCE


def test_next_step_tracks_dashboard_cards_and_shortcuts():
    assert "Workspace Dashboard cards" in PLAN
    assert "Project Explorer shortcuts" in PLAN
