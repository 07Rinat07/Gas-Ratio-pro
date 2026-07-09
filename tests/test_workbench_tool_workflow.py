from __future__ import annotations

from core.application_state import ACTIVE_LAS_ID_KEY
from core.workbench_controller import build_workbench_controller
from core.workbench_context import WORKBENCH_SELECTION_KEY
from core.workbench_tool_actions import WORKBENCH_LAST_TOOL_ACTION_KEY
from core.workbench_tools import WORKBENCH_ACTIVE_TOOL_KEY, WORKBENCH_OPEN_TOOLS_KEY
from core.workspace_session import (
    SESSION_ACTIVE_REPORT_KEY,
    SESSION_RECENT_EXPORTS_KEY,
    SESSION_SELECTED_INTERVALS_KEY,
)


def test_open_las_action_updates_application_context_selection_and_active_tool():
    state: dict = {"active_las_id": "old_las", SESSION_SELECTED_INTERVALS_KEY: ["old_interval"]}
    controller = build_workbench_controller(state)

    result = controller.dispatch_renderer_action("action.open_las", {"las_id": "new_las"})

    assert result.command_result.result["accepted"] is True
    assert state[ACTIVE_LAS_ID_KEY] == "new_las"
    assert state[WORKBENCH_SELECTION_KEY]["target"] == "las"
    assert state[WORKBENCH_SELECTION_KEY]["object_id"] == "new_las"
    assert state[WORKBENCH_ACTIVE_TOOL_KEY] == "tool.las_viewer"
    assert "tool.las_viewer" in state[WORKBENCH_OPEN_TOOLS_KEY]
    assert result.view_model()["workspace_context"]["las"] == "new_las"


def test_run_gas_ratio_action_persists_interval_context_and_focuses_analysis_tool():
    state: dict = {"active_las_id": "las_main", SESSION_SELECTED_INTERVALS_KEY: ["int_existing"]}
    controller = build_workbench_controller(state)

    result = controller.dispatch_renderer_action(
        "action.run_gas_ratio_analysis",
        {"interval_ids": ["int_a", "int_existing", "int_b"]},
    )

    assert result.command_result.result["accepted"] is True
    assert state[SESSION_SELECTED_INTERVALS_KEY] == ["int_existing", "int_a", "int_b"]
    assert state[WORKBENCH_SELECTION_KEY]["target"] == "interval"
    assert state[WORKBENCH_SELECTION_KEY]["object_id"] == "int_b"
    assert state[WORKBENCH_ACTIVE_TOOL_KEY] == "tool.gas_ratio_analysis"
    assert result.view_model()["tool_views"]["active_tool_id"] == "tool.gas_ratio_analysis"


def test_report_actions_persist_report_context_and_recent_export_descriptor():
    state: dict = {}
    controller = build_workbench_controller(state)

    refreshed = controller.dispatch_renderer_action("action.refresh_report_preview", {"report_id": "report_main"})
    exported = controller.dispatch_renderer_action(
        "action.export_report_bundle",
        {"report_id": "report_main", "formats": ["html", "pdf"]},
    )

    assert refreshed.command_result.result["accepted"] is True
    assert exported.command_result.result["accepted"] is True
    assert state[SESSION_ACTIVE_REPORT_KEY] == "report_main"
    assert state[WORKBENCH_ACTIVE_TOOL_KEY] == "tool.export"
    assert state[SESSION_RECENT_EXPORTS_KEY] == ["report_main:html,pdf"]
    assert state[WORKBENCH_LAST_TOOL_ACTION_KEY]["action_id"] == "workbench.tool.export_report_bundle"
    assert exported.view_model()["workspace_context"]["active_report"] == "report_main"
