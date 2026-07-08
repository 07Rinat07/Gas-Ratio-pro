from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.storage_lifecycle import DeleteEngine, DeleteResult, StorageDeleteError
from projects import datasets as project_datasets
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id


@dataclass(frozen=True)
class DatasetDeleteResult:
    project_id: str
    kind: str
    dataset_id: str
    deleted: bool
    diagnostic: str = ""


@dataclass(frozen=True)
class DatasetClearResult:
    project_id: str
    kind: str
    deleted_count: int
    diagnostic: str = ""


class DatasetManagerService:
    """Service-layer facade for Dataset Manager operations.

    UI code should call this service instead of deleting dataset folders or
    rewriting manifests directly.  The service routes destructive operations
    through Storage Lifecycle ``DeleteEngine`` so locked XLSX/CSV/LAS files are
    released/retried and reported consistently.
    """

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT, delete_engine: DeleteEngine | None = None) -> None:
        self.root = Path(root)
        self.delete_engine = delete_engine or DeleteEngine()

    def list_datasets(
        self,
        project_id: str,
        kind: str,
        *,
        include_archived: bool = False,
    ) -> tuple[project_datasets.ProjectDatasetRecord, ...]:
        clean_project_id = safe_project_id(project_id)
        normalized = self.normalize_kind(kind)
        if normalized == "LAS":
            return project_datasets.list_project_las_datasets(self.root, clean_project_id, include_archived=include_archived)
        if normalized == "CSV":
            return project_datasets.list_project_csv_datasets(self.root, clean_project_id, include_archived=include_archived)
        if normalized == "Excel":
            return project_datasets.list_project_excel_datasets(self.root, clean_project_id, include_archived=include_archived)
        if normalized == "Core":
            return project_datasets.list_project_core_datasets(self.root, clean_project_id, include_archived=include_archived)
        if normalized == "Mud Log":
            return project_datasets.list_project_mud_log_datasets(self.root, clean_project_id, include_archived=include_archived)
        if normalized == "Production":
            return project_datasets.list_project_production_datasets(self.root, clean_project_id, include_archived=include_archived)
        raise ValueError(f"Неизвестный Dataset section: {kind!r}.")

    def delete_dataset(self, project_id: str, kind: str, dataset_id: str) -> DatasetDeleteResult:
        clean_project_id = safe_project_id(project_id)
        normalized = self.normalize_kind(kind)
        try:
            project_datasets.delete_project_dataset(
                self.root,
                clean_project_id,
                normalized,
                dataset_id,
                delete_engine=self.delete_engine,
            )
        except StorageDeleteError as exc:
            return DatasetDeleteResult(clean_project_id, normalized, dataset_id, False, exc.result.diagnostic_message)
        return DatasetDeleteResult(clean_project_id, normalized, dataset_id, True, "Удалено.")

    def clear_section(self, project_id: str, kind: str) -> DatasetClearResult:
        clean_project_id = safe_project_id(project_id)
        normalized = self.normalize_kind(kind)
        try:
            deleted_count = project_datasets.clear_project_dataset_section(
                self.root,
                clean_project_id,
                normalized,
                delete_engine=self.delete_engine,
            )
        except StorageDeleteError as exc:
            return DatasetClearResult(clean_project_id, normalized, 0, exc.result.diagnostic_message)
        except ValueError as exc:
            return DatasetClearResult(clean_project_id, normalized, 0, str(exc))
        return DatasetClearResult(clean_project_id, normalized, deleted_count, f"Удалено записей: {deleted_count}.")

    def clear_all(self, project_id: str) -> DatasetClearResult:
        clean_project_id = safe_project_id(project_id)
        try:
            deleted_count = project_datasets.clear_project_all_dataset_sections(
                self.root,
                clean_project_id,
                delete_engine=self.delete_engine,
            )
        except StorageDeleteError as exc:
            return DatasetClearResult(clean_project_id, "ALL", 0, exc.result.diagnostic_message)
        return DatasetClearResult(clean_project_id, "ALL", deleted_count, f"Удалено записей: {deleted_count}.")

    @staticmethod
    def normalize_kind(kind: str) -> str:
        # Reuse repository normalizer through a harmless empty list attempt.
        value = str(kind).strip().lower().replace("_", " ").replace("-", " ")
        aliases = {
            "las": "LAS",
            "csv": "CSV",
            "excel": "Excel",
            "xlsx": "Excel",
            "core": "Core",
            "mud log": "Mud Log",
            "mudlog": "Mud Log",
            "production": "Production",
        }
        if value not in aliases:
            raise ValueError(f"Неизвестный раздел Dataset Manager: {kind!r}.")
        return aliases[value]
