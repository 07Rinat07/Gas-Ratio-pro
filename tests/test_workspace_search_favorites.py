from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")
PLAN = Path("docs/archive/legacy_plans/project_plan_v5_legacy.md").read_text(encoding="utf-8")


def test_workspace_universal_search_helpers_are_present():
    assert "def _workspace_universal_search_results" in SOURCE
    assert "def _workspace_search_results_html" in SOURCE
    assert "workspace_universal_search_query" in SOURCE
    assert "id='dashboard-workspace-search-results'" in SOURCE


def test_workspace_search_covers_all_required_entities():
    from core.ui_behavior_contracts import WORKBENCH_SEARCH_BEHAVIOR

    assert set(WORKBENCH_SEARCH_BEHAVIOR.entity_kinds) == {
        "projects", "wells", "las", "curves", "calculations",
        "reports", "documentation", "history", "favorites",
    }


def test_workspace_favorites_are_command_palette_backed():
    from app import streamlit_app as app
    from core.ui_behavior_contracts import WORKBENCH_SEARCH_BEHAVIOR

    contract = app._workspace_search_behavior_contract()
    assert contract is WORKBENCH_SEARCH_BEHAVIOR
    assert contract.favorites_backend == "command_palette"
    assert "Ctrl+K" in contract.empty_hint


def test_workspace_search_stage_is_documented():
    assert "Workspace Search and Favorites" in PLAN
    assert "2.3 Universal Search" in PLAN
    assert "2.4 Favorites" in PLAN
