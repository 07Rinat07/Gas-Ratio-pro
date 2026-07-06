from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from projects.las_files import ProjectLasFile, list_project_las_files, read_project_las_file_dataframe
from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

PROJECT_LAS_EXPLORER_FILE_NAME = "las_explorer.json"
DEPTH_CURVE_NAMES = ("DEPT", "DEPTH", "MD")


@dataclass(frozen=True)
class ProjectLasExplorerSettings:
    las_file_id: str
    tags: tuple[str, ...] = ()
    favorite: bool = False
    note: str = ""
    group: str = ""


@dataclass(frozen=True)
class ProjectLasExplorerDiagnostics:
    las_file_id: str
    rows: int
    curves_count: int
    depth_curve: str
    null_cells: int
    duplicate_depths: int
    min_depth: float | None
    max_depth: float | None
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ProjectLasExplorerItem:
    id: str
    well_id: str
    well_name: str
    version_label: str
    original_file_name: str
    saved_at: str
    size_bytes: int
    archived: bool
    tags: tuple[str, ...]
    favorite: bool
    note: str
    group: str
    curves: tuple[str, ...]
    diagnostics: ProjectLasExplorerDiagnostics | None = None


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _settings_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_LAS_EXPLORER_FILE_NAME


def _clean_text(value: Any, *, max_length: int = 120) -> str:
    text = "" if value is None else str(value).strip()
    if len(text) > max_length:
        raise ValueError(f"Значение слишком длинное: максимум {max_length} символов.")
    return text


def _clean_tag(value: Any) -> str:
    tag = _clean_text(value, max_length=40).lower()
    return " ".join(tag.split())


def _read_settings(root: Path | str, project_id: str) -> dict[str, ProjectLasExplorerSettings]:
    path = _settings_path(root, project_id)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    rows = payload.get("las_files", []) if isinstance(payload, dict) else []
    settings: dict[str, ProjectLasExplorerSettings] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        las_file_id = _clean_text(row.get("las_file_id"), max_length=120)
        if not las_file_id:
            continue
        settings[las_file_id] = ProjectLasExplorerSettings(
            las_file_id=las_file_id,
            tags=tuple(dict.fromkeys(_clean_tag(tag) for tag in row.get("tags", []) if _clean_tag(tag))),
            favorite=bool(row.get("favorite", False)),
            note=_clean_text(row.get("note"), max_length=400),
            group=_clean_text(row.get("group"), max_length=80),
        )
    return settings


