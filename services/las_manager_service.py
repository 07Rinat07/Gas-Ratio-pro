from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.storage_lifecycle import (
    CacheManager,
    DeleteEngine,
    FileHandleManager,
    IndexManager,
    ResourceManager,
    DEFAULT_CACHE_MANAGER,
    DEFAULT_DELETE_ENGINE,
    DEFAULT_FILE_HANDLE_MANAGER,
    DEFAULT_RESOURCE_MANAGER,
)

from projects.las_files import (
    PROJECT_LAS_EXPORT_FORMATS,
    ProjectLasFile,
    ProjectLasWellCard,
    export_project_las_files_zip,
    list_project_las_files,
    list_project_las_wells,
    read_project_las_file_bytes,
    read_project_las_file_dataframe,
    save_project_las_file,
    _las_file_dir,
    _read_manifest,
    _write_manifest,
    set_project_las_file_archived,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id


@dataclass(frozen=True)
class LasSaveResult:
    """Result of saving a LAS file into project storage."""

    record: ProjectLasFile


@dataclass(frozen=True)
class LasDeleteResult:
    """Result of a physical LAS delete operation."""

    project_id: str
    las_file_id: str
    deleted: bool
    index_entries_count: int = 0
    released_resources: int = 0


@dataclass(frozen=True)
class LasArchiveResult:
    """Result of changing archive state for a LAS version."""

    project_id: str
    las_file_id: str
    archived: bool
    record: ProjectLasFile


@dataclass(frozen=True)
class LasClearResult:
    """Result of clearing all LAS versions from a project."""

    project_id: str
    deleted_count: int
    index_entries_count: int = 0
    released_resources: int = 0


class LasManagerService:
    """High-level service for project LAS versions.

    UI code should use this service instead of calling ``projects.las_files``
    functions directly.  This keeps all project LAS operations on the same
    service-layer path as Project/Well/Export management.
    """

    def __init__(
        self,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        *,
        delete_engine: DeleteEngine | None = None,
        index_manager: IndexManager | None = None,
        resource_manager: ResourceManager | None = None,
        cache_manager: CacheManager | None = None,
        file_handle_manager: FileHandleManager | None = None,
    ) -> None:
        self.root = Path(root)
        self.resource_manager = resource_manager or DEFAULT_RESOURCE_MANAGER
        self.cache_manager = cache_manager or DEFAULT_CACHE_MANAGER
        self.file_handle_manager = file_handle_manager or DEFAULT_FILE_HANDLE_MANAGER
        self.delete_engine = delete_engine or DEFAULT_DELETE_ENGINE
        self.index_manager = index_manager or IndexManager(self.root)

    def list_files(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasFile, ...]:
        return list_project_las_files(self.root, safe_project_id(project_id), include_archived=include_archived)

    def list_wells(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasWellCard, ...]:
        return list_project_las_wells(self.root, safe_project_id(project_id), include_archived=include_archived)

    def save_las_file(self, **kwargs) -> LasSaveResult:
        return self.save_file(**kwargs)

    def list_las_files(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasFile, ...]:
        return self.list_files(project_id, include_archived=include_archived)

    def clear_las_files(self, project_id: str, *, include_archived: bool = True) -> int:
        return self.clear_files(project_id, include_archived=include_archived).deleted_count

    def save_file(
        self,
        *,
        project_id: str,
        data: bytes,
        file_name: str = "source.las",
        well_name: str = "",
        version_label: str = "Исходный LAS",
        metadata: dict[str, Any] | None = None,
    ) -> LasSaveResult:
        clean_project_id = safe_project_id(project_id)
        record = save_project_las_file(
            data=data,
            root=self.root,
            project_id=clean_project_id,
            file_name=file_name,
            well_name=well_name,
            version_label=version_label,
            metadata=metadata,
        )
        self.index_manager.rebuild_project_index(clean_project_id)
        return LasSaveResult(record=record)

    def archive_file(self, project_id: str, las_file_id: str) -> LasArchiveResult:
        record = set_project_las_file_archived(self.root, safe_project_id(project_id), las_file_id, archived=True)
        return LasArchiveResult(project_id=safe_project_id(project_id), las_file_id=las_file_id, archived=True, record=record)

    def restore_file(self, project_id: str, las_file_id: str) -> LasArchiveResult:
        record = set_project_las_file_archived(self.root, safe_project_id(project_id), las_file_id, archived=False)
        return LasArchiveResult(project_id=safe_project_id(project_id), las_file_id=las_file_id, archived=False, record=record)

    def release_las_resources(self, project_id: str, las_file_id: str) -> int:
        clean_project_id = safe_project_id(project_id)
        las_dir = _las_file_dir(self.root, clean_project_id, las_file_id)
        released = self.file_handle_manager.release_path(las_dir)
        released += self.resource_manager.release_path(las_dir)
        released += self.cache_manager.clear_path(las_dir)
        return released

    def release_project_las_resources(self, project_id: str) -> int:
        clean_project_id = safe_project_id(project_id)
        project_las_dir = self.root / clean_project_id / "wells"
        released = self.file_handle_manager.release_path(project_las_dir)
        released += self.resource_manager.release_path(project_las_dir)
        released += self.cache_manager.clear_path(project_las_dir)
        return released

    def delete_file(self, project_id: str, las_file_id: str) -> LasDeleteResult:
        clean_project_id = safe_project_id(project_id)
        records = tuple(_read_manifest(self.root, clean_project_id))
        if not any(record.id == las_file_id for record in records):
            index_result = self.index_manager.validate_project_index(clean_project_id)
            return LasDeleteResult(
                project_id=clean_project_id,
                las_file_id=las_file_id,
                deleted=False,
                index_entries_count=index_result.entries_count,
            )

        released = self.release_las_resources(clean_project_id, las_file_id)
        las_dir = _las_file_dir(self.root, clean_project_id, las_file_id)
        delete_result = self.delete_engine.delete_path(las_dir, missing_ok=True)
        remaining = tuple(record for record in records if record.id != las_file_id)
        _write_manifest(self.root, clean_project_id, remaining)
        index_result = self.index_manager.sync_after_delete(clean_project_id)
        return LasDeleteResult(
            project_id=clean_project_id,
            las_file_id=las_file_id,
            deleted=delete_result.deleted,
            index_entries_count=index_result.entries_count,
            released_resources=released + delete_result.released_resources,
        )

    # Compatibility alias for older UI/tests.
    def delete(self, project_id: str, las_file_id: str) -> LasDeleteResult:
        return self.delete_file(project_id, las_file_id)

    def clear_files(self, project_id: str, *, include_archived: bool = True) -> LasClearResult:
        clean_project_id = safe_project_id(project_id)
        records = self.list_files(clean_project_id, include_archived=include_archived)
        deleted_count = 0
        released_total = self.release_project_las_resources(clean_project_id)
        for record in records:
            result = self.delete_file(clean_project_id, record.id)
            if result.deleted:
                deleted_count += 1
                released_total += result.released_resources
        index_result = self.index_manager.sync_after_delete(clean_project_id)
        return LasClearResult(
            project_id=clean_project_id,
            deleted_count=deleted_count,
            index_entries_count=index_result.entries_count,
            released_resources=released_total,
        )

    # Compatibility alias for older UI/tests.
    def clear(self, project_id: str, *, include_archived: bool = True) -> LasClearResult:
        return self.clear_files(project_id, include_archived=include_archived)

    def refresh(self, project_id: str):
        return self.index_manager.rebuild_project_index(safe_project_id(project_id))

    def read_bytes(self, project_id: str, las_file_id: str) -> bytes:
        return read_project_las_file_bytes(self.root, safe_project_id(project_id), las_file_id)

    def read_dataframe(self, project_id: str, las_file_id: str):
        return read_project_las_file_dataframe(self.root, safe_project_id(project_id), las_file_id)

    def export_zip(
        self,
        project_id: str,
        las_file_ids: tuple[str, ...] | list[str],
        formats: tuple[str, ...] | list[str] = PROJECT_LAS_EXPORT_FORMATS,
    ) -> bytes:
        return export_project_las_files_zip(self.root, safe_project_id(project_id), las_file_ids, formats=formats)
