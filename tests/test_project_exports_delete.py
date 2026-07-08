from __future__ import annotations

from projects.exports import clear_project_exports, delete_project_export, list_project_exports, save_project_export
from projects.repository import create_project


def test_delete_project_export_removes_manifest_record_and_file_directory(tmp_path):
    root = tmp_path / "projects"
    project = create_project(root, name="Exports")
    record = save_project_export(b"payload", root=root, project_id=project.id, label="One", file_name="one.txt")
    export_dir = root / project.id / "exports" / record.id
    assert export_dir.exists()

    assert delete_project_export(root, project.id, record.id) is True

    assert not export_dir.exists()
    assert list_project_exports(root, project.id) == ()


def test_clear_project_exports_removes_all_export_directories(tmp_path):
    root = tmp_path / "projects"
    project = create_project(root, name="Exports")
    first = save_project_export(b"first", root=root, project_id=project.id, label="First", file_name="first.txt")
    second = save_project_export(b"second", root=root, project_id=project.id, label="Second", file_name="second.txt")

    removed = clear_project_exports(root, project.id)

    assert removed == 2
    assert list_project_exports(root, project.id) == ()
    assert not (root / project.id / "exports" / first.id).exists()
    assert not (root / project.id / "exports" / second.id).exists()
