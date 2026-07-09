from __future__ import annotations

import pytest

from core.workbench_controller import build_workbench_controller
from core.workbench_shell import WORKBENCH_ACTIVE_DOCK_PANE_KEY, WORKBENCH_ACTIVE_NAVIGATION_KEY


def test_workbench_controller_builds_stable_view_model():
    controller = build_workbench_controller({})

    payload = controller.view_model()

    assert payload["renderer"] == "streamlit-modern"
    assert payload["navigation"][0]["id"] == "nav.dashboard"
    assert payload["interaction"]["active_dock_pane_id"] == "dock.workspace_area"
    assert "action.select_navigation" in controller.contract().action_ids()


def test_workbench_controller_selects_navigation_through_command_framework():
    state = {}
    controller = build_workbench_controller(state)

    result = controller.select_navigation(" nav.reports ")

    assert result.command_result.executed is True
    assert result.command_result.command_id == "workbench.navigation.select"
    assert state[WORKBENCH_ACTIVE_NAVIGATION_KEY] == "nav.reports"
    assert result.view_model()["interaction"]["active_navigation_id"] == "nav.reports"
    assert result.view_model()["interaction"]["active_workspace"] == "reports"


def test_workbench_controller_activates_dock_pane_through_command_framework():
    state = {}
    controller = build_workbench_controller(state)

    result = controller.activate_dock_pane("dock.properties")

    assert result.command_result.executed is True
    assert result.command_result.command_id == "workbench.dock.activate"
    assert state[WORKBENCH_ACTIVE_DOCK_PANE_KEY] == "dock.properties"
    assert result.view_model()["interaction"]["active_dock_pane_id"] == "dock.properties"


def test_workbench_controller_dispatches_renderer_actions_with_validation():
    state = {}
    controller = build_workbench_controller(state)

    result = controller.dispatch_renderer_action(
        "action.select_navigation",
        {"navigation_id": "nav.exports"},
    )

    assert result.command_result.executed is True
    assert state[WORKBENCH_ACTIVE_NAVIGATION_KEY] == "nav.exports"
    assert result.contract.to_dict()["interaction"]["active_workspace"] == "exports"


def test_workbench_controller_rejects_unknown_navigation_and_dock_targets():
    controller = build_workbench_controller({})

    with pytest.raises(KeyError):
        controller.select_navigation("nav.missing")
    with pytest.raises(KeyError):
        controller.activate_dock_pane("dock.missing")
