from __future__ import annotations

from types import SimpleNamespace

import app.streamlit_app as app
from core.build_info import BUILD_VERSION
from core.workbench_navigation import WorkbenchNavigationRouter
from core.workbench_tools import WorkbenchToolRegistry


def test_v202_build_identity() -> None:
    assert BUILD_VERSION == "v204"


def test_existing_workflows_are_reused_by_modern_workbench(monkeypatch) -> None:
    calls: list[str] = []
    project = SimpleNamespace(id="project_test", name="Test")
    monkeypatch.setattr(app, "configure_logging", lambda: object())
    monkeypatch.setattr(app, "_active_project_for_workbench", lambda logger: project)
    monkeypatch.setattr(app, "_render_start_tab", lambda active_project: calls.append("dashboard"))
    monkeypatch.setattr(app, "_render_workbench_las_workspace", lambda logger, active_project: calls.append("las"))
    monkeypatch.setattr(app, "_render_interpretation_graphs_tab", lambda logger, active_project: calls.append("graphs"))
    monkeypatch.setattr(app, "_render_project_exports_panel", lambda active_project, logger: calls.append("exports"))
    monkeypatch.setattr(app, "_render_documentation_tab", lambda: calls.append("docs"))

    expected = {
        "nav.dashboard": "dashboard",
        "nav.las_workspace": "las",
        "nav.interpretation": "graphs",
        "nav.reports": "graphs",
        "nav.exports": "exports",
        "nav.documentation": "docs",
    }
    for route, marker in expected.items():
        calls.clear()
        assert app.render_modern_workbench_workspace(route) is True
        assert calls == [marker]
    assert app.render_modern_workbench_workspace("nav.unknown") is False


def test_las_workspace_exposes_existing_import_editor_and_correlation_modes() -> None:
    assert app.WORKBENCH_LAS_MODES == (
        "Загрузка и анализ",
        "LAS-редактор",
        "LAS-корреляция",
    )


def test_documentation_is_registered_in_single_navigation_and_tool_models() -> None:
    route = WorkbenchNavigationRouter().by_navigation("nav.documentation")
    tools = WorkbenchToolRegistry({})
    assert route.workspace == "documentation"
    assert route.tool_id == "tool.documentation"
    assert tools.get("tool.documentation").factory == "documentation"
