from __future__ import annotations

from core.event_bus import EVENT_HISTORY_KEY
from core.workspace_session import WorkspaceSession, WorkspaceSessionManager
from core.workbench_controller import build_workbench_controller
from core.workbench_tools import (
    WORKBENCH_ACTIVE_TOOL_KEY,
    WORKBENCH_OPEN_TOOLS_KEY,
    WORKBENCH_TOOLS_KEY,
    WorkbenchToolDescriptor,
    WorkbenchToolManager,
    WorkbenchToolRegistry,
)


def _event_names(state: dict) -> list[str]:
    return [event["name"] for event in state.get(EVENT_HISTORY_KEY, [])]


def test_tool_registry_seeds_default_engineering_tools():
    state = {}
    registry = WorkbenchToolRegistry(state)

    tools = registry.list()

    assert state[WORKBENCH_TOOLS_KEY]
    assert tools[0].id == "tool.workspace_explorer"
    assert "tool.gas_ratio_analysis" in {tool.id for tool in tools}
    assert registry.get("tool.export").category == "reporting"


def test_tool_registry_registers_custom_tool_and_publishes_event():
    state = {}
    registry = WorkbenchToolRegistry(state)

    tool = registry.register(
        WorkbenchToolDescriptor(
            "tool.custom_crossplot",
            "Custom Crossplot",
            "visualization",
            supported_targets=("las",),
            order=100,
        )
    )

    assert tool.id == "tool.custom_crossplot"
    assert registry.get("tool.custom_crossplot").supported_targets == ("las",)
    assert "workbench.tool.registered" in _event_names(state)


def test_tool_manager_activates_tool_tracks_open_order_and_events():
    state = {}
    manager = WorkbenchToolManager(state)

    manager.activate("tool.gas_ratio_analysis", {"source": "test"})

    assert state[WORKBENCH_ACTIVE_TOOL_KEY] == "tool.gas_ratio_analysis"
    assert state[WORKBENCH_OPEN_TOOLS_KEY] == ["tool.workspace_explorer", "tool.gas_ratio_analysis"]
    assert manager.open_tool_ids() == ("tool.workspace_explorer", "tool.gas_ratio_analysis")
    assert "workbench.tool.activated" in _event_names(state)
    assert "workbench.active_tool.changed" in _event_names(state)


def test_controller_activates_tool_through_command_framework_and_renderer_action():
    state = {}
    controller = build_workbench_controller(state)

    result = controller.dispatch_renderer_action("action.activate_tool", {"tool_id": "tool.report_preview"})
    payload = result.view_model()

    assert result.command_result.executed is True
    assert payload["active_tool_id"] == "tool.report_preview"
    assert payload["workspace_context"]["active_tool"] == "tool.report_preview"
    assert "tool.report_preview" in payload["open_tool_ids"]


def test_workspace_session_persists_workbench_tool_state():
    state = {}
    controller = build_workbench_controller(state)
    controller.activate_tool("tool.export")

    session = WorkspaceSession.from_state(state)

    assert session.workbench_active_tool == "tool.export"
    assert "tool.export" in session.workbench_open_tools
    restored_state = {}
    WorkspaceSessionManager(restored_state).restore(session)
    assert restored_state[WORKBENCH_ACTIVE_TOOL_KEY] == "tool.export"
    assert "tool.export" in restored_state[WORKBENCH_OPEN_TOOLS_KEY]
