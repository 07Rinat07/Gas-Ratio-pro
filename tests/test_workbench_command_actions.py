from core.workbench_shell import (
    WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID,
    WORKBENCH_ACTIVE_DOCK_PANE_KEY,
    WORKBENCH_ACTIVE_NAVIGATION_KEY,
    WORKBENCH_SELECT_NAVIGATION_COMMAND_ID,
    WorkbenchShellBuilder,
    register_workbench_interaction_commands,
)
from core.command_framework import WorkbenchCommandRegistry


def test_workbench_builder_exposes_interaction_commands():
    model = WorkbenchShellBuilder({}).build()

    assert WORKBENCH_SELECT_NAVIGATION_COMMAND_ID in model.command_ids()
    assert WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID in model.command_ids()


def test_navigation_command_updates_state_and_publishes_event():
    state = {}
    registry = register_workbench_interaction_commands(state, WorkbenchCommandRegistry(state))

    result = registry.execute(WORKBENCH_SELECT_NAVIGATION_COMMAND_ID, {"navigation_id": " nav.reports "})

    assert result.executed is True
    assert result.result == {"active_navigation_id": "nav.reports"}
    assert state[WORKBENCH_ACTIVE_NAVIGATION_KEY] == "nav.reports"
    assert result.event is not None
    assert result.event.name == "workbench.command_executed"


def test_dock_command_updates_state_and_supports_generic_id_payload():
    state = {}
    registry = register_workbench_interaction_commands(state, WorkbenchCommandRegistry(state))

    result = registry.execute(WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID, {"id": " dock.properties "})

    assert result.executed is True
    assert result.result == {"active_dock_pane_id": "dock.properties"}
    assert state[WORKBENCH_ACTIVE_DOCK_PANE_KEY] == "dock.properties"


def test_command_updated_state_is_reflected_in_shell_model():
    state = {}
    builder = WorkbenchShellBuilder(state)

    builder.command_registry.execute(WORKBENCH_SELECT_NAVIGATION_COMMAND_ID, {"navigation_id": "nav.exports"})
    builder.command_registry.execute(WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID, {"pane_id": "dock.properties"})
    model = builder.build()

    assert model.interaction.active_navigation_id == "nav.exports"
    assert model.interaction.active_workspace == "exports"
    assert model.interaction.active_dock_pane_id == "dock.properties"
