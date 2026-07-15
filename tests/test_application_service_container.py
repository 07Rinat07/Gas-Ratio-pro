from pathlib import Path

from core.application_service_container import application_service_container
from core.runtime_service_registry import runtime_service_registry
from services.interpretation_correlation_application_service import (
    InterpretationCorrelationApplicationService,
)


def test_container_reuses_project_scoped_correlation_service(tmp_path: Path) -> None:
    state = {}
    container = application_service_container(state)

    first = container.correlation(project_id="demo", root=tmp_path)
    second = container.correlation(project_id="demo", root=tmp_path)

    assert first is second
    assert isinstance(first, InterpretationCorrelationApplicationService)
    descriptors = container.descriptors()
    assert len(descriptors) == 1
    assert descriptors[0].project_id == "demo"
    registry_descriptors = runtime_service_registry(state).descriptors()
    assert any(item.scope == "project" and item.type_name == "InterpretationCorrelationApplicationService" for item in registry_descriptors)


def test_project_scope_cleanup_removes_application_service(tmp_path: Path) -> None:
    state = {}
    container = application_service_container(state)
    service = container.correlation(project_id="demo", root=tmp_path)
    assert service.health()["project_id"] == "demo"

    registry = runtime_service_registry(state)
    registry.shutdown_scopes({"project"})

    assert container.snapshot()["active"] == 0


def test_correlation_application_service_manages_workspaces(tmp_path: Path) -> None:
    service = InterpretationCorrelationApplicationService(root=tmp_path, project_id="demo")

    created = service.create_workspace(name="Regional correlation", description="test")
    loaded = service.get_workspace(created.id)

    assert loaded.name == "Regional correlation"
    assert service.list_workspaces() == (loaded,)
    assert service.delete_workspace(created.id) is True
    assert service.list_workspaces() == ()
