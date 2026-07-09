from core.application_state import (
    ACTIVE_LAS_ID_KEY,
    ACTIVE_PROJECT_ID_KEY,
    ACTIVE_WELL_ID_KEY,
    ACTIVE_WORKSPACE_ID_KEY,
)
from core.command_framework import WorkbenchCommand, WorkbenchCommandRegistry, default_workbench_commands
from core.event_bus import EVENT_QUEUE_KEY
from core.workbench_shell import WorkbenchShellBuilder
from core.workspace_session import SESSION_ACTIVE_REPORT_KEY, SESSION_RECENT_EXPORTS_KEY, SESSION_WINDOW_LAYOUT_KEY


def test_default_commands_are_registered_as_ui_neutral_descriptors():
    commands = default_workbench_commands()

    ids = {command.id for command in commands}

    assert "workspace.open" in ids
    assert "workspace.save_session" in ids
    assert "workspace.reset" in ids
    assert "export.bundle" in ids
    assert all(command.title for command in commands)
    assert all(command.visible for command in commands)


def test_command_registry_executes_handler_and_publishes_event():
    state = {}
    registry = WorkbenchCommandRegistry(state)
    registry.register(WorkbenchCommand("workspace.refresh", "Refresh", "workspace"), lambda payload: payload["value"] + 1)

    result = registry.execute("workspace.refresh", {"value": 41})

    assert result.executed is True
    assert result.result == 42
    assert result.event is not None
    assert state[EVENT_QUEUE_KEY][-1]["name"] == "workbench.command_executed"
    assert state[EVENT_QUEUE_KEY][-1]["payload"]["command_id"] == "workspace.refresh"


def test_workbench_shell_model_contains_core_regions_and_status_payload():
    state = {
        ACTIVE_PROJECT_ID_KEY: "project_alpha",
        ACTIVE_WELL_ID_KEY: "well_one",
        ACTIVE_LAS_ID_KEY: "las_main",
        ACTIVE_WORKSPACE_ID_KEY: "interpretation",
        SESSION_ACTIVE_REPORT_KEY: "engineering_summary",
        SESSION_RECENT_EXPORTS_KEY: ("report.html", "report.pdf"),
        SESSION_WINDOW_LAYOUT_KEY: {"left": 280, "right": 320},
    }

    model = WorkbenchShellBuilder(state).build()

    assert model.panel_ids() == (
        "project_explorer",
        "workspace_toolbar",
        "workspace_area",
        "properties",
        "status_bar",
    )
    assert "workspace.save_session" in model.command_ids()
    assert "export.bundle" in model.command_ids()
    assert model.status.ready() is True
    assert model.status.to_dict()["recent_exports_count"] == 2
    assert model.layout == {"left": 280, "right": 320}


def test_workbench_shell_is_serializable_for_future_streamlit_renderer():
    state = {ACTIVE_PROJECT_ID_KEY: "project_beta"}

    payload = WorkbenchShellBuilder(state).build().to_dict()

    assert payload["context"]["project_id"] == "project_beta"
    assert payload["panels"][0]["id"] == "project_explorer"
    assert payload["commands"][0]["id"]
    assert payload["status"]["ready"] is True
