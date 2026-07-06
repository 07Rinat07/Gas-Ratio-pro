from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import ProjectWellCard, ensure_project_well_card, list_project_well_cards, safe_well_id

PROJECT_FORMATION_TOPS_FILE_NAME = "formation_tops.json"
PROJECT_WELL_TRAJECTORY_FILE_NAME = "well_trajectory.json"
PROJECT_WELL_NOTES_FILE_NAME = "well_notes.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _optional_float(value: Any, field_label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        clean = value.strip().replace(",", ".")
        if not clean:
            return None
        value = clean
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_label}: ожидается число.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{field_label}: значение должно быть конечным числом.")
    return number


def _required_float(value: Any, field_label: str) -> float:
    number = _optional_float(value, field_label)
    if number is None:
        raise ValueError(f"{field_label}: значение обязательно.")
    return number


def _clean_text(value: Any, field_label: str, *, max_length: int = 160, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


@dataclass(frozen=True)
class ProjectFormationTop:
    id: str
    well_id: str
    name: str
    md_m: float
    tvd_m: float | None = None
    color: str = ""
    source: str = "manual"
    note: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ProjectTrajectoryStation:
    id: str
    well_id: str
    md_m: float
    inclination_deg: float
    azimuth_deg: float
    tvd_m: float | None = None
    north_m: float | None = None
    east_m: float | None = None
    source: str = "manual"
    updated_at: str = ""


@dataclass(frozen=True)
class ProjectWellNote:
    id: str
    well_id: str
    title: str
    body: str
    category: str = "general"
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ProjectWellManagerRecord:
    well_id: str
    name: str
    status: str
    status_label: str
    field: str
    operator: str
    kb_m: float | None
    gl_m: float | None
    planned_td_m: float | None
    actual_td_m: float | None
    tops_count: int
    trajectory_stations_count: int
    notes_count: int
    completeness_percent: int
    updated_at: str


def _top_from_dict(raw: dict[str, Any]) -> ProjectFormationTop:
    return ProjectFormationTop(
        id=str(raw.get("id", "")),
        well_id=safe_well_id(str(raw.get("well_id", ""))),
        name=str(raw.get("name", "")),
        md_m=_required_float(raw.get("md_m"), "MD"),
        tvd_m=_optional_float(raw.get("tvd_m"), "TVD"),
        color=str(raw.get("color", "")),
        source=str(raw.get("source", "manual")),
        note=str(raw.get("note", "")),
        updated_at=str(raw.get("updated_at", "")),
    )


def _station_from_dict(raw: dict[str, Any]) -> ProjectTrajectoryStation:
    return ProjectTrajectoryStation(
        id=str(raw.get("id", "")),
        well_id=safe_well_id(str(raw.get("well_id", ""))),
        md_m=_required_float(raw.get("md_m"), "MD"),
        inclination_deg=_required_float(raw.get("inclination_deg"), "Инклинометрия"),
        azimuth_deg=_required_float(raw.get("azimuth_deg"), "Азимут"),
        tvd_m=_optional_float(raw.get("tvd_m"), "TVD"),
        north_m=_optional_float(raw.get("north_m"), "North"),
        east_m=_optional_float(raw.get("east_m"), "East"),
        source=str(raw.get("source", "manual")),
        updated_at=str(raw.get("updated_at", "")),
    )


def _note_from_dict(raw: dict[str, Any]) -> ProjectWellNote:
    return ProjectWellNote(
        id=str(raw.get("id", "")),
        well_id=safe_well_id(str(raw.get("well_id", ""))),
        title=str(raw.get("title", "")),
        body=str(raw.get("body", "")),
        category=str(raw.get("category", "general")),
        created_at=str(raw.get("created_at", "")),
        updated_at=str(raw.get("updated_at", "")),
    )


def _dataclass_to_dict(item: Any) -> dict[str, Any]:
    return dict(item.__dict__)


def _load_items(root: Path | str, project_id: str, file_name: str, parser) -> tuple[Any, ...]:
    raw = _json_read(_project_dir(root, project_id) / file_name, [])
    if not isinstance(raw, list):
        return ()
    items = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            items.append(parser(row))
        except (TypeError, ValueError):
            continue
    return tuple(items)


def _save_items(root: Path | str, project_id: str, file_name: str, items: Iterable[Any]) -> None:
    _json_write(_project_dir(root, project_id) / file_name, [_dataclass_to_dict(item) for item in items])


def list_project_formation_tops(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str | None = None,
) -> tuple[ProjectFormationTop, ...]:
    items = _load_items(root, project_id, PROJECT_FORMATION_TOPS_FILE_NAME, _top_from_dict)
    if well_id:
        clean_well_id = safe_well_id(well_id)
        items = tuple(item for item in items if item.well_id == clean_well_id)
    return tuple(sorted(items, key=lambda item: (item.well_id, item.md_m, item.name.lower())))


def save_project_formation_top(
    root: Path | str,
    project_id: str,
    well_id: str,
    name: str,
    md_m: Any,
    *,
    tvd_m: Any = None,
    color: str = "",
    source: str = "manual",
    note: str = "",
    top_id: str | None = None,
) -> ProjectFormationTop:
    clean_well_id = safe_well_id(well_id)
    clean_name = _clean_text(name, "Пласт", required=True)
    md_value = _required_float(md_m, "MD")
    if md_value < 0 or md_value > 15000:
        raise ValueError("MD пласта должен быть в диапазоне 0..15000 м.")
    tvd_value = _optional_float(tvd_m, "TVD")
    if tvd_value is not None and (tvd_value < 0 or tvd_value > md_value + 1000):
        raise ValueError("TVD пласта должен быть положительным и не должен сильно превышать MD.")
    ensure_project_well_card(root, project_id, clean_well_id, clean_well_id)
    now = _utc_now()
    clean_id = safe_well_id(top_id or f"{clean_well_id}-{clean_name.lower().replace(' ', '-')}")
    top = ProjectFormationTop(
        id=clean_id,
        well_id=clean_well_id,
        name=clean_name,
        md_m=md_value,
        tvd_m=tvd_value,
        color=_clean_text(color, "Цвет", max_length=32),
        source=_clean_text(source, "Источник", max_length=80) or "manual",
        note=_clean_text(note, "Примечание", max_length=500),
        updated_at=now,
    )
    existing = [item for item in list_project_formation_tops(root, project_id) if item.id != clean_id]
    _save_items(root, project_id, PROJECT_FORMATION_TOPS_FILE_NAME, [top, *existing])
    append_project_history(root, project_id, "formation-top", f"Saved top {top.name} for well {clean_well_id}", object_type="well", object_id=clean_well_id)
    return top


def list_project_trajectory_stations(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str | None = None,
) -> tuple[ProjectTrajectoryStation, ...]:
    items = _load_items(root, project_id, PROJECT_WELL_TRAJECTORY_FILE_NAME, _station_from_dict)
    if well_id:
        clean_well_id = safe_well_id(well_id)
        items = tuple(item for item in items if item.well_id == clean_well_id)
    return tuple(sorted(items, key=lambda item: (item.well_id, item.md_m)))


def save_project_trajectory_station(
    root: Path | str,
    project_id: str,
    well_id: str,
    md_m: Any,
    inclination_deg: Any,
    azimuth_deg: Any,
    *,
    tvd_m: Any = None,
    north_m: Any = None,
    east_m: Any = None,
    source: str = "manual",
    station_id: str | None = None,
) -> ProjectTrajectoryStation:
    clean_well_id = safe_well_id(well_id)
    md_value = _required_float(md_m, "MD")
    inc_value = _required_float(inclination_deg, "Инклинометрия")
    az_value = _required_float(azimuth_deg, "Азимут")
    if md_value < 0 or md_value > 15000:
        raise ValueError("MD станции должен быть в диапазоне 0..15000 м.")
    if inc_value < 0 or inc_value > 180:
        raise ValueError("Инклинометрия должна быть в диапазоне 0..180 градусов.")
    if az_value < 0 or az_value >= 360:
        raise ValueError("Азимут должен быть в диапазоне 0..360 градусов.")
    ensure_project_well_card(root, project_id, clean_well_id, clean_well_id)
    now = _utc_now()
    clean_id = safe_well_id(station_id or f"{clean_well_id}-{int(round(md_value * 1000))}")
    station = ProjectTrajectoryStation(
        id=clean_id,
        well_id=clean_well_id,
        md_m=md_value,
        inclination_deg=inc_value,
        azimuth_deg=az_value,
        tvd_m=_optional_float(tvd_m, "TVD"),
        north_m=_optional_float(north_m, "North"),
        east_m=_optional_float(east_m, "East"),
        source=_clean_text(source, "Источник", max_length=80) or "manual",
        updated_at=now,
    )
    existing = [item for item in list_project_trajectory_stations(root, project_id) if item.id != clean_id]
    _save_items(root, project_id, PROJECT_WELL_TRAJECTORY_FILE_NAME, [station, *existing])
    append_project_history(root, project_id, "trajectory", f"Saved trajectory station {station.md_m:g} m for well {clean_well_id}", object_type="well", object_id=clean_well_id)
    return station


def list_project_well_notes(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str | None = None,
) -> tuple[ProjectWellNote, ...]:
    items = _load_items(root, project_id, PROJECT_WELL_NOTES_FILE_NAME, _note_from_dict)
    if well_id:
        clean_well_id = safe_well_id(well_id)
        items = tuple(item for item in items if item.well_id == clean_well_id)
    return tuple(sorted(items, key=lambda item: item.updated_at, reverse=True))


def save_project_well_note(
    root: Path | str,
    project_id: str,
    well_id: str,
    title: str,
    body: str,
    *,
    category: str = "general",
    note_id: str | None = None,
) -> ProjectWellNote:
    clean_well_id = safe_well_id(well_id)
    clean_title = _clean_text(title, "Заголовок", required=True)
    clean_body = _clean_text(body, "Текст заметки", max_length=2000, required=True)
    ensure_project_well_card(root, project_id, clean_well_id, clean_well_id)
    now = _utc_now()
    existing_notes = list_project_well_notes(root, project_id)
    clean_id = safe_well_id(note_id or f"{clean_well_id}-note-{len(existing_notes) + 1}")
    old = next((item for item in existing_notes if item.id == clean_id), None)
    note = ProjectWellNote(
        id=clean_id,
        well_id=clean_well_id,
        title=clean_title,
        body=clean_body,
        category=_clean_text(category, "Категория", max_length=80) or "general",
        created_at=old.created_at if old else now,
        updated_at=now,
    )
    _save_items(root, project_id, PROJECT_WELL_NOTES_FILE_NAME, [note, *(item for item in existing_notes if item.id != clean_id)])
    append_project_history(root, project_id, "well-note", f"Saved note {note.title} for well {clean_well_id}", object_type="well", object_id=clean_well_id)
    return note


def _count_by_well(items: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.well_id] = counts.get(item.well_id, 0) + 1
    return counts


def _well_completeness(card: ProjectWellCard, tops_count: int, stations_count: int, notes_count: int) -> int:
    checks = (
        bool(card.name),
        bool(card.field.field),
        bool(card.operator.operator),
        card.coordinates.has_any,
        card.depth_reference.has_kb,
        card.depth_reference.has_gl,
        card.depth_reference.has_td,
        tops_count > 0,
        stations_count > 0,
        notes_count > 0,
    )
    return int(round(sum(1 for value in checks if value) / len(checks) * 100))


def list_project_well_manager_records(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectWellManagerRecord, ...]:
    tops = _count_by_well(list_project_formation_tops(root, project_id))
    stations = _count_by_well(list_project_trajectory_stations(root, project_id))
    notes = _count_by_well(list_project_well_notes(root, project_id))
    records = []
    for card in list_project_well_cards(root, project_id):
        tops_count = tops.get(card.well_id, 0)
        stations_count = stations.get(card.well_id, 0)
        notes_count = notes.get(card.well_id, 0)
        records.append(
            ProjectWellManagerRecord(
                well_id=card.well_id,
                name=card.name,
                status=card.status,
                status_label=card.status_label,
                field=card.field.field or "",
                operator=card.operator.operator or "",
                kb_m=card.depth_reference.kb_m,
                gl_m=card.depth_reference.gl_m,
                planned_td_m=card.depth_reference.planned_td_m,
                actual_td_m=card.depth_reference.actual_td_m,
                tops_count=tops_count,
                trajectory_stations_count=stations_count,
                notes_count=notes_count,
                completeness_percent=_well_completeness(card, tops_count, stations_count, notes_count),
                updated_at=card.updated_at,
            )
        )
    return tuple(sorted(records, key=lambda item: (item.completeness_percent, item.updated_at), reverse=True))


def filter_project_well_manager_records(
    records: Iterable[ProjectWellManagerRecord],
    *,
    query: str = "",
    status: str = "",
    field: str = "",
    operator: str = "",
) -> tuple[ProjectWellManagerRecord, ...]:
    clean_query = query.strip().lower()
    clean_status = status.strip().lower()
    clean_field = field.strip().lower()
    clean_operator = operator.strip().lower()
    filtered = []
    for record in records:
        haystack = " ".join((record.well_id, record.name, record.status_label, record.field, record.operator)).lower()
        if clean_query and clean_query not in haystack:
            continue
        if clean_status and clean_status not in (record.status.lower(), record.status_label.lower()):
            continue
        if clean_field and clean_field not in record.field.lower():
            continue
        if clean_operator and clean_operator not in record.operator.lower():
            continue
        filtered.append(record)
    return tuple(filtered)


def build_project_well_manager_table(records: Iterable[ProjectWellManagerRecord]) -> list[dict[str, Any]]:
    return [
        {
            "Скважина": record.name,
            "ID": record.well_id,
            "Статус": record.status_label,
            "Месторождение": record.field or "—",
            "Оператор": record.operator or "—",
            "KB": record.kb_m if record.kb_m is not None else "—",
            "GL": record.gl_m if record.gl_m is not None else "—",
            "TD факт": record.actual_td_m if record.actual_td_m is not None else "—",
            "Пласты": record.tops_count,
            "Траектория": record.trajectory_stations_count,
            "Заметки": record.notes_count,
            "Готовность, %": record.completeness_percent,
        }
        for record in records
    ]


def project_well_manager_status(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> dict[str, int]:
    records = list_project_well_manager_records(root, project_id)
    return {
        "wells": len(records),
        "ready_wells": sum(1 for record in records if record.status == "ready"),
        "formation_tops": len(list_project_formation_tops(root, project_id)),
        "trajectory_stations": len(list_project_trajectory_stations(root, project_id)),
        "notes": len(list_project_well_notes(root, project_id)),
        "average_completeness_percent": int(round(sum(record.completeness_percent for record in records) / len(records))) if records else 0,
    }
