from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")
PLAN = Path("docs/project_plan.md").read_text(encoding="utf-8")


def test_workspace_universal_search_helpers_are_present():
    assert "def _workspace_universal_search_results" in SOURCE
    assert "def _workspace_search_results_html" in SOURCE
    assert "workspace_universal_search_query" in SOURCE
    assert "id='dashboard-workspace-search-results'" in SOURCE


def test_workspace_search_covers_all_required_entities():
    for marker in (
        "проекты",
        "скважины",
        "LAS",
        "кривые",
        "расчеты",
        "отчеты",
        "документация",
        "история",
        "избранное",
    ):
        assert marker in SOURCE


def test_workspace_favorites_are_command_palette_backed():
    assert "def _workspace_favorite_entries" in SOURCE
    assert "COMMAND_PALETTE_FAVORITES_KEY" in SOURCE
    assert "Закрепите команды и объекты через Ctrl+K" in SOURCE
    assert "active_project.name" in SOURCE


def test_workspace_search_stage_is_documented():
    assert "Workspace Search and Favorites" in PLAN
    assert "2.3 Universal Search" in PLAN
    assert "2.4 Favorites" in PLAN
