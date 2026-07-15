from pathlib import Path

from core.application_service_container import application_service_container
from services.workbench_application_service import WorkbenchApplicationService


def test_workbench_service_is_session_scoped_and_reused(tmp_path: Path) -> None:
    state = {}
    container = application_service_container(state)
    first = container.workbench(projects_root=tmp_path)
    second = container.workbench(projects_root=tmp_path)
    isolated = container.workbench(projects_root=tmp_path / "other")
    assert first is second
    assert isolated is not first
    assert isinstance(first, WorkbenchApplicationService)
    descriptor = next(item for item in container.descriptors() if item.service_name == "workbench")
    assert descriptor.project_id == "__session__"


def test_workbench_facade_coordinates_selection_and_bulk_actions(tmp_path: Path) -> None:
    state = {}
    service = application_service_container(state).workbench(projects_root=tmp_path)
    selection = service.select("dataset", "ds-1", {"project_id": "p-1"})
    assert selection.object_id == "ds-1"
    service.set_bulk_selection(key="grid", target="dataset", object_ids=["ds-1"])
    request = service.request_bulk_action({
        "target": "dataset", "action_id": "verify", "object_ids": ["ds-1"]
    })
    assert request["object_ids"] == ("ds-1",)
    assert service.consume_bulk_action() == request
    assert service.consume_bulk_action() is None


def test_workbench_entry_service_remains_lazy(tmp_path: Path) -> None:
    state = {}
    service = application_service_container(state).workbench(projects_root=tmp_path)
    before = service.health_snapshot()
    assert before["entry_initialized"] is False
    assert service.project_entries() == []
    after = service.health_snapshot()
    assert after["entry_initialized"] is True


def test_ui_does_not_construct_workbench_coordination_services_directly() -> None:
    for source in (Path("app/streamlit_app.py"), Path("app/workbench_renderer.py")):
        text = source.read_text(encoding="utf-8")
        for constructor in (
            "WorkbenchBulkActionService(",
            "WorkbenchSelectionService(",
            "WorkbenchPropertyActionService(",
            "WorkbenchEntryPointService(",
        ):
            assert constructor not in text
