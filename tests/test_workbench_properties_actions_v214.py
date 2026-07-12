from core.workbench_context import WorkbenchSelectionService
from core.workbench_property_actions import (
    WORKBENCH_PROPERTY_ACTION_REQUEST_KEY,
    WorkbenchPropertyActionService,
    property_actions_for,
)
from core.workbench_shell import WorkbenchShellBuilder


def test_property_actions_are_contextual_and_destructive_actions_require_confirmation():
    dataset = {item["id"]: item for item in property_actions_for("dataset")}
    calculation = {item["id"]: item for item in property_actions_for("calculation")}
    export = {item["id"]: item for item in property_actions_for("export")}

    assert set(dataset) >= {"open", "verify", "delete", "technical"}
    assert dataset["delete"]["destructive"] is True
    assert dataset["delete"]["requires_confirmation"] is True
    assert calculation["verify"]["title"] == "Проверить целостность"
    assert export["download"]["navigation_id"] == "nav.exports"


def test_property_action_request_is_lightweight_and_consumed_once():
    state = {}
    service = WorkbenchPropertyActionService(state)
    payload = service.request({
        "action_id": "verify",
        "target": "calculation",
        "object_id": "calc-1",
        "metadata": {"project_id": "default", "rows": 10},
    })
    assert state[WORKBENCH_PROPERTY_ACTION_REQUEST_KEY]["object_id"] == "calc-1"
    assert payload["metadata"]["rows"] == 10
    assert service.consume()["action_id"] == "verify"
    assert service.consume() is None


def test_property_action_command_is_registered_by_workbench_shell():
    state = {}
    shell = WorkbenchShellBuilder(state)
    result = shell.command_registry.execute(
        "workbench.property_action.request",
        {"action_id": "open", "target": "dataset", "object_id": "dataset-1"},
    )
    assert result.executed is True
    assert state[WORKBENCH_PROPERTY_ACTION_REQUEST_KEY]["target"] == "dataset"


def test_selection_metadata_keeps_repository_context_for_actions():
    state = {}
    selection = WorkbenchSelectionService(state).select(
        "dataset", "dataset-1", {"project_id": "default", "section": "csv"}
    )
    assert selection.metadata["section"] == "csv"
