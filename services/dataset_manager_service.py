from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from core.storage_lifecycle import CacheManager, DeleteEngine, DeleteResult, FileHandleManager, IndexManager, IndexSyncResult, ResourceManager, StorageDeleteError
from projects import datasets as project_datasets
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from services.las_manager_service import LasManagerService

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
        self.resource_manager = resource_manager or ResourceManager()
        self.cache_manager = cache_manager or CacheManager()
        self.file_handle_manager = file_handle_manager or FileHandleManager(self.resource_manager)
        self.delete_engine = delete_engine or DeleteEngine(
            self.resource_manager,
            cache_manager=self.cache_manager,
            file_handle_manager=self.file_handle_manager,
        )
        self.index_manager = index_manager or IndexManager(self.root)
        self.las_manager = LasManagerService(
            self.root,
            delete_engine=self.delete_engine,
            index_manager=self.index_manager,
            resource_manager=self.resource_manager,
            cache_manager=self.cache_manager,
            file_handle_manager=self.file_handle_manager,
        )

    @property
    def section_specs(self) -> dict[str, DatasetSectionSpec]:
        return {
            "las": DatasetSectionSpec(
                key="las",
                label="LAS",
                folder_name="wells",
                manifest_name="las_files.json",
                list_records=project_datasets.list_project_las_datasets,
                write_manifest=lambda *_args, **_kwargs: None,
                dataset_dir=lambda root, project_id, dataset_id: Path(root) / safe_project_id(project_id) / "wells" / str(dataset_id),
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
        return self.datasets_root(project_id) / spec.folder_name

    def sync_project_index(self, project_id: str) -> IndexSyncResult:
        """Rebuild Project Database index after Dataset Manager changes."""

        return self.index_manager.sync_after_delete(project_id)

    def list_records(self, project_id: str, section: str, *, include_archived: bool = True) -> tuple[object, ...]:
        spec = self._spec(section)
        return spec.list_records(self.root, project_id, include_archived=include_archived)

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
        if str(section).strip().lower().replace("-", "_").replace(" ", "_") == "las":
            result = self.las_manager.delete_file(project_id, dataset_id)
            return DatasetDeleteSummary(
                project_id=safe_project_id(project_id),
                section="las",
                requested=1,
                deleted=1 if result.deleted else 0,
                missing=0 if result.deleted else 1,
                released_resources=result.released_resources,
                index_entries=result.index_entries_count,
            )
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
        if str(section).strip().lower().replace("-", "_").replace(" ", "_") == "las":
            records = self.las_manager.list_files(project_id, include_archived=True)
            result = self.las_manager.clear_files(project_id, include_archived=True)
            return DatasetDeleteSummary(
                project_id=safe_project_id(project_id),
                section="las",
                requested=len(records),
                deleted=result.deleted_count,
                missing=0,
                released_resources=result.released_resources,
                index_entries=result.index_entries_count,
            )
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

    def delete(self, project_id: str, section: str, dataset_id: str) -> DatasetDeleteSummary:
        """Compatibility alias for older UI code."""

        return self.delete_dataset(project_id, section, dataset_id)

    def clear(self, project_id: str, section: str | None = None) -> DatasetDeleteSummary:
        """Compatibility alias for clearing one section or all Dataset sections."""

        if section is None:
            return self.clear_all(project_id)
        return self.clear_section(project_id, section)

    def refresh(self, project_id: str) -> IndexSyncResult:
        """Compatibility alias for Project Database index synchronization."""

        return self.sync_project_index(project_id)

    def diagnostics(self):
        return {
            "resources": self.resource_manager.diagnostics(),
            "file_handles": self.file_handle_manager.diagnostics(),
            "cache_entries": self.cache_manager.diagnostics(),
        }
