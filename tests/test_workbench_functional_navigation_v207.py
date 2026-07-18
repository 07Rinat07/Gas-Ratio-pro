from pathlib import Path

from core.workbench_navigation import WorkbenchNavigationRouter


def test_data_workspace_is_a_first_class_route():
    route = WorkbenchNavigationRouter().by_navigation("nav.data")
    assert route.workspace == "data"
    assert route.tool_id == "tool.workspace_explorer"


def test_workbench_menu_and_project_tree_use_real_buttons():
    from app.workbench_renderer import workbench_menu_navigation_ids
    from core.application_state import ApplicationContext
    from core.workbench_context import WorkspaceContext
    from core.workbench_shell import WorkbenchInteractionState
    from core.workbench_ui_providers import WorkbenchUIProviderService

    payload = WorkbenchUIProviderService({}).build(
        WorkspaceContext(ApplicationContext(), WorkbenchInteractionState()), {"tool": {}}
    )
    tree_routes = {item.get("navigation_id") for item in payload.project_tree}

    assert WorkbenchNavigationRouter().by_navigation("nav.data").workspace == "data"
    assert "nav.data" in workbench_menu_navigation_ids()
    assert "nav.data" in tree_routes


def test_reports_route_uses_dedicated_workflow():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert '"nav.reports": WorkspaceRoute("nav.reports", "report-workflow", lambda project: _render_workbench_reports' in source
    assert 'Открыть Data Workspace' in source
