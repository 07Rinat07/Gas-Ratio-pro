from pathlib import Path

from core.workbench_navigation import WorkbenchNavigationRouter


def test_data_workspace_is_a_first_class_route():
    route = WorkbenchNavigationRouter().by_navigation("nav.data")
    assert route.workspace == "data"
    assert route.tool_id == "tool.workspace_explorer"


def test_workbench_menu_and_project_tree_use_real_buttons():
    source = Path("app/workbench_renderer.py").read_text(encoding="utf-8")
    assert '("Data", "nav.data")' in source
    assert 'workbench_menu_' in source
    assert 'workbench_tree_' in source
    assert WorkbenchNavigationRouter().by_navigation("nav.data").workspace == "data"
    assert "<span class='workbench-menu-item" not in source


def test_reports_route_uses_dedicated_workflow():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert '"nav.reports": WorkspaceRoute("nav.reports", "report-workflow", lambda project: _render_workbench_reports' in source
    assert 'Открыть Data Workspace' in source
