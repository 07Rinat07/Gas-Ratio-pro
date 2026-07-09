from __future__ import annotations

from core.workbench_controller import build_workbench_controller
from core.workbench_tool_actions import (
    WORKBENCH_LAST_TOOL_ACTION_KEY,
    WORKBENCH_TOOL_ACTION_HISTORY_KEY,
)


def _item(payload: dict, tool_id: str) -> dict:
    return next(item for item in payload["items"] if item["id"] == tool_id)


def test_las_view_action_is_exposed_and_dispatched_through_command_framework():
    state = {"active_las_id": "las_main"}
    controller = build_workbench_controller(state)

    view = _item(controller.view_model()["tool_views"], "tool.las_viewer")
    action_ids = {action["id"] for action in view["actions"]}
    assert "action.open_las" in action_ids

    result = controller.dispatch_renderer_action("action.open_las", {"las_id": "las_main"})

    assert result.command_result.executed is True
    assert result.command_result.result["accepted"] is True
    assert state[WORKBENCH_LAST_TOOL_ACTION_KEY]["action_id"] == "workbench.tool.open_las"
    assert state[WORKBENCH_TOOL_ACTION_HISTORY_KEY][-1]["payload"]["las_id"] == "las_main"


def test_gas_ratio_action_requires_las_and_interval_context():
    state = {"active_las_id": "las_main"}
    controller = build_workbench_controller(state)

    rejected = controller.dispatch_renderer_action("action.run_gas_ratio_analysis", {})
    assert rejected.command_result.result["accepted"] is False

    controller.select_object("interval", "int_main")
    accepted = controller.dispatch_renderer_action("action.run_gas_ratio_analysis", {})

    assert accepted.command_result.result["accepted"] is True
    assert accepted.command_result.result["payload"]["interval_ids"] == ["int_main"]


def test_report_preview_and_export_actions_are_command_backed():
    state = {"workspace_session_active_report": "report_main"}
    controller = build_workbench_controller(state)

    payload = controller.activate_tool("tool.report_preview").view_model()["tool_views"]
    report_view = payload["active_tool"]
    action_ids = [action["id"] for action in report_view["actions"]]
    assert "action.refresh_report_preview" in action_ids
    assert "action.export_report_bundle" in action_ids

    refresh = controller.dispatch_renderer_action("action.refresh_report_preview", {})
    export = controller.dispatch_renderer_action("action.export_report_bundle", {})

    assert refresh.command_result.result["accepted"] is True
    assert export.command_result.result["accepted"] is True
    assert export.command_result.result["payload"]["formats"] == ["html", "pdf", "docx"]
