from core.workbench_bulk_actions import (
    WORKBENCH_BULK_ACTION_REQUEST_KEY,
    WorkbenchBulkActionService,
    bulk_actions_for,
)


def test_bulk_actions_are_contextual_and_delete_requires_confirmation():
    datasets = {item["id"]: item for item in bulk_actions_for("dataset")}
    calculations = {item["id"]: item for item in bulk_actions_for("calculation")}
    exports = {item["id"]: item for item in bulk_actions_for("export")}

    assert set(datasets) == {"verify", "export", "delete"}
    assert datasets["delete"]["destructive"] is True
    assert datasets["delete"]["requires_confirmation"] is True
    assert "export" in calculations
    assert "export" in exports


def test_bulk_request_deduplicates_ids_and_is_consumed_once():
    state = {}
    service = WorkbenchBulkActionService(state)
    request = service.request({
        "target": "dataset",
        "action_id": "verify",
        "object_ids": ["d1", "d1", "d2"],
        "metadata": {"project_id": "default", "section": "csv"},
    })
    assert request["object_ids"] == ("d1", "d2")
    assert WORKBENCH_BULK_ACTION_REQUEST_KEY in state
    assert service.consume()["object_ids"] == ("d1", "d2")
    assert service.consume() is None


def test_bulk_selection_is_stored_by_grid_key():
    state = {}
    service = WorkbenchBulkActionService(state)
    service.set_selection(
        key="datasets_csv",
        target="dataset",
        object_ids=["d1", "d2"],
        metadata={"project_id": "default", "section": "csv"},
    )
    assert state["workbench_bulk_selections"]["datasets_csv"]["object_ids"] == ("d1", "d2")


def test_data_grid_enables_bulk_mode_for_supported_tables():
    source = open("app/streamlit_app.py", encoding="utf-8").read()
    assert "enable_multi_selection: bool = False" in source
    assert source.count("enable_multi_selection=True") >= 3
    assert "def _process_workbench_bulk_action" in source
    assert "create_project_backup" in source
    assert "Bulk {target} package" in source
