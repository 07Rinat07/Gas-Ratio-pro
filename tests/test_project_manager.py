from __future__ import annotations

from pathlib import Path

from projects import (
    append_project_history,
    archive_project,
    build_project_backups_table,
    build_project_history_table,
    build_project_templates_table,
    clear_project_recovery_state,
    create_project,
    create_project_backup,
    create_project_from_template,
    create_project_template,
    list_project_backups,
    list_project_history,
    list_project_templates,
    load_project_recovery_state,
    project_manager_status,
    save_project_recovery_state,
)


def test_project_history_and_recovery_checkpoint_are_metadata_only(tmp_path: Path):
    project = create_project(tmp_path, name="Recovery Demo")

    entry = append_project_history(tmp_path, project.id, "opened", "Project opened")
    state = save_project_recovery_state(
        tmp_path,
        project.id,
        "data-workspace",
        "Manual checkpoint",
        {"rows": 10},
    )

    history = list_project_history(tmp_path, project.id)
    loaded_state = load_project_recovery_state(tmp_path, project.id)

    assert entry.action == "opened"
    assert state.active_step == "data-workspace"
    assert loaded_state is not None
    assert loaded_state.payload == {"rows": 10}
    assert len(history) == 2
    assert build_project_history_table(history)[0]["Действие"] == "autosave"

    assert clear_project_recovery_state(tmp_path, project.id) is True
    assert load_project_recovery_state(tmp_path, project.id) is None


def test_project_templates_create_new_projects(tmp_path: Path):
    source = create_project(tmp_path, name="Template Source", description="Original")

    template = create_project_template(tmp_path, source.id, "Standard workspace", "Base structure")
    templates = list_project_templates(tmp_path)
    created = create_project_from_template(tmp_path, template.id, "New from template")

    assert templates[0].id == template.id
    assert created.name == "New from template"
    assert created.id != source.id
    assert build_project_templates_table(templates)[0]["Шаблон"] == "Standard workspace"


def test_project_backups_and_archive_create_zip_records(tmp_path: Path):
    project = create_project(tmp_path, name="Backup Demo")
    project_dir = tmp_path / project.id
    (project_dir / "notes.txt").write_text("metadata", encoding="utf-8")

    backup = create_project_backup(tmp_path, project.id, "Manual backup")
    archive = archive_project(tmp_path, project.id, "Archive backup")
    backups = list_project_backups(tmp_path, project.id)
    status = project_manager_status(tmp_path, project.id)

    assert backup.file_name.endswith(".zip")
    assert archive.file_name.endswith(".zip")
    assert len(backups) == 2
    assert status["backups"] == 2
    assert build_project_backups_table(backups)[0]["Архив"].endswith(".zip")


def test_project_backup_restore_recreates_project_directory(tmp_path: Path):
    project = create_project(tmp_path, name="Restore Demo")
    project_dir = tmp_path / project.id
    (project_dir / "notes.txt").write_text("original", encoding="utf-8")

    backup = create_project_backup(tmp_path, project.id, "Before failure")
    assert backup.id

    import shutil
    from projects import restore_project_backup

    shutil.rmtree(project_dir)
    result = restore_project_backup(tmp_path, backup.id)

    assert result.project_id == project.id
    assert result.backup_id == backup.id
    assert result.files_restored >= 2
    assert (project_dir / "project.json").exists()
    assert (project_dir / "notes.txt").read_text(encoding="utf-8") == "original"
    assert list_project_history(tmp_path, project.id)[0].action == "backup-restored"


def test_project_backup_restore_protects_existing_project_without_overwrite(tmp_path: Path):
    project = create_project(tmp_path, name="Protected Restore")
    backup = create_project_backup(tmp_path, project.id, "Protected backup")

    from projects import restore_project_backup

    try:
        restore_project_backup(tmp_path, backup.id)
    except FileExistsError as exc:
        assert project.id in str(exc)
    else:
        raise AssertionError("Existing project restore must require overwrite=True")

    result = restore_project_backup(tmp_path, backup.id, overwrite=True)
    assert result.overwritten_existing is True
    assert (tmp_path / project.id / "project.json").exists()
