from __future__ import annotations

from core.application_state import (
    ACTIVE_LAS_ID_KEY,
    ACTIVE_PROJECT_ID_KEY,
    ACTIVE_WELL_ID_KEY,
    ACTIVE_WORKSPACE_ID_KEY,
)
from core.event_bus import EVENT_HISTORY_KEY
from core.workspace_session import WorkspaceSession
from core.workbench_context import (
    WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY,
    WORKBENCH_LIFECYCLE_STATE_KEY,
    WORKBENCH_SELECTION_KEY,
    WorkbenchSelectionService,
    WorkspaceContext,
)
from core.workbench_controller import build_workbench_controller
from core.workbench_lifecycle import (
    WORKBENCH_LIFECYCLE_CLOSED,
    WORKBENCH_LIFECYCLE_INITIALIZED,
    WORKBENCH_LIFECYCLE_OPEN,
    WorkbenchLifecycleManager,
)
from core.workbench_shell import WORKBENCH_ACTIVE_DOCK_PANE_KEY, WORKBENCH_ACTIVE_NAVIGATION_KEY


def _event_names(state: dict) -> list[str]:
    return [event["name"] for event in state.get(EVENT_HISTORY_KEY, [])]


def test_lifecycle_manager_initializes_workbench_and_publishes_event():
    state = {}
    manager = WorkbenchLifecycleManager(state)

    result = manager.initialize()

    assert result.executed is True
    assert result.state == WORKBENCH_LIFECYCLE_INITIALIZED
    assert state[WORKBENCH_LIFECYCLE_STATE_KEY] == WORKBENCH_LIFECYCLE_INITIALIZED
    assert result.context.lifecycle_state == WORKBENCH_LIFECYCLE_INITIALIZED
    assert "workbench.initialized" in _event_names(state)


def test_lifecycle_manager_opens_workspace_from_session():
    state = {}
    session = WorkspaceSession(
        project_id="project_alpha",
        well_id="well_one",
        las_id="las_main",
        workspace_id="workspace_engineering",
        workbench_active_navigation="nav.reports",
        workbench_active_dock_pane="dock.properties",
    )

    result = WorkbenchLifecycleManager(state).open_workspace(session)

    assert result.state == WORKBENCH_LIFECYCLE_OPEN
    assert state[ACTIVE_PROJECT_ID_KEY] == "project_alpha"
    assert state[ACTIVE_WELL_ID_KEY] == "well_one"
    assert state[ACTIVE_LAS_ID_KEY] == "las_main"
    assert state[ACTIVE_WORKSPACE_ID_KEY] == "workspace_engineering"
    assert state[WORKBENCH_ACTIVE_NAVIGATION_KEY] == "nav.reports"
    assert state[WORKBENCH_ACTIVE_DOCK_PANE_KEY] == "dock.properties"
    assert state[WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY] == session.session_id()
    assert result.context.application.project_id == "project_alpha"
    assert result.context.interaction.active_navigation_id == "nav.reports"
    assert "workbench.workspace.opened" in _event_names(state)


def test_lifecycle_manager_closes_workspace_and_clears_opened_session():
    state = {WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY: "session_x"}
    manager = WorkbenchLifecycleManager(state)

    result = manager.close_workspace()

    assert result.state == WORKBENCH_LIFECYCLE_CLOSED
    assert state[WORKBENCH_LIFECYCLE_STATE_KEY] == WORKBENCH_LIFECYCLE_CLOSED
    assert WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY not in state
    assert result.context.lifecycle_state == WORKBENCH_LIFECYCLE_CLOSED
    assert "workbench.workspace.closed" in _event_names(state)


def test_selection_service_tracks_domain_references_and_mirrors_known_targets():
    state = {}
    service = WorkbenchSelectionService(state)

    selection = service.select("interval", "int_100_120", {"confidence": "high"})

    assert selection.target == "interval"
    assert state[WORKBENCH_SELECTION_KEY]["object_id"] == "int_100_120"
    assert state["workspace_session_selected_intervals"] == ["int_100_120"]
    assert "workbench.selection.changed" in _event_names(state)

    cleared = service.clear("test")
    assert cleared.is_empty() is True
    assert WORKBENCH_SELECTION_KEY not in state


def test_controller_exposes_workspace_context_and_selection_boundary():
    state = {ACTIVE_PROJECT_ID_KEY: "project_alpha"}
    controller = build_workbench_controller(state)

    controller.select_navigation("nav.interpretation")
    controller.activate_dock_pane("dock.properties")
    controller.select_object("plot", "plot_gas_ratio")

    payload = controller.view_model()
    context = payload["workspace_context"]

    assert context["project"] == "project_alpha"
    assert context["navigation"] == "nav.interpretation"
    assert context["dock_pane"] == "dock.properties"
    assert context["selection"]["target"] == "plot"
    assert context["active_plot"] == "plot_gas_ratio"


def test_workspace_context_is_lightweight_and_serializable():
    state = {
        ACTIVE_PROJECT_ID_KEY: "p",
        ACTIVE_WELL_ID_KEY: "w",
        ACTIVE_LAS_ID_KEY: "l",
        ACTIVE_WORKSPACE_ID_KEY: "ws",
    }
    controller = build_workbench_controller(state)
    controller.select_object("report", "engineering_report")

    context = WorkspaceContext.from_state(state, controller.shell()).to_dict()

    assert context["application"] == {
        "project_id": "p",
        "well_id": "w",
        "las_id": "l",
        "workspace_id": "ws",
    }
    assert context["active_report"] == "engineering_report"
    assert "renderer_state" in context
