from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.storage_lifecycle import (
    CacheManager,
    DeleteEngine,
    FileHandleManager,
    ResourceManager,
    DEFAULT_CACHE_MANAGER,
    DEFAULT_DELETE_ENGINE,
    DEFAULT_FILE_HANDLE_MANAGER,
    DEFAULT_RESOURCE_MANAGER,
)
from typing import Any

import pandas as pd

from wells.repository import (
    DEFAULT_WELLS_ROOT,
    WellRecord,
    delete_well_record,
    delete_well_version,
    list_wells,
    load_well_record,
    read_well_file_bytes,
    save_well_version,
)

# Public service-layer storage constant for UI code.
# Streamlit shell must not import low-level well repository just to locate storage.
DEFAULT_WELLS_STORAGE_ROOT = DEFAULT_WELLS_ROOT


@dataclass(frozen=True)
class WellSaveResult:
    """Result of saving a well version through the service layer."""

    record: WellRecord

    def __getattr__(self, name: str):
        return getattr(self.record, name)


@dataclass(frozen=True)
class WellDeleteResult:
    """Result of deleting a complete well from persistent storage."""

    well_id: str
    deleted: bool
    released_resources: int = 0


@dataclass(frozen=True)
class WellVersionDeleteResult:
    """Result of deleting one version from a saved well."""

    well_id: str
    version_id: str
    deleted: bool
    well_deleted: bool
    remaining_versions: int
    record: WellRecord | None = None
    released_resources: int = 0


@dataclass(frozen=True)
class WellClearResult:
    deleted_count: int
    released_resources: int = 0


@dataclass(frozen=True)
class WellServiceHealth:
    open_resources: int
    cache_entries: int


