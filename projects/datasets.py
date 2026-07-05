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
from importers.excel_importer import load_excel_sheets, read_excel_sheet
from projects.las_files import ProjectLasFile, list_project_las_files, read_project_las_file_dataframe
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

DEPTH_CURVE_CANDIDATES = ("DEPT", "DEPTH", "MD")
PROJECT_DATASETS_DIR_NAME = "datasets"
PROJECT_CSV_DATASETS_DIR_NAME = "csv"
PROJECT_CSV_DATASETS_MANIFEST_FILE_NAME = "csv_datasets.json"
PROJECT_CSV_SOURCE_FILE_NAME = "source.csv"
PROJECT_CSV_DATASETS_SCHEMA_VERSION = 1
PROJECT_EXCEL_DATASETS_DIR_NAME = "excel"
PROJECT_EXCEL_DATASETS_MANIFEST_FILE_NAME = "excel_datasets.json"
PROJECT_EXCEL_SOURCE_FILE_NAME = "source.xlsx"
PROJECT_EXCEL_DATASETS_SCHEMA_VERSION = 1
PROJECT_CORE_DATASETS_DIR_NAME = "core"
PROJECT_CORE_DATASETS_MANIFEST_FILE_NAME = "core_datasets.json"
PROJECT_CORE_SOURCE_CSV_FILE_NAME = "source.csv"
PROJECT_CORE_SOURCE_EXCEL_FILE_NAME = "source.xlsx"
PROJECT_CORE_DATASETS_SCHEMA_VERSION = 1
CORE_MEASUREMENT_ALIASES = {
    "porosity": ("PHI", "POR", "PORO", "POROSITY"),
    "permeability": ("K", "PERM", "PERMEABILITY"),
    "grain_density": ("RHOG", "GRAIN_DENSITY", "GRAIN DENSITY"),
    "sample_id": ("SAMPLE", "SAMPLE_ID", "PLUG", "PLUG_ID", "CORE_ID"),
}


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
class ProjectExcelDataset:
    """Saved Excel dataset metadata for an active project."""

    id: str
    name: str
    original_file_name: str
    saved_at: str
    size_bytes: int
    sheet_count: int = 0
    active_sheet: str = ""
    row_count: int = 0
    column_count: int = 0
    well_id: str = ""
    archived_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)




@dataclass(frozen=True)
class ProjectCoreDataset:
    """Saved core laboratory dataset metadata for an active project."""

    id: str
    name: str
    original_file_name: str
    saved_at: str
    size_bytes: int
    file_format: str = "CSV"
    active_sheet: str = ""
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


