from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from core.storage_lifecycle import DeleteEngine, DeleteResult, IndexManager, IndexSyncResult, ResourceManager, StorageDeleteError
from projects import datasets as project_datasets
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

DatasetSection = Literal["csv", "excel", "core", "mud_log", "production"]


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
    ) -> None:
        self.root = Path(root)
        self.resource_manager = resource_manager or ResourceManager()
        self.delete_engine = delete_engine or DeleteEngine(self.resource_manager)
        self.index_manager = index_manager or IndexManager(self.root)

    @property
    def section_specs(self) -> dict[str, DatasetSectionSpec]:
        return {
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

    def delete_dataset(self, project_id: str, section: str, dataset_id: str) -> DatasetDeleteSummary:
        spec = self._spec(section)
        records = tuple(spec.list_records(self.root, project_id, include_archived=True))
        matching = [record for record in records if getattr(record, "id", "") == dataset_id]
        if not matching:
            return DatasetDeleteSummary(project_id=project_id, section=spec.key, requested=1, deleted=0, missing=1, released_resources=0)

        dataset_path = spec.dataset_dir(self.root, project_id, dataset_id)
        released_before = self.resource_manager.diagnostics().total
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
            released_resources=max(0, released_before - released_after),
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
            released_resources=max(0, released_before - released_after) + delete_result.released_resources,
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

    def diagnostics(self):
        return self.resource_manager.diagnostics()
