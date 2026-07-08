from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

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
    StorageDeleteError,
)
from projects import datasets as project_datasets
from projects import las_files as project_las_files
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

DatasetSection = Literal["las", "csv", "excel", "core", "mud_log", "production"]


@dataclass(frozen=True)
class DatasetSectionSpec:
    key: DatasetSection
    label: str
    folder_name: str
    manifest_name: str
    list_records: Callable[..., tuple[object, ...]]
    write_manifest: Callable[..., None]
    dataset_dir: Callable[[Path | str, str, str], Path]


@dataclass(frozen=True)
class DatasetDeleteSummary:
    project_id: str
    section: str
    requested: int
    deleted: int
    missing: int
    released_resources: int
    index_entries: int = 0


class DatasetManagerService:
    """Service layer for Dataset Manager storage lifecycle operations.

    The service is the only UI-facing entry point for destructive dataset
    operations.  It releases registered resources, removes files through
    ``DeleteEngine`` and updates dataset manifests so deleted records cannot
    reappear after Streamlit rerun or application restart.
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
        # Use process-wide lifecycle managers by default. Streamlit recreates
        # service objects on rerun, but registered previews/cache entries must
        # still be visible to delete/clear operations in the next run.
        self.resource_manager = resource_manager or DEFAULT_RESOURCE_MANAGER
        self.cache_manager = cache_manager or DEFAULT_CACHE_MANAGER
        self.file_handle_manager = file_handle_manager or DEFAULT_FILE_HANDLE_MANAGER
        self.delete_engine = delete_engine or DEFAULT_DELETE_ENGINE
        self.index_manager = index_manager or IndexManager(self.root)

    @property
    def section_specs(self) -> dict[str, DatasetSectionSpec]:
        return {
            "las": DatasetSectionSpec(
                key="las",
                label="LAS",
                folder_name=project_las_files.PROJECT_WELLS_DIR_NAME,
                manifest_name=project_las_files.PROJECT_LAS_MANIFEST_FILE_NAME,
                list_records=project_las_files.list_project_las_files,
                write_manifest=project_las_files._write_manifest,
                dataset_dir=project_las_files._las_file_dir,
            ),
            "csv": DatasetSectionSpec(
                key="csv",
                label="CSV",
                folder_name=project_datasets.PROJECT_CSV_DATASETS_DIR_NAME,
                manifest_name=project_datasets.PROJECT_CSV_DATASETS_MANIFEST_FILE_NAME,
                list_records=project_datasets.list_project_csv_records,
                write_manifest=project_datasets._write_csv_manifest,
                dataset_dir=project_datasets._csv_dataset_dir,
            ),
            "excel": DatasetSectionSpec(
                key="excel",
                label="Excel",
                folder_name=project_datasets.PROJECT_EXCEL_DATASETS_DIR_NAME,
                manifest_name=project_datasets.PROJECT_EXCEL_DATASETS_MANIFEST_FILE_NAME,
                list_records=project_datasets.list_project_excel_records,
                write_manifest=project_datasets._write_excel_manifest,
                dataset_dir=project_datasets._excel_dataset_dir,
            ),
            "core": DatasetSectionSpec(
                key="core",
                label="Core",
                folder_name=project_datasets.PROJECT_CORE_DATASETS_DIR_NAME,
                manifest_name=project_datasets.PROJECT_CORE_DATASETS_MANIFEST_FILE_NAME,
                list_records=project_datasets.list_project_core_records,
                write_manifest=project_datasets._write_core_manifest,
                dataset_dir=project_datasets._core_dataset_dir,
            ),
            "mud_log": DatasetSectionSpec(
                key="mud_log",
                label="Mud Log",
                folder_name=project_datasets.PROJECT_MUD_LOG_DATASETS_DIR_NAME,
                manifest_name=project_datasets.PROJECT_MUD_LOG_DATASETS_MANIFEST_FILE_NAME,
                list_records=project_datasets.list_project_mud_log_records,
                write_manifest=project_datasets._write_mud_log_manifest,
                dataset_dir=project_datasets._mud_log_dataset_dir,
            ),
            "production": DatasetSectionSpec(
                key="production",
                label="Production",
                folder_name=project_datasets.PROJECT_PRODUCTION_DATASETS_DIR_NAME,
                manifest_name=project_datasets.PROJECT_PRODUCTION_DATASETS_MANIFEST_FILE_NAME,
                list_records=project_datasets.list_project_production_records,
                write_manifest=project_datasets._write_production_manifest,
                dataset_dir=project_datasets._production_dataset_dir,
            ),
        }

    def _spec(self, section: str) -> DatasetSectionSpec:
        key = str(section).strip().lower().replace("-", "_").replace(" ", "_")
        specs = self.section_specs
        if key not in specs:
            raise ValueError(f"Unsupported Dataset Manager section: {section}")
        return specs[key]

    def datasets_root(self, project_id: str = DEFAULT_PROJECT_ID) -> Path:
        return self.root / safe_project_id(project_id) / project_datasets.PROJECT_DATASETS_DIR_NAME

    def section_dir(self, project_id: str, section: str) -> Path:
        spec = self._spec(section)
        if spec.key == "las":
            return project_las_files._project_wells_dir(self.root, project_id)
        return self.datasets_root(project_id) / spec.folder_name

    def supported_sections(self) -> tuple[str, ...]:
        """Return stable public Dataset Manager section keys used by UI."""

        return tuple(self.section_specs.keys())

    def section_label(self, section: str) -> str:
        """Return human-readable section label for compatibility/UI code."""

        return self._spec(section).label

    def is_supported_section(self, section: str) -> bool:
        """Return whether the section is managed by this service."""

        try:
            self._spec(section)
        except ValueError:
            return False
        return True

    def sync_project_index(self, project_id: str) -> IndexSyncResult:
        """Rebuild Project Database index after Dataset Manager changes."""

        return self.index_manager.sync_after_delete(project_id)

    def list_records(self, project_id: str, section: str, *, include_archived: bool = True) -> tuple[object, ...]:
        spec = self._spec(section)
        return spec.list_records(self.root, project_id, include_archived=include_archived)


    def list_dataset_cards(self, project_id: str, section: str, *, include_archived: bool = False) -> tuple[project_datasets.ProjectDatasetRecord, ...]:
        """Return UI-ready Dataset Manager cards for one section.

        This method is the service-layer replacement for direct UI calls to
        ``projects.datasets.list_project_*_datasets`` and keeps Dataset Manager
        rendering behind a stable service contract.
        """

        spec = self._spec(section)
        if spec.key == "las":
            return project_datasets.list_project_las_datasets(self.root, project_id, include_archived=include_archived)
        if spec.key == "csv":
            return project_datasets.list_project_csv_datasets(self.root, project_id, include_archived=include_archived)
        if spec.key == "excel":
            return project_datasets.list_project_excel_datasets(self.root, project_id, include_archived=include_archived)
        if spec.key == "core":
            return project_datasets.list_project_core_datasets(self.root, project_id, include_archived=include_archived)
        if spec.key == "mud_log":
            return project_datasets.list_project_mud_log_datasets(self.root, project_id, include_archived=include_archived)
        if spec.key == "production":
            return project_datasets.list_project_production_datasets(self.root, project_id, include_archived=include_archived)
        raise ValueError(f"Unsupported Dataset Manager section: {section}")

    def register_dataset_file(
        self,
        project_id: str,
        section: str,
        dataset_id: str,
        file_path: Path | str,
        *,
        owner: str = "Dataset Manager",
        description: str = "",
    ):
        """Register a file-backed Dataset resource before preview/import operations.

        UI code can call this when a Dataset file is opened for preview.  Later
        delete/clear operations release the same path through FileHandleManager,
        preventing Windows locked-file deletion errors where possible.
        """

        resource_id = f"dataset:{project_id}:{section}:{dataset_id}:{Path(file_path).name}"
        return self.file_handle_manager.register_file(
            file_path,
            owner=owner,
            resource_id=resource_id,
            description=description or f"Dataset {section}/{dataset_id}",
        )

    def register_dataset_cache(
        self,
        cache_key: str,
        *,
        owner: str = "Dataset Manager",
        path: Path | str | None = None,
        description: str = "",
    ):
        """Register a Dataset cache object for lifecycle cleanup."""

        return self.cache_manager.register(cache_key, owner=owner, path=path, description=description)

    def release_dataset_resources(self, project_id: str, section: str, dataset_id: str) -> int:
        """Release file handles and caches belonging to a Dataset folder."""

        dataset_path = self._spec(section).dataset_dir(self.root, project_id, dataset_id)
        released = self.file_handle_manager.release_path(dataset_path)
        released += self.resource_manager.release_path(dataset_path)
        released += self.cache_manager.clear_path(dataset_path)
        return released

    def delete_dataset(self, project_id: str, section: str, dataset_id: str) -> DatasetDeleteSummary:
        spec = self._spec(section)
        records = tuple(spec.list_records(self.root, project_id, include_archived=True))
        matching = [record for record in records if getattr(record, "id", "") == dataset_id]
        if not matching:
            return DatasetDeleteSummary(project_id=project_id, section=spec.key, requested=1, deleted=0, missing=1, released_resources=0)

        dataset_path = spec.dataset_dir(self.root, project_id, dataset_id)
        released_before = self.resource_manager.diagnostics().total
        released_explicit = self.release_dataset_resources(project_id, spec.key, dataset_id)
        self.delete_engine.delete_path(dataset_path, missing_ok=True)
        kept_records = tuple(record for record in records if getattr(record, "id", "") != dataset_id)
        spec.write_manifest(self.root, project_id, kept_records)
        index_result = self.sync_project_index(project_id)
        released_after = self.resource_manager.diagnostics().total
        return DatasetDeleteSummary(
            project_id=project_id,
            section=spec.key,
            requested=1,
            deleted=1,
            missing=0,
            released_resources=max(0, released_before - released_after) + released_explicit,
            index_entries=index_result.entries_count,
        )

    def delete_selected(self, project_id: str, section: str, dataset_ids: list[str] | tuple[str, ...]) -> DatasetDeleteSummary:
        spec = self._spec(section)
        requested_ids = tuple(str(item) for item in dataset_ids if str(item).strip())
        deleted = 0
        missing = 0
        released = 0
        for dataset_id in requested_ids:
            summary = self.delete_dataset(project_id, spec.key, dataset_id)
            deleted += summary.deleted
            missing += summary.missing
            released += summary.released_resources
        index_result = self.sync_project_index(project_id) if requested_ids else self.index_manager.validate_project_index(project_id)
        return DatasetDeleteSummary(
            project_id=project_id,
            section=spec.key,
            requested=len(requested_ids),
            deleted=deleted,
            missing=missing,
            released_resources=released,
            index_entries=index_result.entries_count,
        )

    def clear_section(self, project_id: str, section: str) -> DatasetDeleteSummary:
        spec = self._spec(section)
        records = tuple(spec.list_records(self.root, project_id, include_archived=True))
        section_path = self.section_dir(project_id, spec.key)
        released_before = self.resource_manager.diagnostics().total
        released_explicit = self.file_handle_manager.release_path(section_path)
        released_explicit += self.resource_manager.release_path(section_path)
        released_explicit += self.cache_manager.clear_path(section_path)
        delete_result: DeleteResult = self.delete_engine.delete_path(section_path, missing_ok=True)
        section_path.mkdir(parents=True, exist_ok=True)
        spec.write_manifest(self.root, project_id, ())
        index_result = self.sync_project_index(project_id)
        released_after = self.resource_manager.diagnostics().total
        return DatasetDeleteSummary(
            project_id=project_id,
            section=spec.key,
            requested=len(records),
            deleted=len(records) if delete_result.deleted or records else 0,
            missing=0,
            released_resources=max(0, released_before - released_after) + released_explicit + delete_result.released_resources,
            index_entries=index_result.entries_count,
        )

    def clear_all(self, project_id: str) -> DatasetDeleteSummary:
        requested = deleted = missing = released = 0
        for section in self.section_specs:
            try:
                summary = self.clear_section(project_id, section)
            except StorageDeleteError:
                raise
            requested += summary.requested
            deleted += summary.deleted
            missing += summary.missing
            released += summary.released_resources
        index_result = self.sync_project_index(project_id)
        return DatasetDeleteSummary(
            project_id=project_id,
            section="all",
            requested=requested,
            deleted=deleted,
            missing=missing,
            released_resources=released,
            index_entries=index_result.entries_count,
        )

    # Compatibility aliases used by older UI code during Sprint 1 migration.
    def delete(self, project_id: str, section: str, dataset_id: str) -> DatasetDeleteSummary:
        return self.delete_dataset(project_id, section, dataset_id)

    def clear(self, project_id: str, section: str) -> DatasetDeleteSummary:
        return self.clear_section(project_id, section)

    def refresh(self, project_id: str) -> IndexSyncResult:
        return self.sync_project_index(project_id)

    def diagnostics(self):
        return {
            "resources": self.resource_manager.diagnostics(),
            "file_handles": self.file_handle_manager.diagnostics(),
            "cache_entries": self.cache_manager.diagnostics(),
        }
