from pathlib import Path

import pandas as pd

from services import ExportManagerService, LasManagerService, ProjectManagerService, WellManagerService
from widgets.common import table_toolbar_labels


def test_project_manager_service_creates_and_deletes_project(tmp_path: Path):
    service = ProjectManagerService(tmp_path)
    default_project = service.ensure_default()
    project = service.create_project("Sprint Project", "demo")

    assert project.id in {record.id for record in service.list_projects()}
    result = service.delete_project(project.id)

    assert result.deleted is True
    assert result.fallback_project_id == default_project.id
    assert project.id not in {record.id for record in service.list_projects()}


def test_export_manager_service_deletes_and_clears_files(tmp_path: Path):
    project_service = ProjectManagerService(tmp_path)
    project = project_service.create_project("Export Project")
    service = ExportManagerService(tmp_path)

    first = service.save_export(project_id=project.id, data=b"one", label="First", file_name="first.txt")
    second = service.save_export(project_id=project.id, data=b"two", label="Second", file_name="second.txt")

    assert service.delete_export(project.id, first.id).deleted is True
    assert [record.id for record in service.list_exports(project.id)] == [second.id]
    assert service.clear_exports(project.id).removed_count == 1
    assert service.list_exports(project.id) == ()


def test_well_manager_service_deletes_last_version_with_well(tmp_path: Path):
    service = WellManagerService(tmp_path)
    df = pd.DataFrame({"DEPT": [1.0], "GR": [10.0]})
    record = service.save_version(df, well_name="Well A", version_label="v1", depth_column="DEPT")

    result = service.delete_version(record.id, record.versions[0].id)
    assert result.deleted is True
    assert result.well_deleted is True
    assert service.list_wells() == ()


def test_las_manager_service_clears_project_las_files(tmp_path: Path):
    project = ProjectManagerService(tmp_path).create_project("LAS Project")
    service = LasManagerService(tmp_path)

    service.save_las_file(project_id=project.id, data=b"~Version\nVERS. 2.0\n", file_name="a.las", well_name="A")
    service.save_las_file(project_id=project.id, data=b"~Version\nVERS. 2.0\n", file_name="b.las", well_name="B")

    assert len(service.list_las_files(project.id)) == 2
    assert service.clear_las_files(project.id) == 2
    assert service.list_las_files(project.id) == ()


def test_common_table_toolbar_labels_are_shared():
    assert table_toolbar_labels() == ("Обновить", "Удалить выбранное", "Очистить список")
