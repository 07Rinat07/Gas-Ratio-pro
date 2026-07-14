from __future__ import annotations

"""Import helpers for manually managed interpretation intervals.

Parsing is independent from Streamlit and persistence. Application is delegated
through ``InterpretationIntervalManager`` so a complete import is recorded as a
single Undo/Redo command.
"""

import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Literal

import pandas as pd

from projects.interpretation_interval_exports import INTERVAL_EXPORT_SCHEMA
from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_intervals import InterpretationInterval, build_interpretation_interval

ImportMode = Literal["append", "upsert", "replace"]
SUPPORTED_IMPORT_SUFFIXES = {".json", ".csv", ".xlsx"}


@dataclass(frozen=True)
class InterpretationIntervalImportPayload:
    intervals: tuple[InterpretationInterval, ...]
    source_format: str
    project_id: str = ""
    well_id: str = ""
    interpretation_id: str = ""


@dataclass(frozen=True)
class InterpretationIntervalImportResult:
    mode: ImportMode
    imported_count: int
    total_count: int
    created_count: int
    updated_count: int


def _clean_optional(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    clean = str(value).strip()
    return clean or None


def _row_to_interval(raw: dict[str, Any], *, row_number: int) -> InterpretationInterval:
    try:
        return build_interpretation_interval(
            interval_id=_clean_optional(raw.get("id")),
            label=str(raw.get("label", "") or ""),
            top=raw.get("top"),
            base=raw.get("base"),
            interval_type=str(raw.get("interval_type", "undefined") or "undefined"),
            color=str(raw.get("color", "#4C78A8") or "#4C78A8"),
            comment=str(raw.get("comment", "") or ""),
            source=str(raw.get("source", "import") or "import"),
            created_at=_clean_optional(raw.get("created_at")),
            updated_at=_clean_optional(raw.get("updated_at")),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Ошибка в строке импорта {row_number}: {exc}") from exc


def _build_payload(
    rows: Iterable[dict[str, Any]],
    *,
    source_format: str,
    project_id: str = "",
    well_id: str = "",
    interpretation_id: str = "",
) -> InterpretationIntervalImportPayload:
    intervals = tuple(_row_to_interval(row, row_number=index) for index, row in enumerate(rows, start=1))
    ids = [item.id for item in intervals]
    if len(ids) != len(set(ids)):
        raise ValueError("Импорт содержит повторяющиеся UUID интервалов.")
    return InterpretationIntervalImportPayload(
        intervals=intervals,
        source_format=source_format,
        project_id=project_id,
        well_id=well_id,
        interpretation_id=interpretation_id,
    )


def parse_interpretation_interval_json(data: bytes) -> InterpretationIntervalImportPayload:
    try:
        raw = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Не удалось прочитать JSON-файл интервалов.") from exc
    if not isinstance(raw, dict) or raw.get("schema") != INTERVAL_EXPORT_SCHEMA:
        raise ValueError("Неподдерживаемая схема JSON-файла интервалов.")
    rows = raw.get("intervals")
    if not isinstance(rows, list):
        raise ValueError("JSON-файл не содержит список intervals.")
    return _build_payload(
        rows,
        source_format="json",
        project_id=str(raw.get("project_id", "") or ""),
        well_id=str(raw.get("well_id", "") or ""),
        interpretation_id=str(raw.get("interpretation_id", "") or ""),
    )


def _frame_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    required = {"label", "top", "base"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Отсутствуют обязательные столбцы: {', '.join(missing)}.")
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def parse_interpretation_interval_csv(data: bytes) -> InterpretationIntervalImportPayload:
    try:
        frame = pd.read_csv(BytesIO(data))
    except Exception as exc:
        raise ValueError("Не удалось прочитать CSV-файл интервалов.") from exc
    return _build_payload(_frame_rows(frame), source_format="csv")


def parse_interpretation_interval_xlsx(data: bytes) -> InterpretationIntervalImportPayload:
    try:
        workbook = pd.ExcelFile(BytesIO(data))
        sheet_name = "intervals" if "intervals" in workbook.sheet_names else workbook.sheet_names[0]
        frame = pd.read_excel(BytesIO(data), sheet_name=sheet_name)
    except Exception as exc:
        raise ValueError("Не удалось прочитать Excel-файл интервалов.") from exc
    return _build_payload(_frame_rows(frame), source_format="xlsx")


def parse_interpretation_interval_import(data: bytes, filename: str) -> InterpretationIntervalImportPayload:
    suffix = Path(filename).suffix.lower()
    if suffix == ".json":
        return parse_interpretation_interval_json(data)
    if suffix == ".csv":
        return parse_interpretation_interval_csv(data)
    if suffix == ".xlsx":
        return parse_interpretation_interval_xlsx(data)
    raise ValueError("Поддерживаются только файлы JSON, CSV и XLSX.")


def apply_interpretation_interval_import(
    manager: InterpretationIntervalManager,
    payload: InterpretationIntervalImportPayload,
    *,
    mode: ImportMode = "upsert",
) -> InterpretationIntervalImportResult:
    if mode not in {"append", "upsert", "replace"}:
        raise ValueError(f"Неподдерживаемый режим импорта: {mode}")

    existing = manager.list_intervals()
    existing_by_id = {item.id: item for item in existing}
    imported_by_id = {item.id: item for item in payload.intervals}

    if mode == "append":
        duplicates = sorted(set(existing_by_id).intersection(imported_by_id))
        if duplicates:
            raise ValueError("UUID импортируемых интервалов уже существуют в текущей интерпретации.")
        merged = (*existing, *payload.intervals)
        created_count = len(payload.intervals)
        updated_count = 0
    elif mode == "replace":
        merged = payload.intervals
        created_count = len(set(imported_by_id).difference(existing_by_id))
        updated_count = len(set(imported_by_id).intersection(existing_by_id))
    else:
        merged_by_id = dict(existing_by_id)
        merged_by_id.update(imported_by_id)
        merged = tuple(merged_by_id.values())
        created_count = len(set(imported_by_id).difference(existing_by_id))
        updated_count = len(set(imported_by_id).intersection(existing_by_id))

    stored = manager.replace_all(tuple(merged), action=f"import_{mode}")
    return InterpretationIntervalImportResult(
        mode=mode,
        imported_count=len(payload.intervals),
        total_count=len(stored),
        created_count=created_count,
        updated_count=updated_count,
    )
