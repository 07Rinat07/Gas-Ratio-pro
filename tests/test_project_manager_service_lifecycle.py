from __future__ import annotations

from core.storage_lifecycle import DeleteEngine, ResourceManager
from services.project_manager_service import ProjectManagerService
from projects.repository import DEFAULT_PROJECT_ID


def test_project_delete_uses_lifecycle_delete_engine_and_releases_project_resources(tmp_path):
    resource_manager = ResourceManager()
    delete_engine = DeleteEngine(resource_manager, attempts=1)
    service = ProjectManagerService(tmp_path, delete_engine=delete_engine)
    project = service.create_project("Lifecycle Project").project
    project_dir = tmp_path / project.id
    locked_file = project_dir / "datasets" / "demo" / "source.xlsx"
    locked_file.parent.mkdir(parents=True, exist_ok=True)
    locked_file.write_text("demo", encoding="utf-8")

    released = {"count": 0}

    def release_callback() -> None:
        released["count"] += 1

    resource_manager.register_file(
        locked_file,
        owner="test-project-preview",
        release_callback=release_callback,
    )

    result = service.delete_project_complete(project.id)

    assert result.project_deleted is True
    assert result.delete_result is not None
    assert result.delete_result.released_resources >= 1
    assert released["count"] == 1
    assert not project_dir.exists()
    assert not resource_manager.diagnostics().resources


def test_project_service_compatibility_aliases(tmp_path):
    service = ProjectManagerService(tmp_path)
    created = service.create("Alias Project")

    assert service.load(created.project.id).id == created.project.id
    assert service.open_project(created.project.id).id == created.project.id
    assert created.project.id in [project.id for project in service.list()]

    deleted = service.delete(created.project.id)

    assert deleted.project_deleted is True
    assert deleted.fallback_project_id == DEFAULT_PROJECT_ID


def test_project_service_health_and_index_contract(tmp_path):
    service = ProjectManagerService(tmp_path)
    project = service.create_project("Indexed Project").project
    sync = service.rebuild_index(project.id)
    health = service.health()

    assert sync.project_id == project.id
    assert health.projects_count >= 1
    assert health.default_project_exists is True
