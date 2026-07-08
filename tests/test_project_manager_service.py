from __future__ import annotations

from services.project_manager_service import ProjectManagerService
from projects.exports import list_project_exports, save_project_export
from projects.recent_projects import list_recent_projects
from projects.repository import DEFAULT_PROJECT_ID


def test_project_manager_service_creates_project_and_touches_recent_history(tmp_path):
    service = ProjectManagerService(tmp_path)

    result = service.create_project("Test Project", "demo")

    assert result.project.id != DEFAULT_PROJECT_ID
    assert (tmp_path / result.project.id / "project.json").exists()
    recent_ids = [entry.project_id for entry in list_recent_projects(tmp_path, include_missing=True)]
    assert result.project.id in recent_ids


def test_project_manager_service_removes_recent_entry_without_deleting_project(tmp_path):
    service = ProjectManagerService(tmp_path)
    project = service.create_project("Recent Only").project

    removed = service.remove_recent_entry(project.id)

    assert removed is True
    assert (tmp_path / project.id / "project.json").exists()
    assert project.id not in [entry.project_id for entry in list_recent_projects(tmp_path, include_missing=True)]


def test_project_manager_service_delete_project_clears_exports_and_history(tmp_path):
    service = ProjectManagerService(tmp_path)
    project = service.create_project("Delete Me").project
    export = save_project_export(
        b"data",
        root=tmp_path,
        project_id=project.id,
        label="Demo Export",
        file_name="demo.txt",
    )

    result = service.delete_project_complete(project.id)

    assert result.project_deleted is True
    assert result.recent_history_removed is True
    assert result.exports_removed == 1
    assert result.fallback_project_id == DEFAULT_PROJECT_ID
    assert not (tmp_path / project.id).exists()
    assert project.id not in [entry.project_id for entry in list_recent_projects(tmp_path, include_missing=True)]
    assert list_project_exports(tmp_path, project.id) == ()
    assert not (tmp_path / project.id / "exports" / export.id).exists()


def test_project_manager_service_protects_default_project(tmp_path):
    service = ProjectManagerService(tmp_path)
    service.ensure_default()

    try:
        service.delete_project_complete(DEFAULT_PROJECT_ID)
    except ValueError as exc:
        assert "Основной проект" in str(exc)
    else:
        raise AssertionError("Default project deletion must be rejected")

    assert (tmp_path / DEFAULT_PROJECT_ID / "project.json").exists()
