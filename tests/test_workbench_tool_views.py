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


def _item(payload: dict, tool_id: str) -> dict:
    return next(item for item in payload["items"] if item["id"] == tool_id)


def test_las_viewer_provider_exposes_selected_las_context():
    state = {
        "active_project_id": "project_alpha",
        "active_well_id": "well_one",
        "active_las_id": "well_one_main_las",
    }
    controller = build_workbench_controller(state)

    payload = controller.view_model()["tool_views"]
    las_view = _item(payload, "tool.las_viewer")

    assert las_view["status"] == "ready"
    assert las_view["empty_state"] == ""
    assert las_view["content"]["selected_las"]["las_id"] == "well_one_main_las"
    assert las_view["content"]["summary_cards"][2]["title"] == "LAS"
    assert las_view["metadata"]["primary_target"] == "las"


def test_gas_ratio_provider_waits_for_interval_after_las_is_selected():
    state = {"active_las_id": "las_main"}
    controller = build_workbench_controller(state)

    payload = controller.activate_tool("tool.gas_ratio_analysis").view_model()["tool_views"]
    gas_view = payload["active_tool"]

    assert gas_view["id"] == "tool.gas_ratio_analysis"
    assert gas_view["status"] == "waiting_for_interval"
    assert gas_view["content"]["las_id"] == "las_main"
    assert gas_view["content"]["selected_intervals"] == []


def test_gas_ratio_provider_exposes_selected_intervals_without_calculating():
    state = {
        "active_las_id": "las_main",
        "workspace_session_selected_intervals": ["int_top", "int_bottom"],
    }
    controller = build_workbench_controller(state)
    controller.select_object("interval", "int_mid", {"source": "test"})

    payload = controller.activate_tool("tool.gas_ratio_analysis").view_model()["tool_views"]
    gas_view = payload["active_tool"]

    assert gas_view["status"] == "ready"
    assert gas_view["content"]["active_interval"] == "int_mid"
    assert gas_view["content"]["selected_intervals"] == ["int_top", "int_bottom", "int_mid"]
    assert gas_view["metadata"]["interval_count"] == 3


def test_report_preview_provider_exposes_report_summary_and_export_action():
    state = {
        "workspace_session_active_report": "report_engineering",
        "workspace_session_active_plot": "plot_ratio",
        "workspace_session_selected_intervals": ["int_a"],
    }
    controller = build_workbench_controller(state)

    payload = controller.activate_tool("tool.report_preview").view_model()["tool_views"]
    report_view = payload["active_tool"]

    assert report_view["status"] == "ready"
    assert report_view["content"]["report"]["report_id"] == "report_engineering"
    assert report_view["content"]["report"]["plot_id"] == "plot_ratio"
    assert report_view["actions"][-1]["payload"] == {"tool_id": "tool.export"}
    assert report_view["metadata"]["primary_target"] == "report"
