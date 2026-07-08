from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from core.storage_lifecycle import (
    DEFAULT_CACHE_MANAGER,
    DEFAULT_DELETE_ENGINE,
    DEFAULT_FILE_HANDLE_MANAGER,
    DEFAULT_RESOURCE_MANAGER,
    CacheManager,
    DeleteEngine,
    DeleteResult,
    FileHandleManager,
    ResourceManager,
)
from wells.repository import (
    DEFAULT_WELLS_ROOT,
    WellRecord,
    _manifest_path,
    _utc_now,
    _well_dir,
    _write_record,
    list_wells,
    load_well_record,
    read_well_file_bytes,
    save_well_version,
)


@dataclass(frozen=True)
class WellSaveResult:
    """Result of saving a well version through the service layer."""

    record: WellRecord


@dataclass(frozen=True)
class WellDeleteResult:
    """Result of deleting a complete well from persistent storage."""

    well_id: str
    deleted: bool
    delete_result: DeleteResult | None = None
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
    delete_result: DeleteResult | None = None
    released_resources: int = 0


@dataclass(frozen=True)
class WellClearResult:
    """Result of clearing all saved wells."""

    deleted_count: int
    released_resources: int = 0


@dataclass(frozen=True)
class WellManagerHealth:
    """Small diagnostics DTO for saved well storage."""

    well_count: int
    version_count: int
    open_resources: int
    cache_entries: int


