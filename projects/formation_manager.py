from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import ensure_project_well_card, safe_well_id

PROJECT_FORMATION_MANAGER_FILE_NAME = "formation_manager.json"
FORMATION_OBJECT_TYPES = {"top", "contact", "horizon", "marker"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _formation_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_FORMATION_MANAGER_FILE_NAME


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


def _clean_text(value: Any, field_label: str, *, max_length: int = 160, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _optional_float(value: Any, field_label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if not value:
            return None
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


def _clean_object_type(value: Any) -> str:
    object_type = _clean_text(value, "Тип объекта", max_length=40).lower() or "top"
    if object_type not in FORMATION_OBJECT_TYPES:
        raise ValueError(f"Тип объекта должен быть одним из: {', '.join(sorted(FORMATION_OBJECT_TYPES))}.")
    return object_type


def _clean_id(value: str) -> str:
    return safe_well_id(value)


@dataclass(frozen=True)
class FormationObject:
    id: str
    object_type: str
    name: str
    well_id: str = ""
    md_m: float | None = None
    tvd_m: float | None = None
    color: str = ""
    source: str = "manual"
    note: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class FormationManagerSummary:
    objects: int
    tops: int
    contacts: int
    horizons: int
    markers: int
    wells: int


def _object_from_dict(raw: dict[str, Any]) -> FormationObject:
    return FormationObject(
        id=_clean_text(raw.get("id"), "ID", max_length=120, required=True),
        object_type=_clean_object_type(raw.get("object_type", "top")),
        name=_clean_text(raw.get("name"), "Название", required=True),
        well_id=safe_well_id(str(raw.get("well_id", ""))) if raw.get("well_id") else "",
        md_m=_optional_float(raw.get("md_m"), "MD"),
        tvd_m=_optional_float(raw.get("tvd_m"), "TVD"),
        color=_clean_text(raw.get("color"), "Цвет", max_length=32),
        source=_clean_text(raw.get("source", "manual"), "Источник", max_length=80) or "manual",
        note=_clean_text(raw.get("note"), "Примечание", max_length=500),
        updated_at=str(raw.get("updated_at", "")),
    )


def _to_dict(item: FormationObject) -> dict[str, Any]:
    return dict(item.__dict__)


def list_formation_objects(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    *,
    object_type: str = "",
    well_id: str = "",
) -> tuple[FormationObject, ...]:
    payload = _json_read(_formation_path(root, project_id), {"objects": []})
    rows = payload.get("objects", []) if isinstance(payload, dict) else []
    items: list[FormationObject] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            items.append(_object_from_dict(row))
        except ValueError:
            continue
    if object_type:
        clean_type = _clean_object_type(object_type)
        items = [item for item in items if item.object_type == clean_type]
    if well_id:
        clean_well_id = safe_well_id(well_id)
        items = [item for item in items if item.well_id == clean_well_id]
    return tuple(sorted(items, key=lambda item: (item.object_type, item.well_id, item.md_m if item.md_m is not None else -1, item.name.lower())))


def save_formation_object(
    root: Path | str,
    project_id: str,
    name: str,
    *,
    object_type: str = "top",
    well_id: str = "",
    md_m: Any = None,
    tvd_m: Any = None,
    color: str = "",
    source: str = "manual",
    note: str = "",
    object_id: str | None = None,
) -> FormationObject:
    clean_type = _clean_object_type(object_type)
    clean_name = _clean_text(name, "Название", required=True)
    clean_well_id = safe_well_id(well_id) if well_id else ""
    md_value = _optional_float(md_m, "MD")
    tvd_value = _optional_float(tvd_m, "TVD")
    if clean_type in {"top", "contact", "marker"} and md_value is None:
        raise ValueError("MD: значение обязательно для tops, contacts и markers.")
    if md_value is not None and (md_value < 0 or md_value > 15000):
        raise ValueError("MD должен быть в диапазоне 0..15000 м.")
    if tvd_value is not None and (tvd_value < 0 or (md_value is not None and tvd_value > md_value + 1000)):
        raise ValueError("TVD должен быть положительным и не должен сильно превышать MD.")
    if clean_well_id:
        ensure_project_well_card(root, project_id, clean_well_id, clean_well_id)
    now = _utc_now()
    clean_id = _clean_id(object_id or f"{clean_type}-{clean_well_id or 'field'}-{clean_name.lower().replace(' ', '-')}")
    item = FormationObject(
        id=clean_id,
        object_type=clean_type,
        name=clean_name,
        well_id=clean_well_id,
        md_m=md_value,
        tvd_m=tvd_value,
        color=_clean_text(color, "Цвет", max_length=32),
        source=_clean_text(source, "Источник", max_length=80) or "manual",
        note=_clean_text(note, "Примечание", max_length=500),
        updated_at=now,
    )
    existing = [row for row in list_formation_objects(root, project_id) if row.id != clean_id]
    _json_write(_formation_path(root, project_id), {"version": 1, "objects": [_to_dict(item), *[_to_dict(row) for row in existing]]})
    append_project_history(root, project_id, "formation-manager", f"Saved {clean_type} {clean_name}", object_type="formation", object_id=clean_id)
    return item


def filter_formation_objects(
    objects: Iterable[FormationObject],
    *,
    query: str = "",
    object_type: str = "",
    well_id: str = "",
) -> tuple[FormationObject, ...]:
    clean_query = query.strip().lower()
    clean_type = object_type.strip().lower()
    clean_well = safe_well_id(well_id) if well_id else ""
    result = []
    for item in objects:
        haystack = " ".join((item.id, item.object_type, item.name, item.well_id, item.source, item.note)).lower()
        if clean_query and clean_query not in haystack:
            continue
        if clean_type and item.object_type != clean_type:
            continue
        if clean_well and item.well_id != clean_well:
            continue
        result.append(item)
    return tuple(result)


def build_formation_manager_table(objects: Iterable[FormationObject]) -> list[dict[str, Any]]:
    return [
        {
            "Тип": item.object_type,
            "Название": item.name,
            "Скважина": item.well_id or "—",
            "MD": item.md_m if item.md_m is not None else "—",
            "TVD": item.tvd_m if item.tvd_m is not None else "—",
            "Цвет": item.color or "—",
            "Источник": item.source,
            "Примечание": item.note or "—",
        }
        for item in objects
    ]


def summarize_formation_manager(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> FormationManagerSummary:
    objects = list_formation_objects(root, project_id)
    return FormationManagerSummary(
        objects=len(objects),
        tops=sum(1 for item in objects if item.object_type == "top"),
        contacts=sum(1 for item in objects if item.object_type == "contact"),
        horizons=sum(1 for item in objects if item.object_type == "horizon"),
        markers=sum(1 for item in objects if item.object_type == "marker"),
        wells=len({item.well_id for item in objects if item.well_id}),
    )


def export_formation_objects_csv(objects: Iterable[FormationObject]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "object_type", "name", "well_id", "md_m", "tvd_m", "color", "source", "note", "updated_at"])
    writer.writeheader()
    for item in objects:
        writer.writerow(_to_dict(item))
    return output.getvalue()


def import_formation_objects_csv(root: Path | str, project_id: str, csv_text: str) -> tuple[FormationObject, ...]:
    reader = csv.DictReader(io.StringIO(csv_text))
    saved: list[FormationObject] = []
    for row in reader:
        saved.append(
            save_formation_object(
                root,
                project_id,
                row.get("name", ""),
                object_type=row.get("object_type", "top"),
                well_id=row.get("well_id", ""),
                md_m=row.get("md_m", ""),
                tvd_m=row.get("tvd_m", ""),
                color=row.get("color", ""),
                source=row.get("source", "csv"),
                note=row.get("note", ""),
                object_id=row.get("id") or None,
            )
        )
    return tuple(saved)
