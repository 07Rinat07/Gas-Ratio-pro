from __future__ import annotations

import html
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
PROJECT_CALCULATION_CARD_WARNING_LIMIT = 5
PROJECT_CALCULATION_CARD_COLUMN_LIMIT = 12
PROJECT_CALCULATION_KEY_COLUMN_PRIORITY = (
    "depth",
    "dept",
    "md",
    "tvd",
    "c1",
    "c2",
    "c3",
    "ic4",
    "nc4",
    "ic5",
    "nc5",
    "wh",
    "bh",
    "ch",
    "bar2",
    "pixler_c1_c2",
    "pixler_c1_c3",
    "pixler_c1_c4",
    "pixler_c1_c5",
    "oil_indicator",
    "inverse_oil_indicator",
    "interpretation",
)
PROJECT_CALCULATION_EXPORT_LABELS = {"csv": "CSV", "xlsx": "XLSX", "metadata": "metadata.json"}
PROJECT_CALCULATION_COMPARE_COLUMN_LIMIT = 20
PROJECT_CALCULATION_CARD_MAPPING_LIMIT = 8
PROJECT_CALCULATION_REQUIRED_MAPPING_FIELDS = (
    "depth",
    "c1",
    "c2",
    "c3",
    "ic4",
    "nc4",
)
PROJECT_CALCULATION_DEPTH_COLUMN_ALIASES = ("depth", "dept", "md")
PROJECT_CALCULATION_KEY_GAS_MAPPING_FIELDS = ("c1", "c2", "c3", "ic4", "nc4")



@dataclass(frozen=True)
class ProjectCalculationsSummary:
    count: int
    total_rows: int
    total_warnings: int
    latest_saved_at: str = ""
    latest_source_label: str = ""
    sources: tuple[str, ...] = ()
    columns: tuple[str, ...] = ()




@dataclass(frozen=True)
class ProjectCalculationCard:
    id: str
    source_label: str
    sheet_name: str
    saved_at: str
    row_count: int
    ch_mode: str = ""
    warning_preview: tuple[str, ...] = ()
    warnings_count: int = 0
    key_columns: tuple[str, ...] = ()
    available_exports: tuple[str, ...] = ()
    graph_ready: bool = False
    mapping_count: int = 0
    mapping_preview: tuple[str, ...] = ()
    missing_mapping_fields: tuple[str, ...] = ()
    ch_mode_label: str = ""
    open_warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class ProjectCalculationComparison:
    left_id: str
    right_id: str
    left_source_label: str
    right_source_label: str
    left_rows: int
    right_rows: int
    row_delta: int
    added_columns: tuple[str, ...] = ()
    removed_columns: tuple[str, ...] = ()
    common_columns: tuple[str, ...] = ()
    changed_columns: tuple[str, ...] = ()
    changed_cell_count: int = 0
    added_warnings: tuple[str, ...] = ()
    removed_warnings: tuple[str, ...] = ()
    common_warnings: tuple[str, ...] = ()

    @property
    def has_differences(self) -> bool:
        return bool(
            self.row_delta
            or self.added_columns
            or self.removed_columns
            or self.changed_columns
            or self.changed_cell_count
            or self.added_warnings
            or self.removed_warnings
        )


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



def summarize_project_calculations(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> ProjectCalculationsSummary:
    records = list_project_calculations(root, project_id)
    if not records:
        return ProjectCalculationsSummary(count=0, total_rows=0, total_warnings=0)

    columns: set[str] = set()
    for record in records:
        try:
            metadata = read_project_calculation_metadata(root, project_id, record.id)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError, ValueError, TypeError):
            continue
        for column in metadata.get("columns", ()):
            column_name = str(column).strip()
            if column_name:
                columns.add(column_name)

    latest = records[0]
    return ProjectCalculationsSummary(
        count=len(records),
        total_rows=sum(record.row_count for record in records),
        total_warnings=sum(record.warnings_count for record in records),
        latest_saved_at=latest.saved_at,
        latest_source_label=latest.source_label,
        sources=tuple(dict.fromkeys(record.source_label for record in records if record.source_label)),
        columns=tuple(sorted(columns, key=str.lower)),
    )




