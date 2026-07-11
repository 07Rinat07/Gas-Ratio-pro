from core.event_bus import EVENT_HISTORY_KEY
from core.workbench_controller import build_workbench_controller
from core.workbench_shell import WORKBENCH_DOCK_LAYOUT_KEY, WorkbenchDockManager, WorkbenchShellBuilder


def _pane(state, pane_id):
    return next(item for item in state[WORKBENCH_DOCK_LAYOUT_KEY] if item["id"] == pane_id)


def test_dock_manager_persists_open_close_collapse_restore_and_focus():
    state = {}
    WorkbenchShellBuilder(state).build()
    manager = WorkbenchDockManager(state)

    manager.focus("dock.properties")
    assert _pane(state, "dock.properties")["opened"] is True
    assert state["workbench_active_dock_pane"] == "dock.properties"

    manager.collapse("dock.properties")
    assert _pane(state, "dock.properties")["collapsed"] is True
    assert "workbench_active_dock_pane" not in state

    manager.restore("dock.properties")
    assert _pane(state, "dock.properties")["collapsed"] is False
    assert _pane(state, "dock.properties")["opened"] is True

    manager.close("dock.properties")
    assert _pane(state, "dock.properties")["opened"] is False
    assert any(item["name"] == "workbench.dock.closed" for item in state[EVENT_HISTORY_KEY])


def test_controller_routes_dock_actions_through_commands():
    state = {}
    controller = build_workbench_controller(state)

    result = controller.dispatch_renderer_action("action.collapse_dock_pane", {"pane_id": "dock.project_explorer"})
    assert result.command_result.command_id == "workbench.dock.collapse"
    assert _pane(state, "dock.project_explorer")["collapsed"] is True

    result = controller.dispatch_renderer_action("action.restore_dock_pane", {"pane_id": "dock.project_explorer"})
    assert result.command_result.command_id == "workbench.dock.restore"
    assert result.view_model()["interaction"]["active_dock_pane_id"] == "dock.project_explorer"


def test_registered_tools_have_serializable_dock_panes_and_activation_opens_tool_pane():
    state = {}
    controller = build_workbench_controller(state)
    payload = controller.view_model()

    tool_panes = {pane["metadata"].get("tool_id"): pane for pane in payload["dock_panes"] if pane["metadata"].get("tool_id")}
    assert "tool.las_viewer" in tool_panes
    assert tool_panes["tool.las_viewer"]["opened"] is False

    result = controller.activate_tool("tool.las_viewer")
    panes = {pane["id"]: pane for pane in result.view_model()["dock_panes"]}
    assert panes["dock.tool.las_viewer"]["opened"] is True
    assert result.view_model()["interaction"]["active_dock_pane_id"] == "dock.tool.las_viewer"
    assert all("DataFrame" not in repr(pane) for pane in panes.values())
