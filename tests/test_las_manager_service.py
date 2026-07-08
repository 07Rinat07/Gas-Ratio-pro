from __future__ import annotations

from pathlib import Path

from services.las_manager_service import LasManagerService


SIMPLE_LAS = b"""~Version Information\nVERS. 2.0 : CWLS LOG ASCII STANDARD - VERSION 2.0\nWRAP. NO  : ONE LINE PER DEPTH STEP\n~Well Information\nSTRT.M 1000.0 : START DEPTH\nSTOP.M 1001.0 : STOP DEPTH\nSTEP.M 0.5 : STEP\nNULL. -999.25 : NULL VALUE\nWELL. Test Well : WELL\n~Curve Information\nDEPT.M : DEPTH\nGR.API : GAMMA RAY\n~ASCII\n1000.0 45.0\n1000.5 46.0\n1001.0 47.0\n"""


def test_las_manager_service_save_list_read_export_and_delete(tmp_path: Path) -> None:
    service = LasManagerService(tmp_path)

    saved = service.save_file(
        project_id="demo-project",
        data=SIMPLE_LAS,
        file_name="test.las",
        well_name="Test Well",
        version_label="Raw LAS",
    ).record

    assert saved.id
    assert saved.name == "Test Well"
    assert service.count_files("demo-project") == 1
    assert service.list_files("demo-project")[0].id == saved.id
    assert service.list_wells("demo-project")[0].versions[0].id == saved.id
    assert service.read_file_bytes("demo-project", saved.id) == SIMPLE_LAS

    dataframe = service.read_dataframe("demo-project", saved.id)
    assert list(dataframe.columns) == ["DEPT", "GR"]
    assert len(dataframe) == 3

    archive = service.archive_file("demo-project", saved.id)
    assert archive.archived is True
    assert service.count_files("demo-project") == 0
    assert service.count_files("demo-project", include_archived=True) == 1

    restored = service.restore_file("demo-project", saved.id)
    assert restored.archived is False
    assert service.count_files("demo-project") == 1

    export_result = service.export_zip("demo-project", [saved.id], ["las"])
    assert export_result.project_id == "demo-project"
    assert export_result.las_file_ids == (saved.id,)
    assert export_result.data.startswith(b"PK")

    deleted = service.delete_file("demo-project", saved.id)
    assert deleted.deleted is True
    assert service.count_files("demo-project", include_archived=True) == 0
    assert not (tmp_path / "demo-project" / "wells" / saved.id).exists()


def test_las_manager_service_delete_missing_returns_false(tmp_path: Path) -> None:
    service = LasManagerService(tmp_path)

    result = service.delete_file("demo-project", "missing-las")

    assert result.deleted is False
