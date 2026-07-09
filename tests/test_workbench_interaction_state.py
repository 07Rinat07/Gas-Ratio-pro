from core.workbench_shell import (
    WORKBENCH_ACTIVE_DOCK_PANE_KEY,
    WORKBENCH_ACTIVE_NAVIGATION_KEY,
    WorkbenchDockPane,
    WorkbenchNavigationItem,
    WorkbenchShellBuilder,
    activate_workbench_dock_pane,
    select_workbench_navigation,
)


def test_workbench_interaction_state_uses_safe_defaults():
    payload = WorkbenchShellBuilder({}).build().to_dict()

    assert payload["interaction"] == {
        "active_navigation_id": "nav.dashboard",
        "active_workspace": "dashboard",
        "active_dock_pane_id": "dock.workspace_area",
    }


def test_workbench_interaction_state_restores_valid_selection_from_state():
    state = {
        WORKBENCH_ACTIVE_NAVIGATION_KEY: "nav.reports",
        WORKBENCH_ACTIVE_DOCK_PANE_KEY: "dock.properties",
    }

    interaction = WorkbenchShellBuilder(state).build().interaction

    assert interaction.active_navigation_id == "nav.reports"
    assert interaction.active_workspace == "reports"
    assert interaction.active_dock_pane_id == "dock.properties"


def test_workbench_interaction_state_falls_back_when_saved_values_are_stale():
    state = {
        WORKBENCH_ACTIVE_NAVIGATION_KEY: "nav.deleted",
        WORKBENCH_ACTIVE_DOCK_PANE_KEY: "dock.deleted",
    }
    navigation = (
        WorkbenchNavigationItem("nav.hidden", "Hidden", "hidden", visible=False, order=1),
        WorkbenchNavigationItem("nav.enabled", "Enabled", "enabled", order=2),
    )
    dock_panes = (
        WorkbenchDockPane("dock.left", "project_explorer", "left", order=1),
        WorkbenchDockPane("dock.center", "workspace_area", "center", order=2),
    )

    interaction = WorkbenchShellBuilder(state).build(navigation=navigation, dock_panes=dock_panes).interaction

    assert interaction.active_navigation_id == "nav.enabled"
    assert interaction.active_workspace == "enabled"
    assert interaction.active_dock_pane_id == "dock.center"


def test_workbench_selection_helpers_persist_trimmed_identifiers():
    state = {}

    select_workbench_navigation(state, "  nav.exports  ")
    activate_workbench_dock_pane(state, "  dock.properties  ")

    assert state[WORKBENCH_ACTIVE_NAVIGATION_KEY] == "nav.exports"
    assert state[WORKBENCH_ACTIVE_DOCK_PANE_KEY] == "dock.properties"