def _select_project_calculation_key_columns(columns: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    clean_columns = tuple(dict.fromkeys(str(column).strip() for column in columns if str(column).strip()))
    if not clean_columns:
        return ()

    columns_by_folded = {column.casefold(): column for column in clean_columns}
    selected: list[str] = []
    for priority_column in PROJECT_CALCULATION_KEY_COLUMN_PRIORITY:
        matched = columns_by_folded.get(priority_column.casefold())
        if matched and matched not in selected:
            selected.append(matched)

    for column in clean_columns:
        if len(selected) >= PROJECT_CALCULATION_CARD_COLUMN_LIMIT:
            break
        if column not in selected:
            selected.append(column)

    return tuple(selected[:PROJECT_CALCULATION_CARD_COLUMN_LIMIT])


def _normalize_project_calculation_mapping(mapping: Any) -> dict[str, str]:
    if not isinstance(mapping, dict):
        return {}

    normalized: dict[str, str] = {}
    for target_field, source_column in mapping.items():
        clean_target = str(target_field).strip()
        clean_source = str(source_column).strip()
        if clean_target and clean_source and clean_source.lower() not in {"none", "nan"}:
            normalized[clean_target] = clean_source
    return normalized


def _build_project_calculation_mapping_preview(mapping: dict[str, str]) -> tuple[str, ...]:
    priority = PROJECT_CALCULATION_REQUIRED_MAPPING_FIELDS + tuple(
        field for field in mapping if field not in PROJECT_CALCULATION_REQUIRED_MAPPING_FIELDS
    )
    preview: list[str] = []
    for field in priority:
        if field in mapping:
            preview.append(f"{field} → {mapping[field]}")
        if len(preview) >= PROJECT_CALCULATION_CARD_MAPPING_LIMIT:
            break
    return tuple(preview)


def _missing_project_calculation_mapping_fields(mapping: dict[str, str]) -> tuple[str, ...]:
    mapped_fields = {field.casefold() for field in mapping}
    return tuple(field for field in PROJECT_CALCULATION_REQUIRED_MAPPING_FIELDS if field.casefold() not in mapped_fields)


def _build_project_calculation_open_warnings(
    *,
    columns: tuple[str, ...],
    missing_mapping_fields: tuple[str, ...],
) -> tuple[str, ...]:
    folded_columns = {column.casefold() for column in columns}
    warnings: list[str] = []

    if not any(alias in folded_columns for alias in PROJECT_CALCULATION_DEPTH_COLUMN_ALIASES):
        warnings.append(
            "В сохраненном snapshot не найдена колонка depth/DEPT/MD. "
            "Интерпретационные графики могут открыться без корректной оси глубины."
        )

    missing_gas_fields = tuple(
        field for field in PROJECT_CALCULATION_KEY_GAS_MAPPING_FIELDS if field in missing_mapping_fields
    )
    if missing_gas_fields:
        warnings.append(
            "В mapping snapshot отсутствуют ключевые газовые поля: "
            + ", ".join(missing_gas_fields)
            + ". Перед анализом проверьте сопоставление C1-C5 и предупреждения расчета."
        )

    return tuple(warnings)


def _project_calculation_ch_mode_label(ch_mode: str) -> str:
    clean_mode = str(ch_mode).strip()
    if not clean_mode:
        return "не указан"
    labels = {
        "ratio": "ratio / расчетный режим Ch",
        "standard": "standard / стандартный режим Ch",
        "legacy": "legacy / старый режим Ch",
    }
    return labels.get(clean_mode.casefold(), clean_mode)


def build_project_calculation_card(
    root: Path | str,
    project_id: str,
    calculation_id: str,
) -> ProjectCalculationCard:
    """Build a compact UI card for a saved project calculation.

    The card is intentionally metadata-driven, so the project screen can show
    the important context before the user opens a calculation in interpretation
    graphs or downloads the export files.
    """

    records = {record.id: record for record in list_project_calculations(root, project_id)}
    record = records.get(_safe_calculation_id(calculation_id))
    if record is None:
        raise FileNotFoundError(f"Project calculation not found: {calculation_id}")

    metadata = read_project_calculation_metadata(root, project_id, record.id)
    warnings = tuple(str(warning) for warning in metadata.get("warnings", ()) if str(warning))
    columns = tuple(str(column) for column in metadata.get("columns", ()) if str(column))
    mapping = _normalize_project_calculation_mapping(metadata.get("mapping", {}))
    available_exports = tuple(
        PROJECT_CALCULATION_EXPORT_LABELS.get(file_key, file_key.upper())
        for file_key in ("csv", "xlsx", "metadata")
        if file_key in record.files
    )
    folded_columns = {column.casefold() for column in columns}
    graph_ready = bool(columns) and any(column in folded_columns for column in {"depth", "dept", "md"})
    missing_mapping_fields = _missing_project_calculation_mapping_fields(mapping)
    open_warnings = _build_project_calculation_open_warnings(
        columns=columns,
        missing_mapping_fields=missing_mapping_fields,
    )

    return ProjectCalculationCard(
        id=record.id,
        source_label=record.source_label,
        sheet_name=record.sheet_name,
        saved_at=record.saved_at,
        row_count=record.row_count,
        ch_mode=record.ch_mode,
        warning_preview=warnings[:PROJECT_CALCULATION_CARD_WARNING_LIMIT],
        warnings_count=len(warnings),
        key_columns=_select_project_calculation_key_columns(columns),
        available_exports=available_exports,
        graph_ready=graph_ready,
        mapping_count=len(mapping),
        mapping_preview=_build_project_calculation_mapping_preview(mapping),
        missing_mapping_fields=missing_mapping_fields,
        ch_mode_label=_project_calculation_ch_mode_label(record.ch_mode or str(metadata.get("ch_mode", ""))),
        open_warnings=open_warnings,
    )

def filter_project_calculations(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    source_query: str = "",
    warning_state: str = "any",
    required_columns: tuple[str, ...] | list[str] | None = None,
) -> tuple[ProjectCalculationRecord, ...]:
    """Return saved calculation records matching practical project filters.

    The function intentionally keeps filtering conservative: corrupted metadata
    does not break the project screen, but records that require metadata-based
    checks are skipped because their warning list or column set cannot be
    trusted.
    """

    records = list_project_calculations(root, project_id)
    clean_source_query = source_query.strip().casefold()
    clean_warning_state = warning_state.strip().casefold() or "any"
    clean_required_columns = tuple(
        dict.fromkeys(str(column).strip() for column in (required_columns or ()) if str(column).strip())
    )
    required_columns_folded = {column.casefold() for column in clean_required_columns}

    filtered: list[ProjectCalculationRecord] = []
    for record in records:
        if clean_source_query and clean_source_query not in record.source_label.casefold():
            continue

        needs_metadata = clean_warning_state in {"with_warnings", "without_warnings"} or bool(required_columns_folded)
        metadata: dict[str, Any] = {}
        if needs_metadata:
            try:
                metadata = read_project_calculation_metadata(root, project_id, record.id)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError, ValueError, TypeError):
                continue

        if clean_warning_state == "with_warnings":
            warnings = metadata.get("warnings", ())
            if not warnings:
                continue
        elif clean_warning_state == "without_warnings":
            warnings = metadata.get("warnings", ())
            if warnings:
                continue
        elif clean_warning_state not in {"any", "all"}:
            raise ValueError("Некорректный режим фильтра предупреждений.")

        if required_columns_folded:
            available_columns = {str(column).strip().casefold() for column in metadata.get("columns", ())}
            if not required_columns_folded.issubset(available_columns):
                continue

        filtered.append(record)

    return tuple(filtered)



