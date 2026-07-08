from pathlib import Path

import pandas as pd

from core.storage_lifecycle import CacheManager, DeleteEngine, FileHandleManager, ResourceManager
from services.well_manager_service import WellManagerService


def _service(tmp_path: Path) -> WellManagerService:
    resource_manager = ResourceManager()
    cache_manager = CacheManager()
    file_handle_manager = FileHandleManager(resource_manager)
    delete_engine = DeleteEngine(
        resource_manager,
        cache_manager=cache_manager,
        file_handle_manager=file_handle_manager,
        attempts=1,
        delay_seconds=0,
    )
    return WellManagerService(
        tmp_path,
        resource_manager=resource_manager,
        cache_manager=cache_manager,
        file_handle_manager=file_handle_manager,
        delete_engine=delete_engine,
    )


def test_well_service_contract_aliases_remain_available(tmp_path: Path):
    service = _service(tmp_path)
    df = pd.DataFrame({"DEPT": [1.0], "GR": [10]})

    saved = service.save(df, well_name="Compat Well", version_label="v1", depth_column="DEPT").record

    assert service.list() == service.list_wells()
    assert service.list_records() == service.list_wells()
    assert service.load(saved.id).id == saved.id
    assert service.get(saved.id).id == saved.id
    assert service.read_bytes(saved.id, saved.versions[0].id, "csv")


def test_well_delete_releases_registered_resources_and_cache(tmp_path: Path):
    service = _service(tmp_path)
    df = pd.DataFrame({"DEPT": [1.0, 2.0], "GR": [10, 20]})
    record = service.save_version(df, well_name="Delete Well", version_label="v1", depth_column="DEPT").record
    version_id = record.versions[0].id

    service.register_well_file(record.id, version_id, "xlsx", description="preview workbook")
    service.register_well_cache("well-preview-cache", well_id=record.id, version_id=version_id)
    assert service.health().open_resources >= 1
    assert service.health().cache_entries >= 1

    result = service.delete_well(record.id)

    assert result.deleted is True
    assert result.released_resources >= 1
    assert service.list_wells() == ()
    assert service.health().open_resources == 0
    assert service.health().cache_entries == 0
    assert not (tmp_path / record.id).exists()


def test_well_version_delete_uses_lifecycle_and_deletes_empty_well(tmp_path: Path):
    service = _service(tmp_path)
    df = pd.DataFrame({"DEPT": [1.0], "GR": [10]})
    record = service.save_version(df, well_name="Last Version", version_label="v1", depth_column="DEPT").record
    version_id = record.versions[0].id
    service.register_well_cache("last-version-preview", well_id=record.id, version_id=version_id)

    result = service.delete_well_version(record.id, version_id)

    assert result.deleted is True
    assert result.well_deleted is True
    assert result.remaining_versions == 0
    assert service.list_wells() == ()
    assert service.health().cache_entries == 0
    assert not (tmp_path / record.id).exists()


def test_well_clear_removes_all_saved_wells(tmp_path: Path):
    service = _service(tmp_path)
    df = pd.DataFrame({"DEPT": [1.0], "GR": [10]})
    service.save_version(df, well_name="Well A", version_label="v1", depth_column="DEPT")
    service.save_version(df, well_name="Well B", version_label="v1", depth_column="DEPT")

    result = service.clear_all()

    assert result.deleted_count == 2
    assert service.list_wells() == ()
    assert not any(tmp_path.iterdir())
