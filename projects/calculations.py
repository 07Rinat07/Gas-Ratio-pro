from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from reports.export_csv import export_csv_bytes
from reports.export_xlsx import export_xlsx_bytes


PROJECT_CALCULATIONS_DIR_NAME = "calculations"
PROJECT_CALCULATIONS_MANIFEST_FILE_NAME = "calculations.json"
PROJECT_CALCULATION_METADATA_FILE_NAME = "metadata.json"
PROJECT_CALCULATION_CSV_FILE_NAME = "calculation.csv"
PROJECT_CALCULATION_XLSX_FILE_NAME = "calculation.xlsx"
PROJECT_CALCULATIONS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProjectCalculationRecord:
    id: str
    source_label: str
    sheet_name: str
    saved_at: str
    row_count: int
    ch_mode: str = ""
    warnings_count: int = 0
    files: dict[str, str] = field(default_factory=dict)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", value.strip()).strip("-").lower()
    return slug or "calculation"


def _safe_calculation_id(value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", value):
        raise ValueError("Некорректный идентификатор расчета проекта.")
    return value


def _calculations_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_CALCULATIONS_DIR_NAME


def _manifest_path(root: Path | str, project_id: str) -> Path:
    return _calculations_dir(root, project_id) / PROJECT_CALCULATIONS_MANIFEST_FILE_NAME


def _calculation_dir(root: Path | str, project_id: str, calculation_id: str) -> Path:
    return _calculations_dir(root, project_id) / _safe_calculation_id(calculation_id)


def _record_from_dict(raw: dict[str, Any]) -> ProjectCalculationRecord:
    return ProjectCalculationRecord(
        id=str(raw.get("id", "")),
        source_label=str(raw.get("source_label", "")) or "Расчет",
        sheet_name=str(raw.get("sheet_name", "")),
        saved_at=str(raw.get("saved_at", "")),
        row_count=int(raw.get("row_count", 0) or 0),
        ch_mode=str(raw.get("ch_mode", "")),
        warnings_count=int(raw.get("warnings_count", 0) or 0),
        files=dict(raw.get("files", {})),
    )


def _record_to_dict(record: ProjectCalculationRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "source_label": record.source_label,
        "sheet_name": record.sheet_name,
        "saved_at": record.saved_at,
        "row_count": record.row_count,
        "ch_mode": record.ch_mode,
        "warnings_count": record.warnings_count,
        "files": record.files,
    }


def _read_manifest(root: Path | str, project_id: str) -> tuple[ProjectCalculationRecord, ...]:
    path = _manifest_path(root, project_id)
    if not path.exists():
        return ()

    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("calculations", ()) if isinstance(payload, dict) else ()
    return tuple(_record_from_dict(record) for record in records)


def _write_manifest(root: Path | str, project_id: str, records: tuple[ProjectCalculationRecord, ...]) -> Path:
    path = _manifest_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_CALCULATIONS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "calculations": [_record_to_dict(record) for record in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_project_calculations(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectCalculationRecord, ...]:
    try:
        records = _read_manifest(root, project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()
    return tuple(sorted(records, key=lambda record: record.saved_at, reverse=True))


def save_project_calculation(
    df: pd.DataFrame,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    source_label: str = "Расчет",
    sheet_name: str = "",
    mapping: dict[str, str] | None = None,
    ch_mode: str = "",
    warnings: tuple[str, ...] | list[str] | None = None,
    header_row: int | None = None,
) -> ProjectCalculationRecord:
    if df is None or df.empty:
        raise ValueError("Нет расчетных данных для сохранения в проект.")

    clean_source_label = source_label.strip() or "Расчет"
    clean_sheet_name = sheet_name.strip()
    warning_items = tuple(dict.fromkeys(str(warning) for warning in (warnings or ()) if str(warning)))
    now = _utc_now()
    base_id = f"{now[:10].replace('-', '')}-{_slugify(clean_source_label)}-{_slugify(clean_sheet_name)}"
    calculation_id = base_id
    counter = 2
    while _calculation_dir(root, project_id, calculation_id).exists():
        calculation_id = f"{base_id}-{counter}"
        counter += 1

    calculation_dir = _calculation_dir(root, project_id, calculation_id)
    calculation_dir.mkdir(parents=True, exist_ok=True)
    (calculation_dir / PROJECT_CALCULATION_CSV_FILE_NAME).write_bytes(export_csv_bytes(df))
    (calculation_dir / PROJECT_CALCULATION_XLSX_FILE_NAME).write_bytes(
        export_xlsx_bytes(df, sheet_name="calculation")
    )

    metadata = {
        "source_label": clean_source_label,
        "sheet_name": clean_sheet_name,
        "mapping": mapping or {},
        "ch_mode": ch_mode,
        "warnings": list(warning_items),
        "header_row": header_row,
        "saved_at": now,
        "row_count": int(len(df)),
        "columns": [str(column) for column in df.columns],
    }
    (calculation_dir / PROJECT_CALCULATION_METADATA_FILE_NAME).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    record = ProjectCalculationRecord(
        id=calculation_id,
        source_label=clean_source_label,
        sheet_name=clean_sheet_name,
        saved_at=now,
        row_count=int(len(df)),
        ch_mode=ch_mode,
        warnings_count=len(warning_items),
        files={
            "csv": PROJECT_CALCULATION_CSV_FILE_NAME,
            "xlsx": PROJECT_CALCULATION_XLSX_FILE_NAME,
            "metadata": PROJECT_CALCULATION_METADATA_FILE_NAME,
        },
    )
    records = (record, *tuple(item for item in _read_manifest(root, project_id) if item.id != record.id))
    _write_manifest(root, project_id, records)
    return record


def read_project_calculation_file_bytes(
    root: Path | str,
    project_id: str,
    calculation_id: str,
    file_key: str,
) -> bytes:
    records = {record.id: record for record in list_project_calculations(root, project_id)}
    if calculation_id not in records:
        raise FileNotFoundError(f"Project calculation not found: {calculation_id}")
    file_name = records[calculation_id].files.get(file_key)
    if not file_name:
        raise FileNotFoundError(f"Project calculation file not found for key: {file_key}")
    return (_calculation_dir(root, project_id, calculation_id) / Path(file_name).name).read_bytes()


def read_project_calculation_dataframe(
    root: Path | str,
    project_id: str,
    calculation_id: str,
) -> pd.DataFrame:
    return pd.read_csv(BytesIO(read_project_calculation_file_bytes(root, project_id, calculation_id, "csv")))


def read_project_calculation_metadata(
    root: Path | str,
    project_id: str,
    calculation_id: str,
) -> dict[str, Any]:
    data = read_project_calculation_file_bytes(root, project_id, calculation_id, "metadata")
    return json.loads(data.decode("utf-8"))
