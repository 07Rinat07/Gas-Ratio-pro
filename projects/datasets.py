from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from importers.csv_importer import read_csv
from projects.las_files import ProjectLasFile, list_project_las_files, read_project_las_file_dataframe
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

DEPTH_CURVE_CANDIDATES = ("DEPT", "DEPTH", "MD")
PROJECT_DATASETS_DIR_NAME = "datasets"
PROJECT_CSV_DATASETS_DIR_NAME = "csv"
PROJECT_CSV_DATASETS_MANIFEST_FILE_NAME = "csv_datasets.json"
PROJECT_CSV_SOURCE_FILE_NAME = "source.csv"
PROJECT_CSV_DATASETS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProjectCsvDataset:
    """Saved CSV dataset metadata for an active project."""

    id: str
    name: str
    original_file_name: str
    saved_at: str
    size_bytes: int
    row_count: int = 0
    column_count: int = 0
    well_id: str = ""
    archived_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDatasetRecord:
    """Compact project dataset card used by Dataset Manager.

    The card is intentionally metadata-oriented. For LAS and CSV datasets it
    reads only enough tabular information to show size, column names and basic
    readiness diagnostics. It does not duplicate source files during indexing and
    does not mutate saved datasets.
    """

    id: str
    kind: str
    name: str
    source_id: str
    well_id: str
    version_label: str
    original_file_name: str
    saved_at: str
    archived_at: str = ""
    row_count: int = 0
    column_count: int = 0
    depth_curve: str = ""
    curves: tuple[str, ...] = ()
    status: str = "ready"
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    @property
    def status_label(self) -> str:
        labels = {
            "ready": "готов",
            "warning": "требует проверки",
            "error": "ошибка чтения",
        }
        return labels.get(self.status, self.status)

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", value.strip()).strip("-").lower()
    return slug or "dataset"


def _safe_csv_dataset_id(value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", value):
        raise ValueError("Некорректный идентификатор CSV dataset проекта.")
    return value


def _safe_file_name(value: str) -> str:
    file_name = Path(str(value)).name.strip()
    if not file_name:
        return "source.csv"
    safe_name = re.sub(r"[^0-9A-Za-zА-Яа-я_.-]+", "_", file_name).strip("._")
    return safe_name or "source.csv"


def _csv_datasets_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_DATASETS_DIR_NAME / PROJECT_CSV_DATASETS_DIR_NAME


def _csv_manifest_path(root: Path | str, project_id: str) -> Path:
    return _csv_datasets_dir(root, project_id) / PROJECT_CSV_DATASETS_MANIFEST_FILE_NAME


def _csv_dataset_dir(root: Path | str, project_id: str, dataset_id: str) -> Path:
    return _csv_datasets_dir(root, project_id) / _safe_csv_dataset_id(dataset_id)


def _find_depth_curve(columns: tuple[str, ...]) -> str:
    by_upper = {column.upper(): column for column in columns}
    for candidate in DEPTH_CURVE_CANDIDATES:
        if candidate in by_upper:
            return by_upper[candidate]
    return ""


def _curve_names(dataframe: pd.DataFrame) -> tuple[str, ...]:
    return tuple(str(column) for column in dataframe.columns)


def _csv_record_from_dict(raw: dict[str, Any]) -> ProjectCsvDataset:
    return ProjectCsvDataset(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")) or "CSV dataset",
        original_file_name=str(raw.get("original_file_name", "")) or "source.csv",
        saved_at=str(raw.get("saved_at", "")),
        size_bytes=int(raw.get("size_bytes", 0) or 0),
        row_count=int(raw.get("row_count", 0) or 0),
        column_count=int(raw.get("column_count", 0) or 0),
        well_id=str(raw.get("well_id", "")),
        archived_at=str(raw.get("archived_at", "")),
        metadata=dict(raw.get("metadata", {}) or {}),
    )


def _csv_record_to_dict(record: ProjectCsvDataset) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "original_file_name": record.original_file_name,
        "saved_at": record.saved_at,
        "size_bytes": record.size_bytes,
        "row_count": record.row_count,
        "column_count": record.column_count,
        "well_id": record.well_id,
        "archived_at": record.archived_at,
        "metadata": dict(record.metadata),
    }


def _read_csv_manifest(root: Path | str, project_id: str) -> tuple[ProjectCsvDataset, ...]:
    path = _csv_manifest_path(root, project_id)
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("csv_datasets", ()) if isinstance(payload, dict) else ()
    return tuple(_csv_record_from_dict(record) for record in records)


