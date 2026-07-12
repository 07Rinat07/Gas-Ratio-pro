from core.workbench_controller import build_workbench_controller
from core.workbench_navigation import WorkbenchNavigationRouter
from core.workbench_tools import WORKBENCH_ACTIVE_TOOL_KEY


def test_single_navigation_model_maps_every_shell_section_to_one_tool():
    router = WorkbenchNavigationRouter()

    payload = router.payload()

    assert [item["navigation_id"] for item in payload] == [
        "nav.dashboard",
        "nav.data",
        "nav.las_workspace",
        "nav.correlation",
        "nav.interpretation",
        "nav.reports",
        "nav.exports",
        "nav.documentation",
    ]
    assert router.by_navigation("nav.las_workspace").tool_id == "tool.las_viewer"
    assert router.by_navigation("nav.las_workspace").primary is True


def test_selecting_las_workspace_activates_existing_las_viewer_tool_contract():
    state = {"active_project_id": "project_alpha", "active_las_id": "las_main"}
    controller = build_workbench_controller(state)

    result = controller.select_navigation("nav.las_workspace")
    payload = result.view_model()

    assert state[WORKBENCH_ACTIVE_TOOL_KEY] == "tool.las_viewer"
    assert payload["interaction"]["active_workspace"] == "las_workspace"
    assert payload["active_module"]["route"]["tool_id"] == "tool.las_viewer"
    assert payload["active_module"]["tool"]["renderer_hint"] == "las_curve_viewer"
    assert payload["active_module"]["tool"]["content"]["selected_las"]["las_id"] == "las_main"


def test_navigation_keeps_ui_payload_free_of_service_and_dataframe_objects():
    controller = build_workbench_controller({"active_las_id": "las_main"})

    payload = controller.select_navigation("nav.las_workspace").view_model()
    text = repr(payload)

    assert "DataFrame" not in text
    assert "LasViewerToolViewProvider object" not in text
    assert payload["active_module"]["route"]["metadata"]["service_contract"] == "LasViewerToolViewProvider"


def test_each_navigation_section_focuses_its_registered_module():
    controller = build_workbench_controller({})
    expected = {
        "nav.dashboard": "tool.workspace_explorer",
        "nav.las_workspace": "tool.las_viewer",
        "nav.interpretation": "tool.gas_ratio_analysis",
        "nav.reports": "tool.report_preview",
        "nav.exports": "tool.export",
        "nav.documentation": "tool.documentation",
    }

    for navigation_id, tool_id in expected.items():
        payload = controller.select_navigation(navigation_id).view_model()
        assert payload["active_module"]["route"]["tool_id"] == tool_id
        assert payload["tool_views"]["active_tool_id"] == tool_id
