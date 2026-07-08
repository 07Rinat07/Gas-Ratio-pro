from pathlib import Path

import pandas as pd

from services.well_manager_service import WellManagerService


def test_well_manager_service_saves_and_reads_well_version(tmp_path: Path):
    service = WellManagerService(tmp_path)
    df = pd.DataFrame({"DEPT": [1000.0, 1000.5], "GR": [45.0, 46.0]})

    result = service.save_version(df, well_name="Well A", version_label="prepared", depth_column="DEPT")

    assert result.record.id
    assert service.count_wells() == 1
    assert service.read_file_bytes(result.record.id, result.record.versions[0].id, "csv")


def test_well_manager_service_deletes_single_version_without_reappearing(tmp_path: Path):
    service = WellManagerService(tmp_path)
    df = pd.DataFrame({"DEPT": [1.0, 2.0], "GR": [10, 20]})
    first = service.save_version(df, well_name="Well B", version_label="v1", depth_column="DEPT").record
    second = service.save_version(df, well_id=first.id, well_name="Well B", version_label="v2", depth_column="DEPT").record

    deleted_version_id = second.versions[0].id
    result = service.delete_version(second.id, deleted_version_id)

    assert result.deleted is True
    assert result.well_deleted is False
    records = service.list_wells()
    assert len(records) == 1
    assert len(records[0].versions) == 1
    assert records[0].versions[0].id != deleted_version_id
    assert not (tmp_path / second.id / "versions" / deleted_version_id).exists()


def test_well_manager_service_deletes_empty_well_after_last_version(tmp_path: Path):
    service = WellManagerService(tmp_path)
    df = pd.DataFrame({"DEPT": [1.0], "GR": [10]})
    record = service.save_version(df, well_name="Well C", version_label="v1", depth_column="DEPT").record

    result = service.delete_version(record.id, record.versions[0].id)

    assert result.deleted is True
    assert result.well_deleted is True
    assert service.list_wells() == ()
    assert not (tmp_path / record.id).exists()


def test_well_manager_service_deletes_complete_well_directory(tmp_path: Path):
    service = WellManagerService(tmp_path)
    df = pd.DataFrame({"DEPT": [1.0], "GR": [10]})
    record = service.save_version(df, well_name="Well D", version_label="v1", depth_column="DEPT").record

    result = service.delete_well(record.id)

    assert result.deleted is True
    assert service.list_wells() == ()
    assert not (tmp_path / record.id).exists()
