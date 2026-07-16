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


def test_project_manager_service_creates_and_restores_backup(tmp_path):
    service = ProjectManagerService(tmp_path)
    project = service.create_project("Service Backup").project
    (tmp_path / project.id / "service-note.txt").write_text("backup payload", encoding="utf-8")

    backup = service.create_backup(project.id, "Service backup")
    service.delete_project_complete(project.id)
    restored = service.restore_backup(backup.backup_id)

    assert restored.project_id == project.id
    assert (tmp_path / project.id / "service-note.txt").read_text(encoding="utf-8") == "backup payload"
    assert project.id in [entry.project_id for entry in list_recent_projects(tmp_path, include_missing=True)]


def test_project_manager_service_saves_recovery_checkpoint(tmp_path):
    service = ProjectManagerService(tmp_path)
    project = service.create_project("Checkpoint Service").project

    checkpoint = service.save_recovery_checkpoint(project.id, "import", "Import checkpoint", {"step": 2})

    assert checkpoint.project_id == project.id
    assert checkpoint.active_step == "import"
    assert checkpoint.payload == {"step": 2}


def test_resolve_active_project_uses_single_record_fast_path(tmp_path, monkeypatch):
    service = ProjectManagerService(tmp_path)
    project = service.create_project("Fast Path").project

    def fail_list_projects(*, include_archived=False):
        raise AssertionError("full project enumeration must not run for a valid active project")

    monkeypatch.setattr(service, "list_projects", fail_list_projects)

    resolved = service.resolve_active_project(project.id)

    assert resolved == project


def test_resolve_active_project_enumerates_only_for_missing_record(tmp_path, monkeypatch):
    service = ProjectManagerService(tmp_path)
    fallback = service.ensure_default()
    calls = {"count": 0}
    original = service.list_projects

    def tracked_list_projects(*, include_archived=False):
        calls["count"] += 1
        return original(include_archived=include_archived)

    monkeypatch.setattr(service, "list_projects", tracked_list_projects)

    resolved = service.resolve_active_project("missing-project")

    assert resolved == fallback
    assert calls["count"] == 1


def test_resolve_active_project_recovers_from_malformed_project_json(tmp_path):
    service = ProjectManagerService(tmp_path)
    fallback = service.ensure_default()
    broken_dir = tmp_path / "broken"
    broken_dir.mkdir()
    (broken_dir / "project.json").write_text("{not-json", encoding="utf-8")

    resolved = service.resolve_active_project("broken")

    assert resolved == fallback
