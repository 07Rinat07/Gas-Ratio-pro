from pathlib import Path

import pytest

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from services.las_workspace_application_service import LasWorkspaceApplicationService


def test_service_is_bound_to_one_project(tmp_path: Path):
    service = LasWorkspaceApplicationService(root=tmp_path, project_id="alpha")
    assert service.project_id == "alpha"
    assert service.list_files() == ()
    snapshot = service.health_snapshot()
    assert snapshot["project_id"] == "alpha"
    assert snapshot["files"] == 0


def test_container_reuses_project_scoped_las_service(tmp_path: Path):
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry)
    first = container.las_workspace(project_id="alpha", root=tmp_path)
    second = container.las_workspace(project_id="alpha", root=tmp_path)
    other = container.las_workspace(project_id="beta", root=tmp_path)
    assert first is second
    assert first is not other
    assert {d.service_name for d in container.descriptors()} == {"las_workspace"}


def test_invalid_project_id_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        LasWorkspaceApplicationService(root=tmp_path, project_id="../escape")
