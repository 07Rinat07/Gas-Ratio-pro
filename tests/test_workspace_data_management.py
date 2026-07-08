from pathlib import Path

from projects.exports import (
    clear_project_exports,
    delete_project_export,
    list_project_exports,
    read_project_export_file_bytes,
    save_project_export,
)
from projects.las_files import (
    clear_project_las_files,
    delete_project_las_file,
    list_project_las_files,
    save_project_las_file,
)


def test_delete_project_export_removes_manifest_record_and_files(tmp_path: Path) -> None:
    record = save_project_export(
        b"export-data",
        root=tmp_path,
        project_id="demo",
        label="Report",
        file_name="report.html",
        mime_type="text/html",
        kind="html",
        source="LAS",
    )

    assert read_project_export_file_bytes(tmp_path, "demo", record.id) == b"export-data"
    assert delete_project_export(tmp_path, "demo", record.id) is True
    assert list_project_exports(tmp_path, "demo") == ()
    assert not (tmp_path / "demo" / "exports" / record.id).exists()
    assert delete_project_export(tmp_path, "demo", record.id) is False


def test_clear_project_exports_removes_all_records_and_files(tmp_path: Path) -> None:
    first = save_project_export(b"a", tmp_path, "demo", "A", "a.txt", "text/plain", "txt")
    second = save_project_export(b"b", tmp_path, "demo", "B", "b.txt", "text/plain", "txt")

    assert len(list_project_exports(tmp_path, "demo")) == 2
    assert clear_project_exports(tmp_path, "demo") == 2
    assert list_project_exports(tmp_path, "demo") == ()
    assert not (tmp_path / "demo" / "exports" / first.id).exists()
    assert not (tmp_path / "demo" / "exports" / second.id).exists()


def test_clear_project_las_files_removes_all_las_versions(tmp_path: Path) -> None:
    first = save_project_las_file(b"~Version\n", tmp_path, "demo", "well1.las", "WELL-1", "v1")
    second = save_project_las_file(b"~Version\n", tmp_path, "demo", "well2.las", "WELL-2", "v1")

    assert len(list_project_las_files(tmp_path, "demo", include_archived=True)) == 2
    assert clear_project_las_files(tmp_path, "demo") == 2
    assert list_project_las_files(tmp_path, "demo", include_archived=True) == ()
    assert not (tmp_path / "demo" / "las_files" / first.id).exists()
    assert not (tmp_path / "demo" / "las_files" / second.id).exists()


def test_delete_project_las_file_is_idempotent(tmp_path: Path) -> None:
    record = save_project_las_file(b"~Version\n", tmp_path, "demo", "well1.las", "WELL-1", "v1")

    assert delete_project_las_file(tmp_path, "demo", record.id) is True
    assert delete_project_las_file(tmp_path, "demo", record.id) is False
    assert list_project_las_files(tmp_path, "demo", include_archived=True) == ()