def _ordered_difference(primary: tuple[str, ...], secondary: tuple[str, ...]) -> tuple[str, ...]:
    secondary_folded = {item.casefold() for item in secondary}
    return tuple(item for item in primary if item.casefold() not in secondary_folded)


def _ordered_intersection(primary: tuple[str, ...], secondary: tuple[str, ...]) -> tuple[str, ...]:
    secondary_folded = {item.casefold() for item in secondary}
    return tuple(item for item in primary if item.casefold() in secondary_folded)


def _metadata_columns(metadata: dict[str, Any]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(column).strip() for column in metadata.get("columns", ()) if str(column).strip()))


def _metadata_warnings(metadata: dict[str, Any]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(warning).strip() for warning in metadata.get("warnings", ()) if str(warning).strip()))


def compare_project_calculations(
    root: Path | str,
    project_id: str,
    left_calculation_id: str,
    right_calculation_id: str,
) -> ProjectCalculationComparison:
    """Compare two saved calculation snapshots without modifying project files.

    The comparison is intentionally conservative and safe for the UI: it reads
    only saved CSV and metadata files, compares table shape, column sets,
    position-based cell changes for common columns, and warning sets. It does
    not infer geological meaning and does not overwrite snapshots.
    """

    left_id = _safe_calculation_id(left_calculation_id)
    right_id = _safe_calculation_id(right_calculation_id)
    if left_id == right_id:
        raise ValueError("Для сравнения нужно выбрать два разных сохраненных расчета.")

    records = {record.id: record for record in list_project_calculations(root, project_id)}
    left_record = records.get(left_id)
    right_record = records.get(right_id)
    if left_record is None or right_record is None:
        raise FileNotFoundError("Project calculation not found for comparison")

    left_metadata = read_project_calculation_metadata(root, project_id, left_id)
    right_metadata = read_project_calculation_metadata(root, project_id, right_id)
    left_df = read_project_calculation_dataframe(root, project_id, left_id)
    right_df = read_project_calculation_dataframe(root, project_id, right_id)

    left_columns = _metadata_columns(left_metadata) or tuple(str(column) for column in left_df.columns)
    right_columns = _metadata_columns(right_metadata) or tuple(str(column) for column in right_df.columns)
    common_columns = _ordered_intersection(left_columns, right_columns)

    changed_columns: list[str] = []
    changed_cell_count = 0
    comparable_rows = min(len(left_df), len(right_df))
    for column in common_columns:
        left_column = next((item for item in left_df.columns if str(item).casefold() == column.casefold()), None)
        right_column = next((item for item in right_df.columns if str(item).casefold() == column.casefold()), None)
        if left_column is None or right_column is None or comparable_rows == 0:
            continue
        left_values = left_df[left_column].head(comparable_rows).reset_index(drop=True)
        right_values = right_df[right_column].head(comparable_rows).reset_index(drop=True)
        unequal = ~(left_values.eq(right_values) | (left_values.isna() & right_values.isna()))
        differences = int(unequal.sum())
        if differences:
            changed_columns.append(column)
            changed_cell_count += differences

    left_warnings = _metadata_warnings(left_metadata)
    right_warnings = _metadata_warnings(right_metadata)

    return ProjectCalculationComparison(
        left_id=left_id,
        right_id=right_id,
        left_source_label=left_record.source_label,
        right_source_label=right_record.source_label,
        left_rows=len(left_df),
        right_rows=len(right_df),
        row_delta=len(right_df) - len(left_df),
        added_columns=_ordered_difference(right_columns, left_columns),
        removed_columns=_ordered_difference(left_columns, right_columns),
        common_columns=common_columns,
        changed_columns=tuple(changed_columns[:PROJECT_CALCULATION_COMPARE_COLUMN_LIMIT]),
        changed_cell_count=changed_cell_count,
        added_warnings=_ordered_difference(right_warnings, left_warnings),
        removed_warnings=_ordered_difference(left_warnings, right_warnings),
        common_warnings=_ordered_intersection(left_warnings, right_warnings),
    )