def _write_csv_manifest(root: Path | str, project_id: str, records: tuple[ProjectCsvDataset, ...]) -> Path:
    path = _csv_manifest_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_CSV_DATASETS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "csv_datasets": [_csv_record_to_dict(record) for record in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _build_dataset_record_from_dataframe(
    *,
    dataset_id: str,
    kind: str,
    name: str,
    source_id: str,
    well_id: str,
    version_label: str,
    original_file_name: str,
    saved_at: str,
    archived_at: str,
    dataframe: pd.DataFrame | None,
    metadata: dict[str, Any] | None,
    missing_depth_warning: str,
    empty_rows_warning: str,
    empty_columns_warning: str,
    error: str = "",
) -> ProjectDatasetRecord:
    warnings: list[str] = []
    curves: tuple[str, ...] = ()
    row_count = 0
    column_count = 0
    depth_curve = ""
    status = "ready"

    if error:
        status = "error"
        warnings.append(error)
    elif dataframe is not None:
        curves = _curve_names(dataframe)
        row_count = int(len(dataframe))
        column_count = int(len(dataframe.columns))
        depth_curve = _find_depth_curve(curves)
        if row_count == 0:
            warnings.append(empty_rows_warning)
        if column_count == 0:
            warnings.append(empty_columns_warning)
        if not depth_curve:
            warnings.append(missing_depth_warning)
        duplicate_columns = tuple(column for column in curves if curves.count(column) > 1)
        if duplicate_columns:
            warnings.append("Найдены дублирующиеся колонки: " + ", ".join(sorted(set(duplicate_columns))[:8]) + ".")
        if warnings:
            status = "warning"
    else:
        status = "warning"
        warnings.append(f"Таблица {kind} не передана для проверки dataset-карточки.")

    return ProjectDatasetRecord(
        id=dataset_id,
        kind=kind,
        name=name,
        source_id=source_id,
        well_id=well_id,
        version_label=version_label,
        original_file_name=original_file_name,
        saved_at=saved_at,
        archived_at=archived_at,
        row_count=row_count,
        column_count=column_count,
        depth_curve=depth_curve,
        curves=curves,
        status=status,
        warnings=tuple(warnings),
        metadata=dict(metadata or {}),
    )


def build_project_las_dataset_record(
    record: ProjectLasFile,
    dataframe: pd.DataFrame | None = None,
    *,
    error: str = "",
) -> ProjectDatasetRecord:
    """Build a Dataset Manager card for one saved project LAS version."""

    return _build_dataset_record_from_dataframe(
        dataset_id=f"las:{record.id}",
        kind="LAS",
        name=f"{record.name} · {record.version_label}",
        source_id=record.id,
        well_id=record.well_id,
        version_label=record.version_label,
        original_file_name=record.original_file_name,
        saved_at=record.saved_at,
        archived_at=record.archived_at,
        dataframe=dataframe,
        metadata=dict(record.metadata or {}),
        missing_depth_warning="Не найдена глубинная кривая DEPT/DEPTH/MD.",
        empty_rows_warning="LAS dataset не содержит строк ASCII-данных.",
        empty_columns_warning="LAS dataset не содержит кривых.",
        error=error,
    )


def build_project_csv_dataset_record(
    record: ProjectCsvDataset,
    dataframe: pd.DataFrame | None = None,
    *,
    error: str = "",
) -> ProjectDatasetRecord:
    """Build a Dataset Manager card for one saved project CSV dataset."""

    return _build_dataset_record_from_dataframe(
        dataset_id=f"csv:{record.id}",
        kind="CSV",
        name=record.name,
        source_id=record.id,
        well_id=record.well_id,
        version_label="CSV",
        original_file_name=record.original_file_name,
        saved_at=record.saved_at,
        archived_at=record.archived_at,
        dataframe=dataframe,
        metadata=dict(record.metadata),
        missing_depth_warning="Не найдена глубинная колонка DEPT/DEPTH/MD.",
        empty_rows_warning="CSV dataset не содержит строк данных.",
        empty_columns_warning="CSV dataset не содержит колонок.",
        error=error,
    )


def save_project_csv_dataset(
    data: bytes,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    file_name: str = "source.csv",
    name: str = "",
    well_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> ProjectCsvDataset:
    """Save uploaded CSV bytes as a project dataset metadata record.

    The source CSV is stored once under ``datasets/csv/<dataset_id>/source.csv``.
    Only compact metadata is written to the manifest, which keeps Dataset Manager
    safe for large files and duplicate source names.
    """

    if not data:
        raise ValueError("Нет данных CSV для сохранения в проект.")

    safe_original_name = _safe_file_name(file_name)
    clean_name = name.strip() or Path(safe_original_name).stem or "CSV dataset"
    now = _utc_now()
    base_id = f"{now[:10].replace('-', '')}-csv-{_slugify(clean_name)}"
    dataset_id = base_id
    counter = 2
    while _csv_dataset_dir(root, project_id, dataset_id).exists():
        dataset_id = f"{base_id}-{counter}"
        counter += 1

    csv_dir = _csv_dataset_dir(root, project_id, dataset_id)
    csv_dir.mkdir(parents=True, exist_ok=True)
    (csv_dir / PROJECT_CSV_SOURCE_FILE_NAME).write_bytes(data)

    row_count = 0
    column_count = 0
    try:
        dataframe = read_csv(BytesIO(data))
    except Exception:
        pass
    else:
        row_count = int(len(dataframe))
        column_count = int(len(dataframe.columns))

    record = ProjectCsvDataset(
        id=dataset_id,
        name=clean_name,
        original_file_name=safe_original_name,
        saved_at=now,
        size_bytes=len(data),
        row_count=row_count,
        column_count=column_count,
        well_id=well_id.strip(),
        metadata=dict(metadata or {}),
    )
    records = (record, *tuple(item for item in _read_csv_manifest(root, project_id) if item.id != record.id))
    _write_csv_manifest(root, project_id, records)
    return record


def list_project_csv_records(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[ProjectCsvDataset, ...]:
    """Return saved CSV dataset metadata records for a project."""

    try:
        records = _read_csv_manifest(root, project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()
    if not include_archived:
        records = tuple(record for record in records if not record.archived_at)
    return tuple(sorted(records, key=lambda record: record.saved_at, reverse=True))


def read_project_csv_dataset_dataframe(
    root: Path | str,
    project_id: str,
    dataset_id: str,
) -> pd.DataFrame:
    """Read a saved project CSV dataset as a prepared dataframe."""

    records = {record.id: record for record in list_project_csv_records(root, project_id, include_archived=True)}
    if dataset_id not in records:
        raise FileNotFoundError(f"Project CSV dataset not found: {dataset_id}")
    return read_csv(_csv_dataset_dir(root, project_id, dataset_id) / PROJECT_CSV_SOURCE_FILE_NAME)


def list_project_las_datasets(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[ProjectDatasetRecord, ...]:
    """Return LAS dataset cards for the active project."""

    datasets: list[ProjectDatasetRecord] = []
    for record in list_project_las_files(root, project_id, include_archived=include_archived):
        try:
            dataframe = read_project_las_file_dataframe(root, project_id, record.id)
        except Exception as exc:  # pragma: no cover - exact parser errors vary by file
            datasets.append(
                build_project_las_dataset_record(
                    record,
                    error=f"Не удалось прочитать LAS: {exc}",
                )
            )
        else:
            datasets.append(build_project_las_dataset_record(record, dataframe))
    return tuple(datasets)


def list_project_csv_datasets(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[ProjectDatasetRecord, ...]:
    """Return CSV dataset cards for the active project.

    Broken CSV files are kept as ``error`` cards so the user can see and repair
    a problematic dataset instead of losing it from the overview.
    """

    datasets: list[ProjectDatasetRecord] = []
    for record in list_project_csv_records(root, project_id, include_archived=include_archived):
        try:
            dataframe = read_project_csv_dataset_dataframe(root, project_id, record.id)
        except Exception as exc:  # pragma: no cover - exact parser errors vary by file
            datasets.append(
                build_project_csv_dataset_record(
                    record,
                    error=f"Не удалось прочитать CSV: {exc}",
                )
            )
        else:
            datasets.append(build_project_csv_dataset_record(record, dataframe))
    return tuple(datasets)


def build_project_dataset_table(datasets: tuple[ProjectDatasetRecord, ...] | list[ProjectDatasetRecord]) -> pd.DataFrame:
    """Convert dataset cards to a small table for Streamlit and tests."""

    return pd.DataFrame(
        [
            {
                "Тип": dataset.kind,
                "Dataset": dataset.name,
                "Статус": dataset.status_label,
                "Скважина ID": dataset.well_id,
                "Источник ID": dataset.source_id,
                "Файл": dataset.original_file_name,
                "Строк": dataset.row_count,
                "Кривых": dataset.column_count,
                "Глубина": dataset.depth_curve,
                "Кривые": ", ".join(dataset.curves[:12]),
                "Предупреждения": "; ".join(dataset.warnings),
                "Сохранено": dataset.saved_at,
                "Архивировано": dataset.archived_at,
            }
            for dataset in datasets
        ]
    )
