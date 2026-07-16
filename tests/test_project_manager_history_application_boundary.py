from pathlib import Path

from services.project_manager_service import ProjectManagerService


def test_project_manager_exposes_serializable_backup_and_history_rows(tmp_path: Path) -> None:
    service = ProjectManagerService(tmp_path, "default")
    project = service.create_project("Boundary project").project

    archive = service.archive_project(project.id, "Architecture boundary archive")
    backup_rows = service.list_backup_rows(project.id)
    history_rows = service.list_history_rows(project.id, limit=50)

    assert archive.project_id == project.id
    assert backup_rows
    assert all(isinstance(row, dict) for row in backup_rows)
    assert any(row["Архив"] == archive.file_name for row in backup_rows)
    assert any(row["Действие"] == "project-archived" for row in history_rows)


def test_project_manager_append_history_returns_plain_row(tmp_path: Path) -> None:
    service = ProjectManagerService(tmp_path, "default")
    project = service.create_project("History project").project

    row = service.append_history(project.id, "opened", "Opened by UI")

    assert row["Действие"] == "opened"
    assert row["Описание"] == "Opened by UI"
    assert isinstance(row, dict)


def test_streamlit_project_manager_does_not_call_project_history_persistence_directly() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    forbidden = (
        "list_project_backups(",
        "archive_project(LAS_CORRELATION_PROJECTS_ROOT",
        "list_project_history(",
        "append_project_history(",
        "build_project_backups_table(",
        "build_project_history_table(",
    )
    for token in forbidden:
        assert token not in source