class WellManagerService:
    """High-level well manager used by UI/controllers.

    Public compatibility contract:
    - UI must use this service instead of calling ``wells.repository`` for
      save/delete workflows;
    - physical deletes go through Storage Lifecycle ``DeleteEngine``;
    - resources/cache/file handles are released before destructive operations;
    - repository functions remain responsible for manifest serialization and
      file reading/writing only.
    """

    def __init__(
        self,
        root: Path | str = DEFAULT_WELLS_ROOT,
        *,
        resource_manager: ResourceManager | None = None,
        delete_engine: DeleteEngine | None = None,
        cache_manager: CacheManager | None = None,
        file_handle_manager: FileHandleManager | None = None,
    ) -> None:
        self.root = Path(root)
        self.resource_manager = resource_manager or DEFAULT_RESOURCE_MANAGER
        self.cache_manager = cache_manager or DEFAULT_CACHE_MANAGER
        self.file_handle_manager = file_handle_manager or DEFAULT_FILE_HANDLE_MANAGER
        self.delete_engine = delete_engine or DEFAULT_DELETE_ENGINE

    @property
    def wells_root(self) -> Path:
        """Compatibility alias for UI/debug code."""

        return self.root

    def well_dir(self, well_id: str) -> Path:
        return _well_dir(self.root, well_id)

    def version_dir(self, well_id: str, version_id: str) -> Path:
        return self.well_dir(well_id) / "versions" / version_id

    def list_wells(self) -> tuple[WellRecord, ...]:
        return list_wells(self.root)

    # Compatibility aliases for older UI/tests.
    list = list_wells
    list_records = list_wells

    def count_wells(self) -> int:
        return len(self.list_wells())

    def load_well(self, well_id: str) -> WellRecord:
        return load_well_record(self.root, well_id)

    load = load_well
    get = load_well

    def read_file_bytes(self, well_id: str, version_id: str, file_key: str) -> bytes:
        return read_well_file_bytes(self.root, well_id, version_id, file_key)

    read_bytes = read_file_bytes

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

    save = save_version
    create_version = save_version

    def register_well_file(
        self,
        well_id: str,
        version_id: str,
        file_key: str,
        *,
        owner: str = "Well Manager",
        description: str = "",
    ) -> None:
        record = self.load_well(well_id)
        version = next((candidate for candidate in record.versions if candidate.id == version_id), None)
        if version is None:
            raise FileNotFoundError(f"Well version not found: {version_id}")
        file_name = version.files.get(file_key)
        if not file_name:
            raise FileNotFoundError(f"Well file not found for key: {file_key}")
        path = self.version_dir(well_id, version_id) / file_name
        self.file_handle_manager.register_file(
            path,
            owner=owner,
            resource_id=f"well-file:{well_id}:{version_id}:{file_key}",
            description=description or f"Saved well file {file_key}",
        )

    def register_well_cache(
        self,
        cache_key: str,
        *,
        owner: str = "Well Manager",
        well_id: str | None = None,
        version_id: str | None = None,
        description: str = "",
    ) -> None:
        path: Path | None = None
        if well_id and version_id:
            path = self.version_dir(well_id, version_id)
        elif well_id:
            path = self.well_dir(well_id)
        self.cache_manager.register(
            cache_key,
            owner=owner,
            path=path,
            description=description or "Saved well cache",
        )

    def release_well_resources(self, well_id: str, version_id: str | None = None) -> int:
        path = self.version_dir(well_id, version_id) if version_id else self.well_dir(well_id)
        released = self.file_handle_manager.release_path(path)
        released += self.resource_manager.release_path(path)
        self.cache_manager.clear_path(path)
        return released

    def delete_well(self, well_id: str) -> WellDeleteResult:
        well_dir = self.well_dir(well_id)
        released = self.release_well_resources(well_id)
        delete_result = self.delete_engine.delete_path(well_dir, missing_ok=True)
        return WellDeleteResult(
            well_id=well_id,
            deleted=delete_result.deleted,
            delete_result=delete_result,
            released_resources=released + delete_result.released_resources,
        )

    # Compatibility aliases.
    delete = delete_well
    remove_well = delete_well
    delete_record = delete_well

    def delete_version(self, well_id: str, version_id: str) -> WellVersionDeleteResult:
        record = self.load_well(well_id)
        remaining_versions = [version for version in record.versions if version.id != version_id]
        if len(remaining_versions) == len(record.versions):
            raise FileNotFoundError(f"Well version not found: {version_id}")

        version_dir = self.version_dir(well_id, version_id)
        released = self.release_well_resources(well_id, version_id)
        delete_result = self.delete_engine.delete_path(version_dir, missing_ok=True)

        updated_record = WellRecord(
            id=record.id,
            name=record.name,
            area=record.area,
            status=record.status,
            comment=record.comment,
            created_at=record.created_at,
            updated_at=_utc_now(),
            versions=tuple(remaining_versions),
        )

        well_deleted = False
        persisted_record: WellRecord | None = updated_record
        if remaining_versions:
            _write_record(self.root, updated_record)
        else:
            well_deleted = True
            # Delete the remaining manifest/well directory through lifecycle as
            # well. The version directory may already be gone; deleting the parent
            # guarantees an empty well cannot reappear after restart.
            parent_result = self.delete_engine.delete_path(self.well_dir(well_id), missing_ok=True)
            released += parent_result.released_resources
            persisted_record = None

        return WellVersionDeleteResult(
            well_id=well_id,
            version_id=version_id,
            deleted=True,
            well_deleted=well_deleted,
            remaining_versions=len(remaining_versions),
            record=persisted_record,
            delete_result=delete_result,
            released_resources=released + delete_result.released_resources,
        )

    delete_well_version = delete_version
    remove_version = delete_version
    delete_version_record = delete_version

    def clear_wells(self) -> WellClearResult:
        deleted_count = 0
        released_resources = 0
        for record in self.list_wells():
            result = self.delete_well(record.id)
            if result.deleted:
                deleted_count += 1
            released_resources += result.released_resources
        return WellClearResult(deleted_count=deleted_count, released_resources=released_resources)

    clear = clear_wells
    clear_all = clear_wells

    def refresh(self) -> tuple[WellRecord, ...]:
        return self.list_wells()

    def health(self) -> WellManagerHealth:
        records = self.list_wells()
        version_count = sum(len(record.versions) for record in records)
        return WellManagerHealth(
            well_count=len(records),
            version_count=version_count,
            open_resources=self.resource_manager.diagnostics().total,
            cache_entries=len(self.cache_manager.diagnostics()),
        )

    def diagnostics(self) -> dict[str, object]:
        return {
            "wells_root": self.root,
            "well_count": self.count_wells(),
            "resources": self.resource_manager.diagnostics(),
            "file_handles": self.file_handle_manager.diagnostics(),
            "cache_entries": self.cache_manager.diagnostics(),
        }
