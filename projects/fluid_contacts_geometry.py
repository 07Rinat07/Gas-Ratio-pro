from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Sequence

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

FLUID_CONTACTS_GEOMETRY_FILE_NAME = "fluid_contacts_geometry.json"
CONTACT_TYPES = {"owc", "goc", "gwc", "fwl", "custom"}
CONTACT_SURFACE_TYPES = {"constant", "surface"}
GEOMETRY_PROPERTY_TYPES = {
    "cell_height",
    "cell_volume",
    "bulk_volume",
    "depth",
    "elevation",
    "relative_depth",
    "above_contact",
    "contact_set",
}
CONTACT_ZONE_CODES = {"gas": 1, "oil": 2, "water": 3, "unknown": 0}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _workspace_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / FLUID_CONTACTS_GEOMETRY_FILE_NAME


def _clean_text(value: Any, label: str, *, required: bool = False, max_length: int = 220) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{label}: максимум {max_length} символов.")
    return text


def _to_float(value: Any, label: str, *, required: bool = False) -> float | None:
    if value is None:
        if required:
            raise ValueError(f"{label}: значение обязательно.")
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if not value:
            if required:
                raise ValueError(f"{label}: значение обязательно.")
            return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: ожидается число.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label}: значение должно быть конечным числом.")
    return round(number, 10)


def _clean_contact_type(value: Any) -> str:
    contact_type = _clean_text(value, "Тип контакта", required=True, max_length=40).lower()
    if contact_type not in CONTACT_TYPES:
        raise ValueError(f"Тип контакта должен быть одним из: {', '.join(sorted(CONTACT_TYPES))}.")
    return contact_type


def _clean_surface_type(value: Any) -> str:
    surface_type = (_clean_text(value, "Тип поверхности", max_length=40) or "constant").lower()
    if surface_type not in CONTACT_SURFACE_TYPES:
        raise ValueError(f"Тип поверхности должен быть одним из: {', '.join(sorted(CONTACT_SURFACE_TYPES))}.")
    return surface_type


def _clean_geometry_type(value: Any) -> str:
    prop_type = _clean_text(value, "Тип геометрического свойства", required=True, max_length=60).lower()
    if prop_type not in GEOMETRY_PROPERTY_TYPES:
        raise ValueError(f"Тип геометрического свойства должен быть одним из: {', '.join(sorted(GEOMETRY_PROPERTY_TYPES))}.")
    return prop_type


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


@dataclass(frozen=True)
class FluidContact:
    name: str
    contact_type: str
    depth_m: float | None = None
    surface_type: str = "constant"
    surface_path: str = ""
    zone: str = ""
    segment: str = ""
    confidence: float | None = None
    source: str = "manual"
    note: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class GridCellGeometry:
    cell_id: str
    top_m: float
    base_m: float
    x_size_m: float = 1.0
    y_size_m: float = 1.0
    zone: str = ""
    segment: str = ""


@dataclass(frozen=True)
class GeometryProperty:
    cell_id: str
    property_name: str
    property_type: str
    value: float | int | str
    unit: str = ""


@dataclass(frozen=True)
class ContactSetCell:
    cell_id: str
    zone_code: int
    zone_name: str
    above_contact_m: float | None
    contact_name: str


@dataclass(frozen=True)
class FluidGeometryJob:
    job_id: str
    name: str
    contact_names: tuple[str, ...] = ()
    geometry_types: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)
    status: str = "draft"
    created_at: str = ""
    note: str = ""


@dataclass(frozen=True)
class FluidGeometryManifest:
    project_id: str
    generated_at: str
    contact_count: int
    job_count: int
    geometry_property_count: int
    warnings: tuple[str, ...] = ()


def _contact_to_dict(contact: FluidContact) -> dict[str, Any]:
    return {
        "name": contact.name,
        "contact_type": contact.contact_type,
        "depth_m": contact.depth_m,
        "surface_type": contact.surface_type,
        "surface_path": contact.surface_path,
        "zone": contact.zone,
        "segment": contact.segment,
        "confidence": contact.confidence,
        "source": contact.source,
        "note": contact.note,
        "created_at": contact.created_at,
    }