def _safe_excel_dataset_id(value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", value):
        raise ValueError("Некорректный идентификатор Excel dataset проекта.")
    return value


def _excel_datasets_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_DATASETS_DIR_NAME / PROJECT_EXCEL_DATASETS_DIR_NAME


def _excel_manifest_path(root: Path | str, project_id: str) -> Path:
    return _excel_datasets_dir(root, project_id) / PROJECT_EXCEL_DATASETS_MANIFEST_FILE_NAME


def _excel_dataset_dir(root: Path | str, project_id: str, dataset_id: str) -> Path:
    return _excel_datasets_dir(root, project_id) / _safe_excel_dataset_id(dataset_id)



def _safe_core_dataset_id(value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", value):
        raise ValueError("Некорректный идентификатор Core dataset проекта.")
    return value


def _core_datasets_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_DATASETS_DIR_NAME / PROJECT_CORE_DATASETS_DIR_NAME


def _core_manifest_path(root: Path | str, project_id: str) -> Path:
    return _core_datasets_dir(root, project_id) / PROJECT_CORE_DATASETS_MANIFEST_FILE_NAME


def _core_dataset_dir(root: Path | str, project_id: str, dataset_id: str) -> Path:
    return _core_datasets_dir(root, project_id) / _safe_core_dataset_id(dataset_id)


def _core_source_file_name(original_file_name: str, file_format: str) -> str:
    suffix = Path(original_file_name).suffix.lower()
    if file_format.upper() == "EXCEL":
        if suffix in {".xlsx", ".xlsm", ".xls"}:
            return f"source{suffix}"
        return PROJECT_CORE_SOURCE_EXCEL_FILE_NAME
    return PROJECT_CORE_SOURCE_CSV_FILE_NAME


def _normalise_column_name(value: str) -> str:
    return re.sub(r"[^0-9A-Za-zА-Яа-я]+", "_", str(value).strip()).strip("_").upper()


def _core_measurement_columns(columns: tuple[str, ...]) -> tuple[str, ...]:
    depth_column = _find_depth_curve(columns)
    aliases = {alias for values in CORE_MEASUREMENT_ALIASES.values() for alias in values}
    measurements: list[str] = []
    for column in columns:
        normalized = _normalise_column_name(column)
        if column == depth_column or normalized in aliases:
            continue
        measurements.append(column)
    return tuple(measurements)


def _core_known_measurements(columns: tuple[str, ...]) -> tuple[str, ...]:
    normalized = {_normalise_column_name(column): column for column in columns}
    found: list[str] = []
    for label, aliases in CORE_MEASUREMENT_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            found.append(label)
    return tuple(found)


def _core_depth_range(dataframe: pd.DataFrame, depth_curve: str) -> tuple[float | None, float | None]:
    if not depth_curve or depth_curve not in dataframe.columns:
        return (None, None)
    values = pd.to_numeric(dataframe[depth_curve], errors="coerce").dropna()
    if values.empty:
        return (None, None)
    return (float(values.min()), float(values.max()))


def _excel_source_file_name(original_file_name: str) -> str:
    suffix = Path(original_file_name).suffix.lower()
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return f"source{suffix}"
    return PROJECT_EXCEL_SOURCE_FILE_NAME


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


def _excel_record_from_dict(raw: dict[str, Any]) -> ProjectExcelDataset:
    return ProjectExcelDataset(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")) or "Excel dataset",
        original_file_name=str(raw.get("original_file_name", "")) or "source.xlsx",
        saved_at=str(raw.get("saved_at", "")),
        size_bytes=int(raw.get("size_bytes", 0) or 0),
        sheet_count=int(raw.get("sheet_count", 0) or 0),
        active_sheet=str(raw.get("active_sheet", "")),
        row_count=int(raw.get("row_count", 0) or 0),
        column_count=int(raw.get("column_count", 0) or 0),
        well_id=str(raw.get("well_id", "")),
        archived_at=str(raw.get("archived_at", "")),
        metadata=dict(raw.get("metadata", {}) or {}),
    )


def _excel_record_to_dict(record: ProjectExcelDataset) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "original_file_name": record.original_file_name,
        "saved_at": record.saved_at,
        "size_bytes": record.size_bytes,
        "sheet_count": record.sheet_count,
        "active_sheet": record.active_sheet,
        "row_count": record.row_count,
        "column_count": record.column_count,
        "well_id": record.well_id,
        "archived_at": record.archived_at,
        "metadata": dict(record.metadata),
    }



def _core_record_from_dict(raw: dict[str, Any]) -> ProjectCoreDataset:
    return ProjectCoreDataset(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")) or "Core dataset",
        original_file_name=str(raw.get("original_file_name", "")) or "core.csv",
        saved_at=str(raw.get("saved_at", "")),
        size_bytes=int(raw.get("size_bytes", 0) or 0),
        file_format=str(raw.get("file_format", "CSV")) or "CSV",
        active_sheet=str(raw.get("active_sheet", "")),
        row_count=int(raw.get("row_count", 0) or 0),
        column_count=int(raw.get("column_count", 0) or 0),
        well_id=str(raw.get("well_id", "")),
        archived_at=str(raw.get("archived_at", "")),
        metadata=dict(raw.get("metadata", {}) or {}),
    )


def _core_record_to_dict(record: ProjectCoreDataset) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "original_file_name": record.original_file_name,
        "saved_at": record.saved_at,
        "size_bytes": record.size_bytes,
        "file_format": record.file_format,
        "active_sheet": record.active_sheet,
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


def _read_excel_manifest(root: Path | str, project_id: str) -> tuple[ProjectExcelDataset, ...]:
    path = _excel_manifest_path(root, project_id)
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("excel_datasets", ()) if isinstance(payload, dict) else ()
    return tuple(_excel_record_from_dict(record) for record in records)


def _write_excel_manifest(root: Path | str, project_id: str, records: tuple[ProjectExcelDataset, ...]) -> Path:
    path = _excel_manifest_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_EXCEL_DATASETS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "excel_datasets": [_excel_record_to_dict(record) for record in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path



def _read_core_manifest(root: Path | str, project_id: str) -> tuple[ProjectCoreDataset, ...]:
    path = _core_manifest_path(root, project_id)
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("core_datasets", ()) if isinstance(payload, dict) else ()
    return tuple(_core_record_from_dict(record) for record in records)


def _write_core_manifest(root: Path | str, project_id: str, records: tuple[ProjectCoreDataset, ...]) -> Path:
    path = _core_manifest_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_CORE_DATASETS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "core_datasets": [_core_record_to_dict(record) for record in records],
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


def build_project_excel_dataset_record(
    record: ProjectExcelDataset,
    dataframe: pd.DataFrame | None = None,
    *,
    error: str = "",
) -> ProjectDatasetRecord:
    """Build a Dataset Manager card for one saved project Excel dataset."""

    metadata = dict(record.metadata)
    if record.sheet_count:
        metadata.setdefault("sheet_count", record.sheet_count)
    if record.active_sheet:
        metadata.setdefault("active_sheet", record.active_sheet)

    dataset = _build_dataset_record_from_dataframe(
        dataset_id=f"excel:{record.id}",
        kind="Excel",
        name=record.name,
        source_id=record.id,
        well_id=record.well_id,
        version_label=record.active_sheet or "Excel",
        original_file_name=record.original_file_name,
        saved_at=record.saved_at,
        archived_at=record.archived_at,
        dataframe=dataframe,
        metadata=metadata,
        missing_depth_warning="Не найдена глубинная колонка DEPT/DEPTH/MD на активном листе Excel.",
        empty_rows_warning="Excel dataset не содержит строк данных на активном листе.",
        empty_columns_warning="Excel dataset не содержит колонок на активном листе.",
        error=error,
    )
    warnings = list(dataset.warnings)
    if not error and record.sheet_count == 0:
        warnings.append("Excel dataset не содержит листов для проверки.")
    if not error and not record.active_sheet:
        warnings.append("Для Excel dataset не задан активный лист.")
    if len(warnings) != len(dataset.warnings):
        status = "warning" if dataset.status == "ready" else dataset.status
        return ProjectDatasetRecord(
            **{**dataset.__dict__, "status": status, "warnings": tuple(warnings)}
        )
    return dataset



def build_project_core_dataset_record(
    record: ProjectCoreDataset,
    dataframe: pd.DataFrame | None = None,
    *,
    error: str = "",
) -> ProjectDatasetRecord:
    """Build a Dataset Manager card for one saved project Core dataset."""

    metadata = dict(record.metadata)
    if record.file_format:
        metadata.setdefault("file_format", record.file_format)
    if record.active_sheet:
        metadata.setdefault("active_sheet", record.active_sheet)

    dataset = _build_dataset_record_from_dataframe(
        dataset_id=f"core:{record.id}",
        kind="Core",
        name=record.name,
        source_id=record.id,
        well_id=record.well_id,
        version_label=record.active_sheet or record.file_format,
        original_file_name=record.original_file_name,
        saved_at=record.saved_at,
        archived_at=record.archived_at,
        dataframe=dataframe,
        metadata=metadata,
        missing_depth_warning="Не найдена глубинная колонка DEPT/DEPTH/MD для привязки core-образцов.",
        empty_rows_warning="Core dataset не содержит строк образцов.",
        empty_columns_warning="Core dataset не содержит колонок измерений.",
        error=error,
    )
    if error or dataframe is None:
        return dataset

    warnings = list(dataset.warnings)
    metadata = dict(dataset.metadata or {})
    columns = tuple(str(column) for column in dataframe.columns)
    depth_curve = dataset.depth_curve
    depth_min, depth_max = _core_depth_range(dataframe, depth_curve)
    measurement_columns = _core_measurement_columns(columns)
    known_measurements = _core_known_measurements(columns)
    metadata.update(
        {
            "sample_count": int(len(dataframe)),
            "depth_min": depth_min,
            "depth_max": depth_max,
            "measurement_columns": list(measurement_columns),
            "known_measurements": list(known_measurements),
        }
    )

    if depth_curve:
        depth_values = pd.to_numeric(dataframe[depth_curve], errors="coerce")
        if depth_values.isna().any():
            warnings.append("Глубинная колонка core содержит пустые или нечисловые значения.")
        duplicated_depths = depth_values.dropna()[depth_values.dropna().duplicated()]
        if not duplicated_depths.empty:
            warnings.append("Найдены дубли глубин core-образцов; проверьте повторные plug samples.")
    if not measurement_columns and not known_measurements:
        warnings.append("Не найдены измерительные колонки core, кроме глубины и идентификаторов образцов.")

    status = "warning" if warnings else "ready"
    return ProjectDatasetRecord(
        **{**dataset.__dict__, "status": status, "warnings": tuple(warnings), "metadata": metadata}
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


def save_project_excel_dataset(
    data: bytes,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    file_name: str = "source.xlsx",
    name: str = "",
    well_id: str = "",
    active_sheet: str = "",
    metadata: dict[str, Any] | None = None,
) -> ProjectExcelDataset:
    """Save uploaded Excel bytes as a project dataset metadata record.

    The workbook is stored once under ``datasets/excel/<dataset_id>/``. The
    manifest keeps only workbook metadata, sheet names and active-sheet summary
    so Dataset Manager can index Excel files without duplicating uploaded data.
    """

    if not data:
        raise ValueError("Нет данных Excel для сохранения в проект.")

    safe_original_name = _safe_file_name(file_name)
    clean_name = name.strip() or Path(safe_original_name).stem or "Excel dataset"
    now = _utc_now()
    base_id = f"{now[:10].replace('-', '')}-excel-{_slugify(clean_name)}"
    dataset_id = base_id
    counter = 2
    while _excel_dataset_dir(root, project_id, dataset_id).exists():
        dataset_id = f"{base_id}-{counter}"
        counter += 1

    excel_dir = _excel_dataset_dir(root, project_id, dataset_id)
    excel_dir.mkdir(parents=True, exist_ok=True)
    source_file_name = _excel_source_file_name(safe_original_name)
    (excel_dir / source_file_name).write_bytes(data)

    row_count = 0
    column_count = 0
    sheet_count = 0
    sheet_names: tuple[str, ...] = ()
    selected_sheet = active_sheet.strip()
    try:
        raw_sheets = load_excel_sheets(BytesIO(data))
    except Exception:
        raw_sheets = {}
    if raw_sheets:
        sheet_names = tuple(str(sheet_name) for sheet_name in raw_sheets)
        sheet_count = len(sheet_names)
        if not selected_sheet or selected_sheet not in raw_sheets:
            selected_sheet = sheet_names[0]
        try:
            dataframe = read_excel_sheet(BytesIO(data), selected_sheet)
        except Exception:
            dataframe = raw_sheets[selected_sheet]
        row_count = int(len(dataframe))
        column_count = int(len(dataframe.columns))

    clean_metadata = dict(metadata or {})
    clean_metadata["source_file_name"] = source_file_name
    clean_metadata["sheet_names"] = list(sheet_names)

    record = ProjectExcelDataset(
        id=dataset_id,
        name=clean_name,
        original_file_name=safe_original_name,
        saved_at=now,
        size_bytes=len(data),
        sheet_count=sheet_count,
        active_sheet=selected_sheet,
        row_count=row_count,
        column_count=column_count,
        well_id=well_id.strip(),
        metadata=clean_metadata,
    )
    records = (record, *tuple(item for item in _read_excel_manifest(root, project_id) if item.id != record.id))
    _write_excel_manifest(root, project_id, records)
    return record


def list_project_excel_records(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[ProjectExcelDataset, ...]:
    """Return saved Excel dataset metadata records for a project."""

    try:
        records = _read_excel_manifest(root, project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()
    if not include_archived:
        records = tuple(record for record in records if not record.archived_at)
    return tuple(sorted(records, key=lambda record: record.saved_at, reverse=True))


def read_project_excel_dataset_dataframe(
    root: Path | str,
    project_id: str,
    dataset_id: str,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    """Read a saved project Excel dataset active sheet as a prepared dataframe."""

    records = {record.id: record for record in list_project_excel_records(root, project_id, include_archived=True)}
    if dataset_id not in records:
        raise FileNotFoundError(f"Project Excel dataset not found: {dataset_id}")
    record = records[dataset_id]
    selected_sheet = sheet_name or record.active_sheet
    if not selected_sheet:
        raise ValueError("Для Excel dataset не задан активный лист.")
    source_file_name = str(record.metadata.get("source_file_name") or _excel_source_file_name(record.original_file_name))
    return read_excel_sheet(_excel_dataset_dir(root, project_id, dataset_id) / source_file_name, selected_sheet)



def save_project_core_dataset(
    data: bytes,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    file_name: str = "core.csv",
    name: str = "",
    well_id: str = "",
    active_sheet: str = "",
    metadata: dict[str, Any] | None = None,
) -> ProjectCoreDataset:
    """Save uploaded core laboratory data as a project dataset record.

    Core datasets may come from CSV or Excel workbooks. The source file is kept
    once under ``datasets/core/<dataset_id>/`` and the manifest stores compact
    metadata only: sample count, active sheet, column count and source format.
    """

    if not data:
        raise ValueError("Нет данных Core dataset для сохранения в проект.")

    safe_original_name = _safe_file_name(file_name)
    suffix = Path(safe_original_name).suffix.lower()
    file_format = "EXCEL" if suffix in {".xlsx", ".xlsm", ".xls"} else "CSV"
    clean_name = name.strip() or Path(safe_original_name).stem or "Core dataset"
    now = _utc_now()
    base_id = f"{now[:10].replace('-', '')}-core-{_slugify(clean_name)}"
    dataset_id = base_id
    counter = 2
    while _core_dataset_dir(root, project_id, dataset_id).exists():
        dataset_id = f"{base_id}-{counter}"
        counter += 1

    core_dir = _core_dataset_dir(root, project_id, dataset_id)
    core_dir.mkdir(parents=True, exist_ok=True)
    source_file_name = _core_source_file_name(safe_original_name, file_format)
    (core_dir / source_file_name).write_bytes(data)

    row_count = 0
    column_count = 0
    selected_sheet = active_sheet.strip()
    try:
        if file_format == "EXCEL":
            raw_sheets = load_excel_sheets(BytesIO(data))
            sheet_names = tuple(str(sheet_name) for sheet_name in raw_sheets)
            if sheet_names:
                if not selected_sheet or selected_sheet not in raw_sheets:
                    selected_sheet = sheet_names[0]
                dataframe = read_excel_sheet(BytesIO(data), selected_sheet)
            else:
                dataframe = pd.DataFrame()
        else:
            sheet_names = ()
            dataframe = read_csv(BytesIO(data))
    except Exception:
        sheet_names = ()
        dataframe = pd.DataFrame()
    row_count = int(len(dataframe))
    column_count = int(len(dataframe.columns))

    clean_metadata = dict(metadata or {})
    clean_metadata["source_file_name"] = source_file_name
    clean_metadata["sheet_names"] = list(sheet_names)

    record = ProjectCoreDataset(
        id=dataset_id,
        name=clean_name,
        original_file_name=safe_original_name,
        saved_at=now,
        size_bytes=len(data),
        file_format=file_format,
        active_sheet=selected_sheet,
        row_count=row_count,
        column_count=column_count,
        well_id=well_id.strip(),
        metadata=clean_metadata,
    )
    records = (record, *tuple(item for item in _read_core_manifest(root, project_id) if item.id != record.id))
    _write_core_manifest(root, project_id, records)
    return record


def list_project_core_records(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[ProjectCoreDataset, ...]:
    """Return saved Core dataset metadata records for a project."""

    try:
        records = _read_core_manifest(root, project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()
    if not include_archived:
        records = tuple(record for record in records if not record.archived_at)
    return tuple(sorted(records, key=lambda record: record.saved_at, reverse=True))


def read_project_core_dataset_dataframe(
    root: Path | str,
    project_id: str,
    dataset_id: str,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    """Read a saved project Core dataset as a prepared dataframe."""

    records = {record.id: record for record in list_project_core_records(root, project_id, include_archived=True)}
    if dataset_id not in records:
        raise FileNotFoundError(f"Project Core dataset not found: {dataset_id}")
    record = records[dataset_id]
    source_file_name = str(record.metadata.get("source_file_name") or _core_source_file_name(record.original_file_name, record.file_format))
    source_path = _core_dataset_dir(root, project_id, dataset_id) / source_file_name
    if record.file_format.upper() == "EXCEL":
        selected_sheet = sheet_name or record.active_sheet
        if not selected_sheet:
            raise ValueError("Для Core Excel dataset не задан активный лист.")
        return read_excel_sheet(source_path, selected_sheet)
    return read_csv(source_path)


def list_project_core_datasets(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[ProjectDatasetRecord, ...]:
    """Return Core dataset cards for the active project."""

    datasets: list[ProjectDatasetRecord] = []
    for record in list_project_core_records(root, project_id, include_archived=include_archived):
        try:
            dataframe = read_project_core_dataset_dataframe(root, project_id, record.id)
        except Exception as exc:  # pragma: no cover - exact parser errors vary by source file
            datasets.append(
                build_project_core_dataset_record(
                    record,
                    error=f"Не удалось прочитать Core dataset: {exc}",
                )
            )
        else:
            datasets.append(build_project_core_dataset_record(record, dataframe))
    return tuple(datasets)


def list_project_excel_datasets(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[ProjectDatasetRecord, ...]:
    """Return Excel dataset cards for the active project."""

    datasets: list[ProjectDatasetRecord] = []
    for record in list_project_excel_records(root, project_id, include_archived=include_archived):
        try:
            dataframe = read_project_excel_dataset_dataframe(root, project_id, record.id)
        except Exception as exc:  # pragma: no cover - exact parser errors vary by workbook
            datasets.append(
                build_project_excel_dataset_record(
                    record,
                    error=f"Не удалось прочитать Excel: {exc}",
                )
            )
        else:
            datasets.append(build_project_excel_dataset_record(record, dataframe))
    return tuple(datasets)


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
