from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.storage_lifecycle import (
    DEFAULT_CACHE_MANAGER,
    DEFAULT_DELETE_ENGINE,
    DEFAULT_FILE_HANDLE_MANAGER,
    DEFAULT_RESOURCE_MANAGER,
    CacheManager,
    DeleteEngine,
    DeleteResult,
    FileHandleManager,
    IndexManager,
    IndexSyncResult,
    ResourceManager,
)
from projects.las_files import (
    PROJECT_LAS_EXPORT_FORMATS,
    ProjectLasFile,
    ProjectLasWellCard,
    export_project_las_files_zip,
    list_project_las_files,
    list_project_las_wells,
    project_las_file_dir,
    project_las_source_path,
    read_project_las_file_bytes,
    read_project_las_file_dataframe,
    remove_project_las_file_record,
    save_project_las_file,
    set_project_las_file_archived,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id


@dataclass(frozen=True)
class LasSaveResult:
    """Result of saving a LAS file into project storage."""

    record: ProjectLasFile
    index_sync: IndexSyncResult | None = None


@dataclass(frozen=True)
class LasDeleteResult:
    """Result of a lifecycle-managed physical LAS delete operation."""

    project_id: str
    las_file_id: str
    deleted: bool
    delete_result: DeleteResult | None = None
    released_resources: int = 0
    index_sync: IndexSyncResult | None = None


@dataclass(frozen=True)
class LasArchiveResult:
    """Result of changing archive state for a LAS version."""

    project_id: str
    las_file_id: str
    archived: bool
    record: ProjectLasFile
    index_sync: IndexSyncResult | None = None


@dataclass(frozen=True)
class LasClearResult:
    """Result of clearing all LAS versions from a project."""

    project_id: str
    deleted_count: int
    released_resources: int = 0
    index_sync: IndexSyncResult | None = None


@dataclass(frozen=True)
class LasManagerHealth:
    """Small service diagnostics DTO used by UI/developer tools."""

    project_id: str
    file_count: int
    well_count: int
    open_resources: int
    cache_entries: int


class LasManagerService:
    """High-level service for project LAS versions.

    Public compatibility contract:
    - UI must use this service instead of calling ``projects.las_files`` for
      project LAS operations;
    - physical deletes go through Storage Lifecycle ``DeleteEngine``;
    - resource/cache release happens before destructive filesystem operations;
    - Project Database index is synchronized after save/archive/delete/clear.
    """

    def __init__(
        self,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        *,
        resource_manager: ResourceManager | None = None,
        delete_engine: DeleteEngine | None = None,
        index_manager: IndexManager | None = None,
        cache_manager: CacheManager | None = None,
        file_handle_manager: FileHandleManager | None = None,
    ) -> None:
        self.root = Path(root)
        self.resource_manager = resource_manager or DEFAULT_RESOURCE_MANAGER
        self.cache_manager = cache_manager or DEFAULT_CACHE_MANAGER
        self.file_handle_manager = file_handle_manager or DEFAULT_FILE_HANDLE_MANAGER
        self.delete_engine = delete_engine or DEFAULT_DELETE_ENGINE
        self.index_manager = index_manager or IndexManager(self.root)

    @property
    def projects_root(self) -> Path:
        """Compatibility alias for older UI/debug code."""

        return self.root

    @property
    def export_formats(self) -> tuple[str, ...]:
        """Supported project LAS export formats."""

        return PROJECT_LAS_EXPORT_FORMATS

    def las_dir(self, project_id: str, las_file_id: str) -> Path:
        return project_las_file_dir(self.root, safe_project_id(project_id), las_file_id)

    def source_path(self, project_id: str, las_file_id: str) -> Path:
        return project_las_source_path(self.root, safe_project_id(project_id), las_file_id)

    def list_files(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasFile, ...]:
        return list_project_las_files(self.root, safe_project_id(project_id), include_archived=include_archived)

    # Compatibility aliases used by older UI code during Sprint 1 migration.
    list = list_files
    list_las_files = list_files

    def list_wells(self, project_id: str, *, include_archived: bool = False) -> tuple[ProjectLasWellCard, ...]:
        return list_project_las_wells(self.root, safe_project_id(project_id), include_archived=include_archived)

    list_las_wells = list_wells

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
        index_sync = self._sync_index_if_possible(clean_project_id)
        return LasSaveResult(record=record, index_sync=index_sync)

    save = save_file
    create = save_file

    def archive_file(self, project_id: str, las_file_id: str) -> LasArchiveResult:
        clean_project_id = safe_project_id(project_id)
        record = set_project_las_file_archived(self.root, clean_project_id, las_file_id, archived=True)
        index_sync = self._sync_index_if_possible(clean_project_id)
        return LasArchiveResult(
            project_id=clean_project_id,
            las_file_id=las_file_id,
            archived=True,
            record=record,
            index_sync=index_sync,
        )

    archive = archive_file

    def restore_file(self, project_id: str, las_file_id: str) -> LasArchiveResult:
        clean_project_id = safe_project_id(project_id)
        record = set_project_las_file_archived(self.root, clean_project_id, las_file_id, archived=False)
        index_sync = self._sync_index_if_possible(clean_project_id)
        return LasArchiveResult(
            project_id=clean_project_id,
            las_file_id=las_file_id,
            archived=False,
            record=record,
            index_sync=index_sync,
        )

    restore = restore_file

    def register_las_file(
        self,
        project_id: str,
        las_file_id: str,
        *,
        owner: str = "LAS Manager",
        description: str = "",
    ):
        """Register a file-backed LAS resource before preview/read operations."""

        source = self.source_path(project_id, las_file_id)
        return self.file_handle_manager.register_file(
            source,
            owner=owner,
            resource_id=f"las:{safe_project_id(project_id)}:{las_file_id}:source",
            description=description or f"LAS source {las_file_id}",
        )

    def register_las_cache(
        self,
        cache_key: str,
        *,
        owner: str = "LAS Manager",
        path: Path | str | None = None,
        description: str = "",
    ):
        """Register a LAS cache object for lifecycle cleanup."""

        return self.cache_manager.register(cache_key, owner=owner, path=path, description=description)

    def release_las_resources(self, project_id: str, las_file_id: str) -> int:
        """Release file handles/resources/caches belonging to one LAS version."""

        target_dir = self.las_dir(project_id, las_file_id)
        released = self.file_handle_manager.release_path(target_dir)
        released += self.resource_manager.release_path(target_dir)
        released += self.cache_manager.clear_path(target_dir)
        return released

    def delete_file(self, project_id: str, las_file_id: str) -> LasDeleteResult:
        clean_project_id = safe_project_id(project_id)
        records = {record.id: record for record in self.list_files(clean_project_id, include_archived=True)}
        if las_file_id not in records:
            return LasDeleteResult(project_id=clean_project_id, las_file_id=las_file_id, deleted=False)

        target_dir = self.las_dir(clean_project_id, las_file_id)
        released = self.release_las_resources(clean_project_id, las_file_id)
        delete_result = self.delete_engine.delete_path(target_dir, missing_ok=True)
        removed = remove_project_las_file_record(self.root, clean_project_id, las_file_id)
        index_sync = self._sync_index_if_possible(clean_project_id)
        return LasDeleteResult(
            project_id=clean_project_id,
            las_file_id=las_file_id,
            deleted=removed,
            delete_result=delete_result,
            released_resources=released + delete_result.released_resources,
            index_sync=index_sync,
        )

    delete = delete_file
    remove_file = delete_file

    def clear_files(self, project_id: str, *, include_archived: bool = True) -> LasClearResult:
        clean_project_id = safe_project_id(project_id)
        records = self.list_files(clean_project_id, include_archived=include_archived)
        deleted_count = 0
        released = 0
        for record in records:
            result = self.delete_file(clean_project_id, record.id)
            if result.deleted:
                deleted_count += 1
            released += result.released_resources
        index_sync = self._sync_index_if_possible(clean_project_id)
        return LasClearResult(project_id=clean_project_id, deleted_count=deleted_count, released_resources=released, index_sync=index_sync)

    clear = clear_files
    clear_all = clear_files

    def read_bytes(self, project_id: str, las_file_id: str) -> bytes:
        return read_project_las_file_bytes(self.root, safe_project_id(project_id), las_file_id)

    def read_dataframe(self, project_id: str, las_file_id: str):
        clean_project_id = safe_project_id(project_id)
        self.register_las_file(clean_project_id, las_file_id, owner="LAS DataFrame Preview")
        self.register_las_cache(
            f"las-dataframe:{clean_project_id}:{las_file_id}",
            owner="LAS DataFrame Preview",
            path=self.las_dir(clean_project_id, las_file_id),
            description="Project LAS dataframe preview",
        )
        return read_project_las_file_dataframe(self.root, clean_project_id, las_file_id)

    def export_zip(
        self,
        project_id: str,
        las_file_ids: tuple[str, ...] | list[str],
        formats: tuple[str, ...] | list[str] = PROJECT_LAS_EXPORT_FORMATS,
    ) -> bytes:
        return export_project_las_files_zip(self.root, safe_project_id(project_id), las_file_ids, formats=formats)

    export = export_zip

    def rebuild_index(self, project_id: str) -> IndexSyncResult:
        return self.index_manager.rebuild_project_index(safe_project_id(project_id))

    def validate_index(self, project_id: str) -> IndexSyncResult:
        return self.index_manager.validate_project_index(safe_project_id(project_id))

    def health(self, project_id: str) -> LasManagerHealth:
        clean_project_id = safe_project_id(project_id)
        return LasManagerHealth(
            project_id=clean_project_id,
            file_count=len(self.list_files(clean_project_id, include_archived=True)),
            well_count=len(self.list_wells(clean_project_id, include_archived=True)),
            open_resources=self.resource_manager.diagnostics().total,
            cache_entries=len(self.cache_manager.diagnostics()),
        )

    def diagnostics(self) -> dict[str, object]:
        return {
            "resources": self.resource_manager.diagnostics(),
            "file_handles": self.file_handle_manager.diagnostics(),
            "cache_entries": self.cache_manager.diagnostics(),
        }

    def _sync_index_if_possible(self, project_id: str) -> IndexSyncResult | None:
        try:
            return self.index_manager.rebuild_project_index(safe_project_id(project_id))
        except (FileNotFoundError, OSError, ValueError):
            return None
