from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from services.project_manager_service import ProjectManagerService
from services.export_manager_service import ExportManagerService
from services.well_manager_service import WellManagerService
from services.dataset_manager_service import DatasetManagerService


def test_workspace_managers_are_lazy_and_reused(tmp_path):
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry)
    project = container.project_manager(root=tmp_path / "projects", default_project_id="default")
    assert project is container.project_manager(root=tmp_path / "projects", default_project_id="default")
    assert isinstance(project, ProjectManagerService)
    assert isinstance(container.export_manager(root=tmp_path / "projects"), ExportManagerService)
    assert isinstance(container.well_manager(root=tmp_path / "wells"), WellManagerService)
    assert isinstance(container.dataset_manager(root=tmp_path / "projects"), DatasetManagerService)
    snapshot = container.snapshot()
    assert snapshot["active"] == 4
    assert {item["project_id"] for item in snapshot["services"]} == {"__workspace__"}


def test_workspace_service_keys_are_root_scoped(tmp_path):
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry)
    first = container.export_manager(root=tmp_path / "a")
    second = container.export_manager(root=tmp_path / "b")
    assert first is not second