def _format_comparison_tuple(values: tuple[str, ...], empty_text: str = "нет") -> str:
    return ", ".join(values) if values else empty_text

def build_project_calculation_comparison_table(comparison: ProjectCalculationComparison) -> pd.DataFrame:
    """Return a compact tabular summary of saved snapshot differences.

    The table is used both in Streamlit and in CSV/HTML downloads, so the
    exported file contains the same sections that the engineer reviewed on
    screen before handing the comparison to a report package.
    """

    return pd.DataFrame(
        [
            {"Раздел": "Базовый расчет", "Значения": comparison.left_source_label},
            {"Раздел": "Новый расчет", "Значения": comparison.right_source_label},
            {"Раздел": "Строк в базовом расчете", "Значения": comparison.left_rows},
            {"Раздел": "Строк в новом расчете", "Значения": comparison.right_rows},
            {"Раздел": "Изменение количества строк", "Значения": comparison.row_delta},
            {"Раздел": "Общие колонки", "Значения": _format_comparison_tuple(comparison.common_columns)},
            {"Раздел": "Колонки добавлены", "Значения": _format_comparison_tuple(comparison.added_columns)},
            {"Раздел": "Колонки удалены", "Значения": _format_comparison_tuple(comparison.removed_columns)},
            {"Раздел": "Колонки с измененными ячейками", "Значения": _format_comparison_tuple(comparison.changed_columns)},
            {"Раздел": "Измененных ячеек", "Значения": comparison.changed_cell_count},
            {"Раздел": "Предупреждения добавлены", "Значения": _format_comparison_tuple(comparison.added_warnings)},
            {"Раздел": "Предупреждения удалены", "Значения": _format_comparison_tuple(comparison.removed_warnings)},
            {"Раздел": "Предупреждения без изменений", "Значения": _format_comparison_tuple(comparison.common_warnings)},
            {
                "Раздел": "Итог",
                "Значения": "Есть отличия" if comparison.has_differences else "Существенные отличия не найдены",
            },
        ]
    )