def _contact_from_dict(raw: dict[str, Any]) -> FluidContact:
    surface_type = _clean_surface_type(raw.get("surface_type"))
    depth_m = _to_float(raw.get("depth_m"), "Глубина контакта", required=surface_type == "constant")
    surface_path = _clean_text(raw.get("surface_path"), "Путь к поверхности", required=surface_type == "surface", max_length=260)
    confidence = _to_float(raw.get("confidence"), "Достоверность контакта")
    if confidence is not None and not 0 <= confidence <= 1:
        raise ValueError("Достоверность контакта должна быть в диапазоне 0..1.")
    return FluidContact(
        name=_clean_text(raw.get("name"), "Название контакта", required=True),
        contact_type=_clean_contact_type(raw.get("contact_type")),
        depth_m=depth_m,
        surface_type=surface_type,
        surface_path=surface_path,
        zone=_clean_text(raw.get("zone"), "Зона", max_length=120),
        segment=_clean_text(raw.get("segment"), "Сегмент", max_length=120),
        confidence=confidence,
        source=_clean_text(raw.get("source"), "Источник", max_length=260) or "manual",
        note=_clean_text(raw.get("note"), "Примечание", max_length=600),
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
    )


def _cell_from_dict(raw: dict[str, Any]) -> GridCellGeometry:
    top = _to_float(raw.get("top_m"), "Кровля ячейки", required=True)
    base = _to_float(raw.get("base_m"), "Подошва ячейки", required=True)
    if top is None or base is None:
        raise ValueError("Кровля и подошва ячейки обязательны.")
    if base < top:
        raise ValueError("Подошва ячейки не может быть меньше кровли.")
    x_size = _to_float(raw.get("x_size_m", 1.0), "Размер X", required=True) or 1.0
    y_size = _to_float(raw.get("y_size_m", 1.0), "Размер Y", required=True) or 1.0
    if x_size <= 0 or y_size <= 0:
        raise ValueError("Размеры ячейки должны быть положительными.")
    return GridCellGeometry(
        cell_id=_clean_text(raw.get("cell_id"), "ID ячейки", required=True, max_length=120),
        top_m=top,
        base_m=base,
        x_size_m=x_size,
        y_size_m=y_size,
        zone=_clean_text(raw.get("zone"), "Зона", max_length=120),
        segment=_clean_text(raw.get("segment"), "Сегмент", max_length=120),
    )


def _job_to_dict(job: FluidGeometryJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "name": job.name,
        "contact_names": list(job.contact_names),
        "geometry_types": list(job.geometry_types),
        "parameters": dict(job.parameters),
        "status": job.status,
        "created_at": job.created_at,
        "note": job.note,
    }


def _job_from_dict(raw: dict[str, Any]) -> FluidGeometryJob:
    geometry_types = tuple(_clean_geometry_type(item) for item in (raw.get("geometry_types") or []))
    return FluidGeometryJob(
        job_id=_clean_text(raw.get("job_id"), "ID задания", required=True, max_length=120),
        name=_clean_text(raw.get("name"), "Название задания", required=True),
        contact_names=tuple(_clean_text(item, "Контакт", max_length=120) for item in (raw.get("contact_names") or [])),
        geometry_types=geometry_types,
        parameters=raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {},
        status=_clean_text(raw.get("status"), "Статус", max_length=80) or "draft",
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
        note=_clean_text(raw.get("note"), "Примечание", max_length=600),
    )


