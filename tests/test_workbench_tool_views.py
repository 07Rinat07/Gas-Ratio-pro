from __future__ import annotations

from core.workbench_controller import build_workbench_controller
from core.workbench_context import WorkspaceContext
from core.workbench_tool_views import WorkbenchToolViewService, build_tool_view_model
from core.workbench_tools import WorkbenchToolRegistry


def test_tool_view_service_builds_renderer_ready_tool_payload():
    state = {}
    controller = build_workbench_controller(state)
    context = controller.context()

    payload = WorkbenchToolViewService(state).payload(context)

    assert payload["active_tool_id"] == "tool.workspace_explorer"
    assert payload["active_tool"]["renderer_hint"] == "tree"
    ids = {item["id"] for item in payload["items"]}
    assert "tool.las_viewer" in ids
    assert "tool.gas_ratio_analysis" in ids
    assert payload["open_tool_ids"] == ["tool.workspace_explorer"]


def test_las_viewer_tool_view_exposes_waiting_status_without_las_context():
    state = {}
    tool = WorkbenchToolRegistry(state).get("tool.las_viewer")
    context = WorkspaceContext.from_state(state, build_workbench_controller(state).shell())

    view = build_tool_view_model(
        tool,
        active_tool_id="tool.workspace_explorer",
        open_tool_ids=("tool.workspace_explorer",),
        context=context,
    )

    payload = view.to_dict()
    assert payload["status"] == "waiting_for_las"
    assert payload["renderer_hint"] == "las_curve_viewer"
    assert payload["actions"][0]["payload"] == {"tool_id": "tool.las_viewer"}


def test_controller_view_model_includes_tool_views_after_activation():
    state = {}
    controller = build_workbench_controller(state)

    result = controller.activate_tool("tool.gas_ratio_analysis")
    payload = result.view_model()

    assert payload["tool_views"]["active_tool_id"] == "tool.gas_ratio_analysis"
    assert payload["tool_views"]["active_tool"]["renderer_hint"] == "interpretation_panel"
    assert "tool.gas_ratio_analysis" in payload["tool_views"]["open_tool_ids"]


def test_streamlit_adapter_payload_exposes_tool_view_contract():
    from app.workbench_renderer import build_streamlit_workbench_adapter

    state = {}
    payload = build_streamlit_workbench_adapter(state).payload()

    assert "tool_views" in payload
    assert payload["tool_views"]["active_tool"]["id"] == "tool.workspace_explorer"