def export_project_calculation_comparison_csv(comparison: ProjectCalculationComparison) -> bytes:
    """Export a saved snapshot comparison to CSV bytes."""

    return export_csv_bytes(build_project_calculation_comparison_table(comparison))


def export_project_calculation_comparison_html(comparison: ProjectCalculationComparison) -> bytes:
    """Export a saved snapshot comparison to a standalone HTML report."""

    status = "Есть отличия" if comparison.has_differences else "Существенные отличия не найдены"
    rows = []
    for row in build_project_calculation_comparison_table(comparison).to_dict("records"):
        rows.append(
            "<tr>"
            f"<th>{html.escape(str(row['Раздел']))}</th>"
            f"<td>{html.escape(str(row['Значения']))}</td>"
            "</tr>"
        )

    document = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Сравнение сохраненных расчетов</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
    h1 {{ margin-bottom: 8px; }}
    .status {{ margin: 12px 0 20px; padding: 10px 12px; border: 1px solid #999; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; vertical-align: top; text-align: left; }}
    th {{ width: 32%; background: #f3f3f3; }}
    .note {{ margin-top: 20px; font-size: 12px; color: #555; }}
  </style>
</head>
<body>
  <h1>Сравнение сохраненных расчетов проекта</h1>
  <div class="status"><strong>Итог:</strong> {html.escape(status)}</div>
  <table>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <p class="note">Отчет построен только по сохраненным snapshots: CSV-таблицам, metadata, колонкам и предупреждениям. Исходные файлы проекта не изменялись.</p>
</body>
</html>
"""
    return document.encode("utf-8")

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