class WellManagerService:
    """High-level well manager used by UI/controllers.

    Streamlit UI should not call the well repository directly for save/delete
    workflows. This service centralizes persistent well operations and returns
    explicit results that the UI can use for cleanup and user feedback.
    """

    def __init__(
        self,
        root: Path | str = DEFAULT_WELLS_ROOT,
        *,
        resource_manager: ResourceManager | None = None,
        cache_manager: CacheManager | None = None,
        file_handle_manager: FileHandleManager | None = None,
        delete_engine: DeleteEngine | None = None,
    ) -> None:
        self.root = Path(root)
        self.resource_manager = resource_manager or DEFAULT_RESOURCE_MANAGER
        self.cache_manager = cache_manager or DEFAULT_CACHE_MANAGER
        self.file_handle_manager = file_handle_manager or DEFAULT_FILE_HANDLE_MANAGER
        self.delete_engine = delete_engine or DEFAULT_DELETE_ENGINE

    def list_wells(self) -> tuple[WellRecord, ...]:
        return list_wells(self.root)

    def count_wells(self) -> int:
        return len(self.list_wells())

    def load_well(self, well_id: str) -> WellRecord:
        return load_well_record(self.root, well_id)

    def read_file_bytes(self, well_id: str, version_id: str, file_key: str) -> bytes:
        return read_well_file_bytes(self.root, well_id, version_id, file_key)

    def save_version(
        self,
        df: pd.DataFrame,
        *,
        well_name: str = "",
        well_id: str | None = None,
        area: str = "",
        status: str = "draft",
        comment: str = "",
        version_label: str = "prepared",
        kind: str = "prepared_las",
        depth_column: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WellSaveResult:
        record = save_well_version(
            df,
            root=self.root,
            well_name=well_name,
            well_id=well_id,
            area=area,
            status=status,
            comment=comment,
            version_label=version_label,
            kind=kind,
            depth_column=depth_column,
            metadata=metadata,
        )
        return WellSaveResult(record=record)

    def delete_well(self, well_id: str) -> WellDeleteResult:
        well_dir = self.root / str(well_id)
        released = self.file_handle_manager.release_path(well_dir)
        released += self.resource_manager.release_path(well_dir)
        released += self.cache_manager.clear_path(well_dir)
        deleted = delete_well_record(self.root, well_id)
        return WellDeleteResult(well_id=well_id, deleted=deleted, released_resources=released)

    def delete(self, well_id: str) -> WellDeleteResult:
        """Compatibility alias for delete_well()."""

        return self.delete_well(well_id)

    def delete_version(self, well_id: str, version_id: str) -> WellVersionDeleteResult:
        version_dir = self.root / str(well_id) / "versions" / str(version_id)
        released = self.file_handle_manager.release_path(version_dir)
        released += self.resource_manager.release_path(version_dir)
        released += self.cache_manager.clear_path(version_dir)
        updated_record = delete_well_version(self.root, well_id, version_id)
        remaining_versions = len(updated_record.versions)
        well_deleted = False
        record: WellRecord | None = updated_record

        if remaining_versions == 0:
            well_dir = self.root / str(well_id)
            released += self.file_handle_manager.release_path(well_dir)
            released += self.resource_manager.release_path(well_dir)
            released += self.cache_manager.clear_path(well_dir)
            well_deleted = delete_well_record(self.root, well_id)
            record = None

        return WellVersionDeleteResult(
            well_id=well_id,
            version_id=version_id,
            deleted=True,
            well_deleted=well_deleted,
            remaining_versions=remaining_versions,
            record=record,
            released_resources=released,
        )


def _well_service_save(self, df, **kwargs):
    return self.save_version(df, **kwargs)

def _well_service_list(self):
    return self.list_wells()

def _well_service_list_records(self):
    return self.list_wells()

def _well_service_load(self, well_id: str):
    return self.load_well(well_id)

def _well_service_get(self, well_id: str):
    return self.load_well(well_id)

def _well_service_read_bytes(self, well_id: str, version_id: str, file_key: str):
    return self.read_file_bytes(well_id, version_id, file_key)

def _well_service_delete_well_version(self, well_id: str, version_id: str):
    return self.delete_version(well_id, version_id)

def _well_service_register_well_file(self, well_id: str, version_id: str, file_key: str, *, description: str = "", owner: str = "WellManagerService"):
    record = self.load_well(well_id)
    version = next((item for item in record.versions if item.id == version_id), None)
    file_name = version.files.get(file_key, file_key) if version else file_key
    path = self.root / str(well_id) / "versions" / str(version_id) / file_name
    return self.file_handle_manager.register_file(path, owner=owner, resource_id=f"well:file:{well_id}:{version_id}:{file_key}", description=description)

def _well_service_register_well_cache(self, key: str, *, well_id: str, version_id: str = "", description: str = ""):
    path = self.root / str(well_id)
    if version_id:
        path = path / "versions" / str(version_id)
    return self.cache_manager.register(key, owner="WellManagerService", path=path, description=description)

def _well_service_health(self):
    return WellServiceHealth(
        open_resources=self.resource_manager.diagnostics().total,
        cache_entries=len(self.cache_manager.diagnostics()),
    )

def _well_service_clear_all(self):
    deleted = 0
    released = 0
    for record in tuple(self.list_wells()):
        result = self.delete_well(record.id)
        if result.deleted:
            deleted += 1
            released += result.released_resources
    return WellClearResult(deleted_count=deleted, released_resources=released)

WellManagerService.save = _well_service_save
WellManagerService.list = _well_service_list
WellManagerService.list_records = _well_service_list_records
WellManagerService.load = _well_service_load
WellManagerService.get = _well_service_get
WellManagerService.read_bytes = _well_service_read_bytes
WellManagerService.delete_well_version = _well_service_delete_well_version
WellManagerService.register_well_file = _well_service_register_well_file
WellManagerService.register_well_cache = _well_service_register_well_cache
WellManagerService.health = _well_service_health
WellManagerService.clear_all = _well_service_clear_all
