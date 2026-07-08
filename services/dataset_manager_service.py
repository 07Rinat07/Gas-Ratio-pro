from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from projects.datasets import (
    ProjectDatasetRecord,
    clear_project_datasets,
    delete_project_dataset,
    list_project_core_datasets,
    list_project_csv_datasets,
    list_project_excel_datasets,
    list_project_las_datasets,
    list_project_mud_log_datasets,
    list_project_production_datasets,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id

DatasetKind = Literal["las", "csv", "excel", "core", "mud_log", "production"]
DATASET_KINDS: tuple[DatasetKind, ...] = ("las", "csv", "excel", "core", "mud_log", "production")


@dataclass(frozen=True)
class DatasetDeleteResult:
    project_id: str
    kind: str
    dataset_id: str
    deleted: bool


@dataclass(frozen=True)
class DatasetClearResult:
    project_id: str
    kind: str
    deleted_count: int


@dataclass(frozen=True)
class DatasetSummary:
    project_id: str
    total: int
    ready: int
    warning: int
    error: int
    by_kind: dict[str, int]


class DatasetManagerService:
    """High-level service for project Dataset Manager operations.

    UI code must use this service instead of manipulating dataset manifests and
    dataset folders directly.  The service provides the same lifecycle actions
    for LAS/CSV/Excel/Core/Mud Log/Production datasets.
    """

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT) -> None:
        self.root = Path(root)

    def list_datasets(
        self,
        project_id: str,
        *,
        kind: DatasetKind | str | None = None,
        include_archived: bool = False,
    ) -> tuple[ProjectDatasetRecord, ...]:
        clean_project_id = safe_project_id(project_id)
        if kind is None:
            records: list[ProjectDatasetRecord] = []
            for dataset_kind in DATASET_KINDS:
                records.extend(self.list_datasets(clean_project_id, kind=dataset_kind, include_archived=include_archived))
            return tuple(records)

        normalized_kind = self._normalize_kind(kind)
        if normalized_kind == "las":
            return list_project_las_datasets(self.root, clean_project_id, include_archived=include_archived)
        if normalized_kind == "csv":
            return list_project_csv_datasets(self.root, clean_project_id, include_archived=include_archived)
        if normalized_kind == "excel":
            return list_project_excel_datasets(self.root, clean_project_id, include_archived=include_archived)
        if normalized_kind == "core":
            return list_project_core_datasets(self.root, clean_project_id, include_archived=include_archived)
        if normalized_kind == "mud_log":
            return list_project_mud_log_datasets(self.root, clean_project_id, include_archived=include_archived)
        if normalized_kind == "production":
            return list_project_production_datasets(self.root, clean_project_id, include_archived=include_archived)
        raise ValueError(f"Неподдерживаемый тип dataset: {kind}")

    def delete_dataset(self, project_id: str, kind: DatasetKind | str, dataset_id: str) -> DatasetDeleteResult:
        clean_project_id = safe_project_id(project_id)
        normalized_kind = self._normalize_kind(kind)
        deleted = delete_project_dataset(self.root, clean_project_id, normalized_kind, dataset_id)
        return DatasetDeleteResult(clean_project_id, normalized_kind, dataset_id, deleted)

    def clear_section(self, project_id: str, kind: DatasetKind | str) -> DatasetClearResult:
        clean_project_id = safe_project_id(project_id)
        normalized_kind = self._normalize_kind(kind)
        deleted_count = clear_project_datasets(self.root, clean_project_id, kind=normalized_kind)
        return DatasetClearResult(clean_project_id, normalized_kind, deleted_count)

    def clear_all(self, project_id: str) -> DatasetClearResult:
        clean_project_id = safe_project_id(project_id)
        deleted_count = clear_project_datasets(self.root, clean_project_id, kind=None)
        return DatasetClearResult(clean_project_id, "all", deleted_count)

    def summarize(self, project_id: str, *, include_archived: bool = False) -> DatasetSummary:
        clean_project_id = safe_project_id(project_id)
        records = self.list_datasets(clean_project_id, include_archived=include_archived)
        by_kind = {kind: 0 for kind in DATASET_KINDS}
        for record in records:
            by_kind[record.kind] = by_kind.get(record.kind, 0) + 1
        return DatasetSummary(
            project_id=clean_project_id,
            total=len(records),
            ready=sum(1 for record in records if record.status == "ready"),
            warning=sum(1 for record in records if record.status == "warning"),
            error=sum(1 for record in records if record.status == "error"),
            by_kind=by_kind,
        )

    @staticmethod
    def _normalize_kind(kind: DatasetKind | str) -> DatasetKind:
        normalized = str(kind).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "mudlog": "mud_log",
            "mud_logs": "mud_log",
            "mud_log_dataset": "mud_log",
            "production_dataset": "production",
            "excel_dataset": "excel",
            "csv_dataset": "csv",
            "core_dataset": "core",
            "las_dataset": "las",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized not in DATASET_KINDS:
            raise ValueError(f"Неподдерживаемый тип dataset: {kind}")
        return normalized  # type: ignore[return-value]
