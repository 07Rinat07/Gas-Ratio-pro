from __future__ import annotations

import ast
from pathlib import Path

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from projects.interpretation_intervals import DEFAULT_INTERPRETATION_ID
from ui.interpretation_interval_panel import resolve_interpretation_id


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_overlay_does_not_construct_interval_manager_directly() -> None:
    source = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "projects.interpretation_interval_manager"
        for alias in node.names
    }
    constructed = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "InterpretationIntervalManager" not in imported_names
    assert "InterpretationIntervalManager" not in constructed
    assert ".interpretation_workspace(" in source
    assert ".list_intervals(" in source


def test_selected_interpretation_scope_is_reused_for_overlay_query() -> None:
    state: dict[str, object] = {}
    assert resolve_interpretation_id(
        state, project_id="project-a", well_id="well-a"
    ) == DEFAULT_INTERPRETATION_ID

    state["manual_interval_interpretation_selector_project-a_well-a"] = "reviewed"
    assert resolve_interpretation_id(
        state, project_id="project-a", well_id="well-a"
    ) == "reviewed"


def test_workspace_list_intervals_is_explicit_application_query(tmp_path: Path) -> None:
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry, {})
    workspace = container.interpretation_workspace(project_id="project-a", root=tmp_path)

    result = workspace.list_intervals(
        state={}, well_id="well-a", interpretation_id=DEFAULT_INTERPRETATION_ID
    )

    assert result == ()
    snapshot = workspace.health_snapshot()
    assert snapshot["manager_scopes"] == 1
