from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

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
from projects.exports import (
    PROJECT_EXPORTS_DIR_NAME,
    PROJECT_EXPORTS_MANIFEST_FILE_NAME,
    ProjectExportRecord,
    list_project_exports,
    read_project_export_file_bytes,
    save_project_export,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id


@dataclass(frozen=True)
class ExportSaveResult:
    """Result of saving one project export through the service layer."""

    record: ProjectExportRecord


@dataclass(frozen=True)
class ExportDeleteResult:
    """Result of deleting one export from project storage."""

    project_id: str
    export_id: str
    deleted: bool
    index_entries_count: int = 0
    released_resources: int = 0


@dataclass(frozen=True)
class ExportClearResult:
    """Result of clearing all exports from one project."""

    project_id: str
    removed_count: int
    index_entries_count: int = 0
    released_resources: int = 0


class ExportManagerService:
    """High-level export manager used by UI/controllers.

    The Streamlit UI must not manipulate export manifests, export folders or
    filesystem objects directly.  This service is the public compatibility
    boundary for project exports and routes destructive operations through the
    Storage Lifecycle Framework: file handles/resources are released, cache is
    cleared, paths are removed by ``DeleteEngine`` and the project index is
    synchronized through ``IndexManager``.
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

    # ------------------------------------------------------------------
    # Public read/list contract
    # ------------------------------------------------------------------
    def list_exports(self, project_id: str) -> tuple[ProjectExportRecord, ...]:
        return list_project_exports(self.root, safe_project_id(project_id))

    # Compatibility alias for older UI/tests.
    def list(self, project_id: str) -> tuple[ProjectExportRecord, ...]:
        return self.list_exports(project_id)

    def count_exports(self, project_id: str) -> int:
        return len(self.list_exports(project_id))

    # Compatibility alias for older UI/tests.
    def count(self, project_id: str) -> int:
        return self.count_exports(project_id)

    def read_export_bytes(self, project_id: str, export_id: str) -> bytes:
        return read_project_export_file_bytes(self.root, safe_project_id(project_id), export_id)

    # Compatibility alias for older UI/tests.
    def read_bytes(self, project_id: str, export_id: str) -> bytes:
        return self.read_export_bytes(project_id, export_id)

    # ------------------------------------------------------------------
    # Public write/delete contract
    # ------------------------------------------------------------------
    def save_export(
        self,
        *,
        project_id: str,
        data: bytes,
        label: str,
        file_name: str,
        mime_type: str,
        kind: str,
        source: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ExportSaveResult:
        clean_project_id = safe_project_id(project_id)
        record = save_project_export(
            data,
            root=self.root,
            project_id=clean_project_id,
            label=label,
            file_name=file_name,
            mime_type=mime_type,
            kind=kind,
            source=source,
            metadata=metadata,
        )
        self.index_manager.rebuild_project_index(clean_project_id)
        return ExportSaveResult(record=record)

    def delete_export(self, project_id: str, export_id: str) -> ExportDeleteResult:
        clean_project_id = safe_project_id(project_id)
        records = self.list_exports(clean_project_id)
        if not any(record.id == export_id for record in records):
            index_result = self.index_manager.validate_project_index(clean_project_id)
            return ExportDeleteResult(
                project_id=clean_project_id,
                export_id=export_id,
                deleted=False,
                index_entries_count=index_result.entries_count,
            )

        export_dir = self._export_dir(clean_project_id, export_id)
        self.release_export_resources(clean_project_id, export_id)
        delete_result = self.delete_engine.delete_path(export_dir, missing_ok=True)
        filtered = tuple(record for record in records if record.id != export_id)
        self._write_manifest(clean_project_id, filtered)
        index_result = self.index_manager.sync_after_delete(clean_project_id)
        return ExportDeleteResult(
            project_id=clean_project_id,
            export_id=export_id,
            deleted=delete_result.deleted,
            index_entries_count=index_result.entries_count,
            released_resources=delete_result.released_resources,
        )

    # Compatibility alias for older UI/tests.
    def delete(self, project_id: str, export_id: str) -> ExportDeleteResult:
        return self.delete_export(project_id, export_id)

    def clear_exports(self, project_id: str) -> ExportClearResult:
        clean_project_id = safe_project_id(project_id)
        records = self.list_exports(clean_project_id)
        released_total = self.release_project_export_resources(clean_project_id)
        exports_dir = self._exports_dir(clean_project_id)
        delete_result = self.delete_engine.delete_path(exports_dir, missing_ok=True)
        self._write_manifest(clean_project_id, ())
        index_result = self.index_manager.sync_after_delete(clean_project_id)
        return ExportClearResult(
            project_id=clean_project_id,
            removed_count=len(records),
            index_entries_count=index_result.entries_count,
            released_resources=released_total + delete_result.released_resources,
        )

    # Compatibility alias for older UI/tests.
    def clear(self, project_id: str) -> ExportClearResult:
        return self.clear_exports(project_id)

    def refresh(self, project_id: str) -> tuple[ProjectExportRecord, ...]:
        """Compatibility refresh hook used by repository-backed UI panels."""

        clean_project_id = safe_project_id(project_id)
        self.index_manager.rebuild_project_index(clean_project_id)
        return self.list_exports(clean_project_id)

    # ------------------------------------------------------------------
    # Storage lifecycle registration/release helpers
    # ------------------------------------------------------------------
    def register_export_file(
        self,
        project_id: str,
        export_id: str,
        path: Path | str,
        *,
        owner: str = "ExportManagerService",
        description: str = "project export file",
    ) -> None:
        clean_project_id = safe_project_id(project_id)
        resource_id = f"export:file:{clean_project_id}:{export_id}:{Path(path).name}"
        self.file_handle_manager.register_file(
            path,
            owner=owner,
            resource_id=resource_id,
            description=description,
        )

    def register_export_cache(
        self,
        project_id: str,
        export_id: str,
        *,
        key: str | None = None,
        description: str = "project export cache",
    ) -> None:
        clean_project_id = safe_project_id(project_id)
        cache_key = key or f"export:cache:{clean_project_id}:{export_id}"
        self.cache_manager.register(
            cache_key,
            owner="ExportManagerService",
            path=self._export_dir(clean_project_id, export_id),
            description=description,
        )

    def release_export_resources(self, project_id: str, export_id: str) -> int:
        clean_project_id = safe_project_id(project_id)
        export_dir = self._export_dir(clean_project_id, export_id)
        released = self.file_handle_manager.release_path(export_dir)
        released += self.resource_manager.release_path(export_dir)
        released += self.cache_manager.clear_path(export_dir)
        return released

    def release_project_export_resources(self, project_id: str) -> int:
        exports_dir = self._exports_dir(safe_project_id(project_id))
        released = self.file_handle_manager.release_path(exports_dir)
        released += self.resource_manager.release_path(exports_dir)
        released += self.cache_manager.clear_path(exports_dir)
        return released

    # ------------------------------------------------------------------
    # Internal manifest/path helpers
    # ------------------------------------------------------------------
    def _exports_dir(self, project_id: str) -> Path:
        return self.root / safe_project_id(project_id) / PROJECT_EXPORTS_DIR_NAME

    def _export_dir(self, project_id: str, export_id: str) -> Path:
        return self._exports_dir(project_id) / self._safe_export_id(export_id)

    def _manifest_path(self, project_id: str) -> Path:
        return self._exports_dir(project_id) / PROJECT_EXPORTS_MANIFEST_FILE_NAME

    def _write_manifest(self, project_id: str, records: Iterable[ProjectExportRecord]) -> Path:
        import json
        from datetime import datetime, timezone

        path = self._manifest_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "project_id": safe_project_id(project_id),
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "exports": [
                {
                    "id": record.id,
                    "label": record.label,
                    "kind": record.kind,
                    "file_name": record.file_name,
                    "mime_type": record.mime_type,
                    "saved_at": record.saved_at,
                    "size_bytes": record.size_bytes,
                    "source": record.source,
                    "metadata": record.metadata,
                }
                for record in records
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def _safe_export_id(value: str) -> str:
        import re

        clean_value = str(value)
        if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", clean_value):
            raise ValueError("Некорректный идентификатор экспорта проекта.")
        return clean_value
