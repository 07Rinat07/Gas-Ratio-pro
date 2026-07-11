from __future__ import annotations

import pytest

from core.command_framework import WorkbenchCommand, WorkbenchCommandRegistry
from core.event_bus import EVENT_HISTORY_KEY
from core.workbench_controller import build_workbench_controller
from core.workbench_dispatcher import WorkbenchDispatchStep, WorkbenchShellDispatcher
from core.workbench_shell import WORKBENCH_ACTIVE_DOCK_PANE_KEY, WORKBENCH_ACTIVE_NAVIGATION_KEY
from core.workbench_tools import WORKBENCH_ACTIVE_TOOL_KEY


def _shell_events(state):
    return [item for item in state.get(EVENT_HISTORY_KEY, ()) if item["name"] == "workbench.shell.state_changed"]


def test_navigation_dispatch_publishes_one_coherent_final_shell_event():
    state = {}
    controller = build_workbench_controller(state)

    result = controller.select_navigation("nav.las_workspace")
    payload = result.view_model()

    assert state[WORKBENCH_ACTIVE_NAVIGATION_KEY] == "nav.las_workspace"
    assert state[WORKBENCH_ACTIVE_TOOL_KEY] == "tool.las_viewer"
    assert state[WORKBENCH_ACTIVE_DOCK_PANE_KEY] == "dock.tool.las_viewer"
    assert len(_shell_events(state)) == 1
    shell_event = payload["shell_event"]
    assert shell_event["primary_command_id"] == "workbench.navigation.select"
    assert shell_event["command_ids"] == [
        "workbench.navigation.select",
        "workbench.tool.activate",
        "workbench.dock.open",
    ]
    assert shell_event["shell_state"] == {
        "active_navigation_id": "nav.las_workspace",
        "active_workspace": "las_workspace",
        "active_tool_id": "tool.las_viewer",
        "active_dock_pane_id": "dock.tool.las_viewer",
        "open_tool_ids": ["tool.workspace_explorer", "tool.las_viewer"],
    }


def test_tool_and_dock_actions_use_same_dispatch_contract():
    state = {}
    controller = build_workbench_controller(state)

    tool_result = controller.activate_tool("tool.report_preview").view_model()["shell_event"]
    dock_result = controller.collapse_dock_pane("dock.tool.report_preview").view_model()["shell_event"]

    assert tool_result["event"]["name"] == "workbench.shell.state_changed"
    assert tool_result["command_ids"] == ["workbench.tool.activate", "workbench.dock.open"]
    assert dock_result["command_ids"] == ["workbench.dock.collapse"]
    assert dock_result["shell_state"]["active_dock_pane_id"] != "dock.tool.report_preview"
    assert len(_shell_events(state)) == 2


def test_dispatch_rolls_back_all_state_when_a_later_command_fails():
    state = {"stable": {"value": 1}}
    registry = WorkbenchCommandRegistry(state)

    def mutate(_payload):
        state["temporary"] = True
        state["stable"]["value"] = 2

    def fail(_payload):
        raise RuntimeError("forced failure")

    registry.register(WorkbenchCommand("test.mutate", "Mutate"), mutate)
    registry.register(WorkbenchCommand("test.fail", "Fail"), fail)
    dispatcher = WorkbenchShellDispatcher(state, registry, lambda: {"temporary": state.get("temporary")})

    with pytest.raises(RuntimeError, match="forced failure"):
        dispatcher.dispatch(
            "test.atomic",
            (
                WorkbenchDispatchStep("test.mutate", {}),
                WorkbenchDispatchStep("test.fail", {}),
            ),
        )

    assert state == {"stable": {"value": 1}}
    assert _shell_events(state) == []


def test_renderer_shell_event_is_serializable_and_contains_no_runtime_services():
    payload = build_workbench_controller({}).dispatch_renderer_action(
        "action.select_navigation",
        {"navigation_id": "nav.reports"},
    ).view_model()

    shell_event = payload["shell_event"]
    assert isinstance(shell_event["dispatch_id"], str) and shell_event["dispatch_id"]
    text = repr(shell_event)
    assert "DataFrame" not in text
    assert "WorkbenchShellDispatcher object" not in text
    assert "WorkbenchCommandRegistry object" not in text