def load_fluid_geometry_workspace(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    return _json_read(_workspace_path(root, project_id), {"contacts": [], "jobs": [], "history": []})


def save_fluid_contact(root, project_id: str, contact: FluidContact | dict[str, Any], *, replace: bool = True) -> FluidContact:
    normalized = _contact_from_dict(_contact_to_dict(contact) if isinstance(contact, FluidContact) else contact)
    if not normalized.created_at:
        normalized = FluidContact(**{**_contact_to_dict(normalized), "created_at": _now_iso()})
    payload = load_fluid_geometry_workspace(root, project_id)
    rows = payload.get("contacts", [])
    exists = any(isinstance(row, dict) and str(row.get("name", "")).strip().lower() == normalized.name.lower() for row in rows)
    if exists and not replace:
        raise ValueError(f"Флюидный контакт '{normalized.name}' уже существует.")
    rows = [row for row in rows if not (isinstance(row, dict) and str(row.get("name", "")).strip().lower() == normalized.name.lower())]
    rows.append(_contact_to_dict(normalized))
    payload["contacts"] = rows
    payload.setdefault("history", []).append({"event": "save_fluid_contact", "name": normalized.name, "at": _now_iso()})
    _json_write(_workspace_path(root, project_id), payload)
    append_project_history(root, project_id, "fluid_geometry.save_contact", f"Saved fluid contact: {normalized.name}")
    return normalized


def list_fluid_geometry_contacts(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[FluidContact, ...]:
    payload = load_fluid_geometry_workspace(root, project_id)
    contacts: list[FluidContact] = []
    for raw in payload.get("contacts", []):
        if isinstance(raw, dict):
            try:
                contacts.append(_contact_from_dict(raw))
            except ValueError:
                continue
    return tuple(sorted(contacts, key=lambda item: (item.contact_type, item.name.lower())))


def create_fluid_geometry_job(
    root,
    project_id: str,
    *,
    name: str,
    contact_names: Sequence[str] = (),
    geometry_types: Sequence[str] = ("cell_height", "cell_volume", "bulk_volume", "depth", "above_contact", "contact_set"),
    parameters: dict[str, Any] | None = None,
    status: str = "planned",
    note: str = "",
    replace: bool = True,
) -> FluidGeometryJob:
    clean_name = _clean_text(name, "Название задания", required=True)
    job_id = clean_name.lower().replace(" ", "_").replace("/", "_")
    job = FluidGeometryJob(
        job_id=job_id,
        name=clean_name,
        contact_names=tuple(_clean_text(item, "Контакт", max_length=120) for item in contact_names),
        geometry_types=tuple(_clean_geometry_type(item) for item in geometry_types),
        parameters=parameters or {},
        status=_clean_text(status, "Статус", max_length=80) or "planned",
        created_at=_now_iso(),
        note=_clean_text(note, "Примечание", max_length=600),
    )
    payload = load_fluid_geometry_workspace(root, project_id)
    rows = payload.get("jobs", [])
    exists = any(isinstance(row, dict) and row.get("job_id") == job.job_id for row in rows)
    if exists and not replace:
        raise ValueError(f"Задание '{job.job_id}' уже существует.")
    rows = [row for row in rows if not (isinstance(row, dict) and row.get("job_id") == job.job_id)]
    rows.append(_job_to_dict(job))
    payload["jobs"] = rows
    payload.setdefault("history", []).append({"event": "create_fluid_geometry_job", "job_id": job.job_id, "at": _now_iso()})
    _json_write(_workspace_path(root, project_id), payload)
    append_project_history(root, project_id, "fluid_geometry.create_job", f"Created fluid geometry job: {job.name}")
    return job


def list_fluid_geometry_jobs(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[FluidGeometryJob, ...]:
    payload = load_fluid_geometry_workspace(root, project_id)
    jobs: list[FluidGeometryJob] = []
    for raw in payload.get("jobs", []):
        if isinstance(raw, dict):
            try:
                jobs.append(_job_from_dict(raw))
            except ValueError:
                continue
    return tuple(sorted(jobs, key=lambda item: item.created_at or item.job_id))


def calculate_cell_height(cell: GridCellGeometry | dict[str, Any]) -> float:
    normalized = _cell_from_dict(cell) if isinstance(cell, dict) else cell
    return round(normalized.base_m - normalized.top_m, 10)


def calculate_cell_volume(cell: GridCellGeometry | dict[str, Any]) -> float:
    normalized = _cell_from_dict(cell) if isinstance(cell, dict) else cell
    return round(calculate_cell_height(normalized) * normalized.x_size_m * normalized.y_size_m, 10)


def calculate_bulk_volume(cells: Iterable[GridCellGeometry | dict[str, Any]]) -> float:
    return round(sum(calculate_cell_volume(cell) for cell in cells), 10)


def calculate_cell_mid_depth(cell: GridCellGeometry | dict[str, Any]) -> float:
    normalized = _cell_from_dict(cell) if isinstance(cell, dict) else cell
    return round((normalized.top_m + normalized.base_m) / 2.0, 10)


def calculate_above_contact(cell: GridCellGeometry | dict[str, Any], contact_depth_m: float) -> float:
    mid_depth = calculate_cell_mid_depth(cell)
    return round(float(contact_depth_m) - mid_depth, 10)


def classify_contact_zone(depth_m: float, *, owc_m: float | None = None, goc_m: float | None = None) -> str:
    """Classify a depth point relative to simple horizontal contacts.

    Depth is positive downward or TVD-like. For a common oil reservoir with optional gas cap:
    depths shallower than GOC are gas, between GOC and OWC are oil, deeper than OWC are water.
    If only OWC is available, depths above OWC are oil and depths below OWC are water.
    """

    depth = float(depth_m)
    if goc_m is not None and depth < float(goc_m):
        return "gas"
    if owc_m is not None and depth > float(owc_m):
        return "water"
    if owc_m is not None or goc_m is not None:
        return "oil"
    return "unknown"


def build_contact_set_cells(
    cells: Iterable[GridCellGeometry | dict[str, Any]],
    *,
    contact_name: str = "OWC",
    owc_m: float | None = None,
    goc_m: float | None = None,
) -> tuple[ContactSetCell, ...]:
    result: list[ContactSetCell] = []
    for raw_cell in cells:
        cell = _cell_from_dict(raw_cell) if isinstance(raw_cell, dict) else raw_cell
        mid = calculate_cell_mid_depth(cell)
        zone = classify_contact_zone(mid, owc_m=owc_m, goc_m=goc_m)
        above = calculate_above_contact(cell, owc_m) if owc_m is not None else None
        result.append(ContactSetCell(cell.cell_id, CONTACT_ZONE_CODES[zone], zone, above, contact_name))
    return tuple(result)


def build_geometry_properties(
    cells: Iterable[GridCellGeometry | dict[str, Any]],
    *,
    contact_depth_m: float | None = None,
    reference_depth_m: float | None = None,
) -> tuple[GeometryProperty, ...]:
    properties: list[GeometryProperty] = []
    for raw_cell in cells:
        cell = _cell_from_dict(raw_cell) if isinstance(raw_cell, dict) else raw_cell
        mid = calculate_cell_mid_depth(cell)
        properties.extend(
            [
                GeometryProperty(cell.cell_id, "Cell Height", "cell_height", calculate_cell_height(cell), "m"),
                GeometryProperty(cell.cell_id, "Cell Volume", "cell_volume", calculate_cell_volume(cell), "m3"),
                GeometryProperty(cell.cell_id, "Bulk Volume", "bulk_volume", calculate_cell_volume(cell), "m3"),
                GeometryProperty(cell.cell_id, "Depth", "depth", mid, "m"),
                GeometryProperty(cell.cell_id, "Elevation", "elevation", round(-mid, 10), "m"),
            ]
        )
        if reference_depth_m is not None:
            properties.append(GeometryProperty(cell.cell_id, "Relative Depth", "relative_depth", round(mid - float(reference_depth_m), 10), "m"))
        if contact_depth_m is not None:
            properties.append(GeometryProperty(cell.cell_id, "Above Contact", "above_contact", calculate_above_contact(cell, float(contact_depth_m)), "m"))
    return tuple(properties)


def summarize_geometry_properties(properties: Iterable[GeometryProperty]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[float]] = {}
    for prop in properties:
        if isinstance(prop.value, (int, float)):
            grouped.setdefault(prop.property_type, []).append(float(prop.value))
    summary: dict[str, dict[str, float]] = {}
    for prop_type, values in grouped.items():
        if values:
            summary[prop_type] = {
                "count": float(len(values)),
                "min": round(min(values), 10),
                "max": round(max(values), 10),
                "mean": round(mean(values), 10),
            }
    return summary


def build_fluid_geometry_manifest(
    root=DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    *,
    geometry_properties: Iterable[GeometryProperty] = (),
) -> FluidGeometryManifest:
    contacts = list_fluid_geometry_contacts(root, project_id)
    jobs = list_fluid_geometry_jobs(root, project_id)
    warnings: list[str] = []
    if not contacts:
        warnings.append("Не зарегистрированы флюидные контакты.")
    if not any(contact.contact_type == "owc" for contact in contacts):
        warnings.append("Не задан OWC/FWL для расчета Above Contact.")
    if not jobs:
        warnings.append("Нет заданий геометрического моделирования.")
    return FluidGeometryManifest(
        project_id=safe_project_id(project_id),
        generated_at=_now_iso(),
        contact_count=len(contacts),
        job_count=len(jobs),
        geometry_property_count=sum(1 for _ in geometry_properties),
        warnings=tuple(warnings),
    )


def build_fluid_contact_table(contacts: Iterable[FluidContact]) -> list[dict[str, Any]]:
    return [
        {
            "name": contact.name,
            "type": contact.contact_type.upper(),
            "surface_type": contact.surface_type,
            "depth_m": contact.depth_m if contact.depth_m is not None else "surface",
            "zone": contact.zone,
            "segment": contact.segment,
            "confidence": contact.confidence if contact.confidence is not None else "",
            "source": contact.surface_path or contact.source,
        }
        for contact in contacts
    ]


def build_geometry_property_table(properties: Iterable[GeometryProperty]) -> list[dict[str, Any]]:
    return [
        {
            "cell_id": prop.cell_id,
            "property": prop.property_name,
            "type": prop.property_type,
            "value": prop.value,
            "unit": prop.unit,
        }
        for prop in properties
    ]


def build_contact_set_table(cells: Iterable[ContactSetCell]) -> list[dict[str, Any]]:
    return [
        {
            "cell_id": cell.cell_id,
            "contact": cell.contact_name,
            "zone": cell.zone_name,
            "zone_code": cell.zone_code,
            "above_contact_m": cell.above_contact_m if cell.above_contact_m is not None else "",
        }
        for cell in cells
    ]


def seed_fluid_geometry_workspace(root, project_id: str, *, overwrite: bool = False) -> dict[str, Any]:
    path = _workspace_path(root, project_id)
    if path.exists() and not overwrite:
        return load_fluid_geometry_workspace(root, project_id)
    payload = {
        "contacts": [
            _contact_to_dict(FluidContact("OWC", "owc", depth_m=1683.0, confidence=0.8, note="Oil-water contact foundation.", created_at=_now_iso())),
            _contact_to_dict(FluidContact("GOC", "goc", depth_m=1610.0, confidence=0.6, note="Gas-oil contact foundation.", created_at=_now_iso())),
        ],
        "jobs": [
            _job_to_dict(
                FluidGeometryJob(
                    job_id="fluid_geometry_foundation",
                    name="Fluid Contacts & Geometry Foundation",
                    contact_names=("OWC", "GOC"),
                    geometry_types=("cell_height", "cell_volume", "bulk_volume", "depth", "elevation", "above_contact", "contact_set"),
                    status="planned",
                    created_at=_now_iso(),
                )
            )
        ],
        "history": [{"event": "seed_fluid_geometry_workspace", "at": _now_iso()}],
    }
    _json_write(path, payload)
    append_project_history(root, project_id, "fluid_geometry.seed", "Seeded fluid contacts and geometry workspace")
    return payload


def render_fluid_geometry_markdown(
    root=DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    *,
    geometry_properties: Iterable[GeometryProperty] = (),
    contact_set_cells: Iterable[ContactSetCell] = (),
) -> str:
    contacts = list_fluid_geometry_contacts(root, project_id)
    jobs = list_fluid_geometry_jobs(root, project_id)
    props = tuple(geometry_properties)
    contact_cells = tuple(contact_set_cells)
    manifest = build_fluid_geometry_manifest(root, project_id, geometry_properties=props)
    summary = summarize_geometry_properties(props)
    lines = [
        "# Fluid Contacts & Geometrical Properties Report",
        "",
        f"Project: `{manifest.project_id}`",
        f"Generated: `{manifest.generated_at}`",
        "",
        "## Summary",
        f"- Fluid contacts: {manifest.contact_count}",
        f"- Geometry jobs: {manifest.job_count}",
        f"- Geometry values: {manifest.geometry_property_count}",
    ]
    if manifest.warnings:
        lines.append("- Warnings: " + "; ".join(manifest.warnings))
    lines.extend(["", "## Fluid Contacts"])
    if contacts:
        lines.append("| Name | Type | Depth/Surface | Zone | Segment | Confidence |")
        lines.append("|---|---:|---:|---|---|---:|")
        for contact in contacts:
            depth = contact.depth_m if contact.depth_m is not None else contact.surface_path or "surface"
            conf = "" if contact.confidence is None else contact.confidence
            lines.append(f"| {contact.name} | {contact.contact_type.upper()} | {depth} | {contact.zone} | {contact.segment} | {conf} |")
    else:
        lines.append("No contacts registered.")
    lines.extend(["", "## Geometry Summary"])
    if summary:
        lines.append("| Property | Count | Min | Max | Mean |")
        lines.append("|---|---:|---:|---:|---:|")
        for prop_type, stats in sorted(summary.items()):
            lines.append(f"| {prop_type} | {stats['count']} | {stats['min']} | {stats['max']} | {stats['mean']} |")
    else:
        lines.append("No calculated geometry values were supplied to the report.")
    lines.extend(["", "## Contact Set Preview"])
    if contact_cells:
        lines.append("| Cell | Contact | Zone | Code | Above Contact, m |")
        lines.append("|---|---|---|---:|---:|")
        for cell in contact_cells[:20]:
            lines.append(f"| {cell.cell_id} | {cell.contact_name} | {cell.zone_name} | {cell.zone_code} | {cell.above_contact_m or ''} |")
    else:
        lines.append("No contact set cells were supplied to the report.")
    lines.extend(["", "## Jobs"])
    if jobs:
        lines.append("| Job | Status | Geometry Types | Contacts |")
        lines.append("|---|---|---|---|")
        for job in jobs:
            lines.append(f"| {job.name} | {job.status} | {', '.join(job.geometry_types)} | {', '.join(job.contact_names)} |")
    else:
        lines.append("No geometry jobs registered.")
    return "\n".join(lines) + "\n"