def _write_settings(root: Path | str, project_id: str, settings: Iterable[ProjectLasExplorerSettings]) -> None:
    path = _settings_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "project_id": safe_project_id(project_id),
        "las_files": [
            {
                "las_file_id": item.las_file_id,
                "tags": list(item.tags),
                "favorite": item.favorite,
                "note": item.note,
                "group": item.group,
            }
            for item in settings
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_project_las_explorer_settings(
    root: Path | str,
    project_id: str,
    las_file_id: str,
    *,
    tags: Iterable[str] = (),
    favorite: bool = False,
    note: str = "",
    group: str = "",
) -> ProjectLasExplorerSettings:
    clean_id = _clean_text(las_file_id, max_length=120)
    if not clean_id:
        raise ValueError("LAS-файл обязателен для настроек LAS Explorer.")
    known_ids = {record.id for record in list_project_las_files(root, project_id, include_archived=True)}
    if clean_id not in known_ids:
        raise FileNotFoundError(f"Project LAS file not found: {clean_id}")
    clean_tags = tuple(dict.fromkeys(tag for tag in (_clean_tag(value) for value in tags) if tag))
    item = ProjectLasExplorerSettings(
        las_file_id=clean_id,
        tags=clean_tags,
        favorite=bool(favorite),
        note=_clean_text(note, max_length=400),
        group=_clean_text(group, max_length=80),
    )
    settings = _read_settings(root, project_id)
    settings[clean_id] = item
    _write_settings(root, project_id, settings.values())
    append_project_history(root, project_id, "las-explorer", f"Updated LAS Explorer metadata for {clean_id}", object_type="las", object_id=clean_id)
    return item


def _find_depth_curve(columns: Iterable[Any]) -> str:
    by_upper = {str(column).upper(): str(column) for column in columns}
    for name in DEPTH_CURVE_NAMES:
        if name in by_upper:
            return by_upper[name]
    return ""


def diagnose_project_las_file(root: Path | str, project_id: str, las_file_id: str) -> ProjectLasExplorerDiagnostics:
    dataframe = read_project_las_file_dataframe(root, project_id, las_file_id)
    depth_curve = _find_depth_curve(dataframe.columns)
    warnings: list[str] = []
    duplicate_depths = 0
    min_depth: float | None = None
    max_depth: float | None = None
    if not depth_curve:
        warnings.append("Глубинная кривая DEPT/DEPTH/MD не найдена.")
    else:
        depth = pd.to_numeric(dataframe[depth_curve], errors="coerce")
        valid_depth = depth.dropna()
        duplicate_depths = int(valid_depth.duplicated().sum())
        if not valid_depth.empty:
            min_depth = float(valid_depth.min())
            max_depth = float(valid_depth.max())
        if duplicate_depths:
            warnings.append(f"Найдены дубли глубины: {duplicate_depths}.")
        if not valid_depth.empty and not valid_depth.is_monotonic_increasing:
            warnings.append("Глубина не монотонно возрастает.")
    null_cells = int(dataframe.isna().sum().sum())
    if dataframe.empty:
        warnings.append("LAS не содержит табличных строк.")
    if len(dataframe.columns) <= 1:
        warnings.append("Недостаточно кривых для анализа.")
    return ProjectLasExplorerDiagnostics(
        las_file_id=las_file_id,
        rows=int(len(dataframe)),
        curves_count=int(len(dataframe.columns)),
        depth_curve=depth_curve,
        null_cells=null_cells,
        duplicate_depths=duplicate_depths,
        min_depth=min_depth,
        max_depth=max_depth,
        warnings=tuple(warnings),
    )


def _safe_diagnostics(root: Path | str, project_id: str, record: ProjectLasFile) -> ProjectLasExplorerDiagnostics | None:
    try:
        return diagnose_project_las_file(root, project_id, record.id)
    except Exception:
        return None


def list_project_las_explorer_items(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    *,
    include_archived: bool = False,
    include_diagnostics: bool = False,
) -> tuple[ProjectLasExplorerItem, ...]:
    settings = _read_settings(root, project_id)
    items: list[ProjectLasExplorerItem] = []
    for record in list_project_las_files(root, project_id, include_archived=include_archived):
        meta = settings.get(record.id, ProjectLasExplorerSettings(record.id))
        diagnostics = _safe_diagnostics(root, project_id, record) if include_diagnostics else None
        curves = tuple(str(curve) for curve in (record.metadata or {}).get("curves", ()) if str(curve))
        if diagnostics and not curves:
            try:
                curves = tuple(str(column) for column in read_project_las_file_dataframe(root, project_id, record.id).columns)
            except Exception:
                curves = ()
        items.append(
            ProjectLasExplorerItem(
                id=record.id,
                well_id=record.well_id,
                well_name=record.name,
                version_label=record.version_label,
                original_file_name=record.original_file_name,
                saved_at=record.saved_at,
                size_bytes=record.size_bytes,
                archived=bool(record.archived_at),
                tags=meta.tags,
                favorite=meta.favorite,
                note=meta.note,
                group=meta.group,
                curves=curves,
                diagnostics=diagnostics,
            )
        )
    return tuple(items)


def search_project_las_explorer_items(
    items: Iterable[ProjectLasExplorerItem],
    query: str = "",
    *,
    well_id: str = "",
    tag: str = "",
    favorites_only: bool = False,
    include_archived: bool = False,
) -> tuple[ProjectLasExplorerItem, ...]:
    clean_query = str(query).strip().lower()
    clean_well_id = str(well_id).strip().lower()
    clean_tag = _clean_tag(tag)
    result: list[ProjectLasExplorerItem] = []
    for item in items:
        if item.archived and not include_archived:
            continue
        if favorites_only and not item.favorite:
            continue
        if clean_well_id and item.well_id.lower() != clean_well_id:
            continue
        if clean_tag and clean_tag not in item.tags:
            continue
        haystack = " ".join((item.id, item.well_id, item.well_name, item.version_label, item.original_file_name, item.note, item.group, " ".join(item.tags), " ".join(item.curves))).lower()
        if clean_query and clean_query not in haystack:
            continue
        result.append(item)
    return tuple(result)


def build_project_las_explorer_table(items: Iterable[ProjectLasExplorerItem]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        diagnostics = item.diagnostics
        rows.append(
            {
                "LAS": item.original_file_name,
                "Скважина": item.well_name,
                "Версия": item.version_label,
                "Группа": item.group,
                "Теги": ", ".join(item.tags),
                "Избранное": "★" if item.favorite else "",
                "Кривые": diagnostics.curves_count if diagnostics else len(item.curves),
                "Строки": diagnostics.rows if diagnostics else "",
                "Глубина": diagnostics.depth_curve if diagnostics else "",
                "Предупреждения": "; ".join(diagnostics.warnings) if diagnostics else "",
                "Дата": item.saved_at,
                "Архив": "Да" if item.archived else "Нет",
            }
        )
    return rows


def preview_project_las_file(root: Path | str, project_id: str, las_file_id: str, *, rows: int = 20) -> pd.DataFrame:
    if rows < 1 or rows > 500:
        raise ValueError("Количество строк предпросмотра должно быть в диапазоне 1..500.")
    return read_project_las_file_dataframe(root, project_id, las_file_id).head(rows).copy()
