from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Sequence

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

PROPERTY_MODELING_FILE_NAME = "property_modeling_workspace.json"

PROPERTY_TYPES = {
    "lithology",
    "facies",
    "net_gross",
    "porosity",
    "permeability",
    "water_saturation",
    "oil_saturation",
    "gas_saturation",
    "geometry",
    "fluid_contact",
}

DISCRETE_PROPERTY_TYPES = {"lithology", "facies", "net_gross", "fluid_contact"}
CONTINUOUS_PROPERTY_TYPES = PROPERTY_TYPES - DISCRETE_PROPERTY_TYPES
CONTACT_TYPES = {"owc", "goc", "gwc", "free_water_level", "custom"}
GEOMETRY_METHODS = {"cell_height", "cell_volume", "bulk_volume", "absolute_depth", "relative_depth", "above_contact"}
DEFAULT_SAND_FACIES = {"sand", "sandstone", "collector", "reservoir", "pay", "1", "true"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _workspace_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROPERTY_MODELING_FILE_NAME


def _clean_text(value: Any, label: str, *, required: bool = False, max_length: int = 180) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{label}: максимум {max_length} символов.")
    return text


def _clean_property_type(value: Any) -> str:
    prop_type = _clean_text(value, "Тип свойства", required=True, max_length=60).lower()
    if prop_type not in PROPERTY_TYPES:
        raise ValueError(f"Тип свойства должен быть одним из: {', '.join(sorted(PROPERTY_TYPES))}.")
    return prop_type


def _clean_contact_type(value: Any) -> str:
    contact_type = _clean_text(value, "Тип контакта", required=True, max_length=40).lower()
    if contact_type not in CONTACT_TYPES:
        raise ValueError(f"Тип контакта должен быть одним из: {', '.join(sorted(CONTACT_TYPES))}.")
    return contact_type


def _clean_geometry_method(value: Any) -> str:
    method = _clean_text(value, "Метод геометрического свойства", required=True, max_length=60).lower()
    if method not in GEOMETRY_METHODS:
        raise ValueError(f"Метод должен быть одним из: {', '.join(sorted(GEOMETRY_METHODS))}.")
    return method


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
class PropertyCubeSpec:
    """Metadata of a modeled reservoir property cube.

    The object intentionally stores metadata and lightweight statistics only. Actual 3D arrays
    should be stored by a dedicated grid backend later, while this registry keeps reproducible
    modeling context: source, algorithm, parameters, units and status.
    """

    name: str
    property_type: str
    unit: str = ""
    source: str = ""
    algorithm: str = "manual"
    parameters: dict[str, Any] = field(default_factory=dict)
    statistics: dict[str, float] = field(default_factory=dict)
    status: str = "draft"
    created_at: str = ""
    author: str = ""
    version: str = "1.0"
    note: str = ""


@dataclass(frozen=True)
class FluidContactSpec:
    name: str
    contact_type: str
    depth_m: float | None = None
    surface_path: str = ""
    zone: str = ""
    segment: str = ""
    note: str = ""


@dataclass(frozen=True)
class GeometryPropertySpec:
    name: str
    method: str
    unit: str = "m"
    contact_name: str = ""
    reference_depth_m: float | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PropertyModelingManifest:
    project_id: str
    generated_at: str
    property_count: int
    contact_count: int
    geometry_count: int
    discrete_count: int
    continuous_count: int
    warnings: tuple[str, ...] = ()


def _cube_to_dict(cube: PropertyCubeSpec) -> dict[str, Any]:
    return {
        "name": cube.name,
        "property_type": cube.property_type,
        "unit": cube.unit,
        "source": cube.source,
        "algorithm": cube.algorithm,
        "parameters": dict(cube.parameters),
        "statistics": dict(cube.statistics),
        "status": cube.status,
        "created_at": cube.created_at,
        "author": cube.author,
        "version": cube.version,
        "note": cube.note,
    }


def _cube_from_dict(raw: dict[str, Any]) -> PropertyCubeSpec:
    return PropertyCubeSpec(
        name=_clean_text(raw.get("name"), "Название свойства", required=True),
        property_type=_clean_property_type(raw.get("property_type")),
        unit=_clean_text(raw.get("unit"), "Единицы", max_length=40),
        source=_clean_text(raw.get("source"), "Источник", max_length=260),
        algorithm=_clean_text(raw.get("algorithm"), "Алгоритм", max_length=120) or "manual",
        parameters=raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {},
        statistics={str(k): float(v) for k, v in (raw.get("statistics") or {}).items() if isinstance(v, (int, float))},
        status=_clean_text(raw.get("status"), "Статус", max_length=60) or "draft",
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
        author=_clean_text(raw.get("author"), "Автор", max_length=120),
        version=_clean_text(raw.get("version"), "Версия", max_length=40) or "1.0",
        note=_clean_text(raw.get("note"), "Примечание", max_length=600),
    )


def _contact_to_dict(contact: FluidContactSpec) -> dict[str, Any]:
    return {
        "name": contact.name,
        "contact_type": contact.contact_type,
        "depth_m": contact.depth_m,
        "surface_path": contact.surface_path,
        "zone": contact.zone,
        "segment": contact.segment,
        "note": contact.note,
    }


def _contact_from_dict(raw: dict[str, Any]) -> FluidContactSpec:
    return FluidContactSpec(
        name=_clean_text(raw.get("name"), "Название контакта", required=True),
        contact_type=_clean_contact_type(raw.get("contact_type")),
        depth_m=_to_float(raw.get("depth_m"), "Глубина контакта"),
        surface_path=_clean_text(raw.get("surface_path"), "Поверхность", max_length=260),
        zone=_clean_text(raw.get("zone"), "Зона", max_length=120),
        segment=_clean_text(raw.get("segment"), "Сегмент", max_length=120),
        note=_clean_text(raw.get("note"), "Примечание", max_length=600),
    )


def _geometry_to_dict(geometry: GeometryPropertySpec) -> dict[str, Any]:
    return {
        "name": geometry.name,
        "method": geometry.method,
        "unit": geometry.unit,
        "contact_name": geometry.contact_name,
        "reference_depth_m": geometry.reference_depth_m,
        "parameters": dict(geometry.parameters),
    }


def _geometry_from_dict(raw: dict[str, Any]) -> GeometryPropertySpec:
    return GeometryPropertySpec(
        name=_clean_text(raw.get("name"), "Название геометрического свойства", required=True),
        method=_clean_geometry_method(raw.get("method")),
        unit=_clean_text(raw.get("unit"), "Единицы", max_length=40) or "m",
        contact_name=_clean_text(raw.get("contact_name"), "Контакт", max_length=120),
        reference_depth_m=_to_float(raw.get("reference_depth_m"), "Опорная глубина"),
        parameters=raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {},
    )


def load_property_modeling_workspace(
    root=DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> dict[str, Any]:
    default = {"properties": [], "fluid_contacts": [], "geometry_properties": [], "history": []}
    payload = _json_read(_workspace_path(root, project_id), default)
    if not isinstance(payload, dict):
        return default
    for key in default:
        if not isinstance(payload.get(key), list):
            payload[key] = []
    return payload


def list_property_cubes(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID, *, property_type: str = "") -> tuple[PropertyCubeSpec, ...]:
    payload = load_property_modeling_workspace(root, project_id)
    cubes: list[PropertyCubeSpec] = []
    for raw in payload.get("properties", []):
        if isinstance(raw, dict):
            try:
                cubes.append(_cube_from_dict(raw))
            except ValueError:
                continue
    if property_type:
        clean_type = _clean_property_type(property_type)
        cubes = [cube for cube in cubes if cube.property_type == clean_type]
    return tuple(sorted(cubes, key=lambda c: (c.property_type, c.name.lower())))


def save_property_cube(
    root,
    project_id: str,
    cube: PropertyCubeSpec | dict[str, Any],
    *,
    replace: bool = True,
    history_note: str = "",
) -> PropertyCubeSpec:
    normalized = _cube_from_dict(_cube_to_dict(cube) if isinstance(cube, PropertyCubeSpec) else cube)
    if not normalized.created_at:
        normalized = PropertyCubeSpec(**{**_cube_to_dict(normalized), "created_at": _now_iso()})
    payload = load_property_modeling_workspace(root, project_id)
    rows = payload.get("properties", [])
    exists = any(isinstance(row, dict) and str(row.get("name", "")).strip().lower() == normalized.name.lower() for row in rows)
    if exists and not replace:
        raise ValueError(f"Свойство '{normalized.name}' уже существует.")
    rows = [row for row in rows if not (isinstance(row, dict) and str(row.get("name", "")).strip().lower() == normalized.name.lower())]
    rows.append(_cube_to_dict(normalized))
    payload["properties"] = rows
    payload.setdefault("history", []).append({"event": "save_property_cube", "name": normalized.name, "at": _now_iso(), "note": history_note})
    _json_write(_workspace_path(root, project_id), payload)
    append_project_history(root, project_id, "property_modeling.save_property_cube", f"Saved property cube: {normalized.name}")
    return normalized


def list_fluid_contacts(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[FluidContactSpec, ...]:
    payload = load_property_modeling_workspace(root, project_id)
    contacts: list[FluidContactSpec] = []
    for raw in payload.get("fluid_contacts", []):
        if isinstance(raw, dict):
            try:
                contacts.append(_contact_from_dict(raw))
            except ValueError:
                continue
    return tuple(sorted(contacts, key=lambda c: (c.contact_type, c.name.lower())))


def save_fluid_contact(root, project_id: str, contact: FluidContactSpec | dict[str, Any], *, replace: bool = True) -> FluidContactSpec:
    normalized = _contact_from_dict(_contact_to_dict(contact) if isinstance(contact, FluidContactSpec) else contact)
    payload = load_property_modeling_workspace(root, project_id)
    rows = payload.get("fluid_contacts", [])
    exists = any(isinstance(row, dict) and str(row.get("name", "")).strip().lower() == normalized.name.lower() for row in rows)
    if exists and not replace:
        raise ValueError(f"Контакт '{normalized.name}' уже существует.")
    rows = [row for row in rows if not (isinstance(row, dict) and str(row.get("name", "")).strip().lower() == normalized.name.lower())]
    rows.append(_contact_to_dict(normalized))
    payload["fluid_contacts"] = rows
    payload.setdefault("history", []).append({"event": "save_fluid_contact", "name": normalized.name, "at": _now_iso()})
    _json_write(_workspace_path(root, project_id), payload)
    append_project_history(root, project_id, "property_modeling.save_fluid_contact", f"Saved fluid contact: {normalized.name}")
    return normalized


def list_geometry_properties(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[GeometryPropertySpec, ...]:
    payload = load_property_modeling_workspace(root, project_id)
    items: list[GeometryPropertySpec] = []
    for raw in payload.get("geometry_properties", []):
        if isinstance(raw, dict):
            try:
                items.append(_geometry_from_dict(raw))
            except ValueError:
                continue
    return tuple(sorted(items, key=lambda g: (g.method, g.name.lower())))


def save_geometry_property(root, project_id: str, geometry: GeometryPropertySpec | dict[str, Any], *, replace: bool = True) -> GeometryPropertySpec:
    normalized = _geometry_from_dict(_geometry_to_dict(geometry) if isinstance(geometry, GeometryPropertySpec) else geometry)
    payload = load_property_modeling_workspace(root, project_id)
    rows = payload.get("geometry_properties", [])
    exists = any(isinstance(row, dict) and str(row.get("name", "")).strip().lower() == normalized.name.lower() for row in rows)
    if exists and not replace:
        raise ValueError(f"Геометрическое свойство '{normalized.name}' уже существует.")
    rows = [row for row in rows if not (isinstance(row, dict) and str(row.get("name", "")).strip().lower() == normalized.name.lower())]
    rows.append(_geometry_to_dict(normalized))
    payload["geometry_properties"] = rows
    payload.setdefault("history", []).append({"event": "save_geometry_property", "name": normalized.name, "at": _now_iso()})
    _json_write(_workspace_path(root, project_id), payload)
    append_project_history(root, project_id, "property_modeling.save_geometry_property", f"Saved geometry property: {normalized.name}")
    return normalized


def _is_sand_value(value: Any, sand_values: Iterable[Any]) -> bool:
    normalized = str(value).strip().lower()
    normalized_sand = {str(item).strip().lower() for item in sand_values}
    return normalized in normalized_sand


def calculate_net_gross_from_facies(facies_values: Sequence[Any], *, sand_values: Iterable[Any] = DEFAULT_SAND_FACIES) -> tuple[int, ...]:
    """Create a 1/0 Net/Gross vector from a facies vector.

    This implements the common Petrel-style expression NG = If(Facies == Sand, 1, 0)
    but supports several sand/reservoir labels for imported projects.
    """

    return tuple(1 if _is_sand_value(value, sand_values) else 0 for value in facies_values)


def calculate_property_statistics(values: Iterable[Any], *, null_values: Iterable[Any] = (-999.25, None, "")) -> dict[str, float]:
    null_set = {str(v) for v in null_values}
    numbers: list[float] = []
    for value in values:
        if str(value) in null_set:
            continue
        number = _to_float(value, "Значение свойства")
        if number is not None:
            numbers.append(number)
    if not numbers:
        return {"count": 0.0}
    sorted_values = sorted(numbers)
    return {
        "count": float(len(numbers)),
        "min": round(sorted_values[0], 10),
        "max": round(sorted_values[-1], 10),
        "mean": round(mean(numbers), 10),
        "p50": round(sorted_values[len(sorted_values) // 2], 10),
    }


def build_net_gross_property_cube(
    facies_values: Sequence[Any],
    *,
    name: str = "NG",
    source: str = "facies",
    sand_values: Iterable[Any] = DEFAULT_SAND_FACIES,
    author: str = "",
) -> tuple[PropertyCubeSpec, tuple[int, ...]]:
    ng_values = calculate_net_gross_from_facies(facies_values, sand_values=sand_values)
    cube = PropertyCubeSpec(
        name=_clean_text(name, "Название NG", required=True),
        property_type="net_gross",
        unit="fraction",
        source=_clean_text(source, "Источник", max_length=260),
        algorithm="NG = If(Facies in sand_values, 1, 0)",
        parameters={"sand_values": sorted({str(v) for v in sand_values})},
        statistics=calculate_property_statistics(ng_values),
        status="computed",
        created_at=_now_iso(),
        author=_clean_text(author, "Автор", max_length=120),
        version="1.0",
        note="Foundation Net/Gross property generated from discrete facies/lithology labels.",
    )
    return cube, ng_values


def build_default_property_modeling_seed(author: str = "") -> dict[str, Any]:
    cubes = [
        PropertyCubeSpec("Facies", "facies", source="well_interpretation", algorithm="discrete_facies_model", status="planned", author=author),
        PropertyCubeSpec("NG", "net_gross", unit="fraction", source="Facies", algorithm="NG = If(Facies == Sand, 1, 0)", status="planned", author=author),
        PropertyCubeSpec("POR", "porosity", unit="fraction", source="petrophysical_workspace", algorithm="porosity_modeling_foundation", status="planned", author=author),
        PropertyCubeSpec("PERM", "permeability", unit="mD", source="petrophysical_workspace", algorithm="permeability_modeling_foundation", status="planned", author=author),
        PropertyCubeSpec("SW", "water_saturation", unit="fraction", source="advanced_saturation_models", algorithm="saturation_modeling_foundation", status="planned", author=author),
    ]
    contacts = [FluidContactSpec("OWC", "owc", note="Oil-water contact foundation."), FluidContactSpec("GOC", "goc", note="Gas-oil contact foundation.")]
    geometry = [
        GeometryPropertySpec("Bulk Volume", "bulk_volume", unit="m3"),
        GeometryPropertySpec("Above Contact", "above_contact", unit="m", contact_name="OWC"),
        GeometryPropertySpec("Absolute Depth", "absolute_depth", unit="m"),
    ]
    return {
        "properties": [_cube_to_dict(cube) for cube in cubes],
        "fluid_contacts": [_contact_to_dict(contact) for contact in contacts],
        "geometry_properties": [_geometry_to_dict(item) for item in geometry],
        "history": [{"event": "seed_property_modeling_workspace", "at": _now_iso()}],
    }


def seed_property_modeling_workspace(root, project_id: str, *, author: str = "", overwrite: bool = False) -> dict[str, Any]:
    path = _workspace_path(root, project_id)
    if path.exists() and not overwrite:
        return load_property_modeling_workspace(root, project_id)
    payload = build_default_property_modeling_seed(author=author)
    _json_write(path, payload)
    append_project_history(root, project_id, "property_modeling.seed", "Seeded property modeling workspace")
    return payload


def build_property_modeling_manifest(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> PropertyModelingManifest:
    cubes = list_property_cubes(root, project_id)
    contacts = list_fluid_contacts(root, project_id)
    geometry = list_geometry_properties(root, project_id)
    warnings: list[str] = []
    if not any(cube.property_type == "facies" for cube in cubes):
        warnings.append("Нет куба/свойства Facies.")
    if not any(cube.property_type == "net_gross" for cube in cubes):
        warnings.append("Нет свойства Net/Gross.")
    if not contacts:
        warnings.append("Не заданы флюидные контакты.")
    return PropertyModelingManifest(
        project_id=safe_project_id(project_id),
        generated_at=_now_iso(),
        property_count=len(cubes),
        contact_count=len(contacts),
        geometry_count=len(geometry),
        discrete_count=sum(1 for cube in cubes if cube.property_type in DISCRETE_PROPERTY_TYPES),
        continuous_count=sum(1 for cube in cubes if cube.property_type in CONTINUOUS_PROPERTY_TYPES),
        warnings=tuple(warnings),
    )


def build_property_cube_table(cubes: Iterable[PropertyCubeSpec]) -> list[dict[str, Any]]:
    return [
        {
            "name": cube.name,
            "type": cube.property_type,
            "unit": cube.unit,
            "source": cube.source,
            "algorithm": cube.algorithm,
            "status": cube.status,
            "count": cube.statistics.get("count", ""),
            "mean": cube.statistics.get("mean", ""),
        }
        for cube in cubes
    ]


def build_fluid_contact_table(contacts: Iterable[FluidContactSpec]) -> list[dict[str, Any]]:
    return [
        {
            "name": contact.name,
            "type": contact.contact_type,
            "depth_m": contact.depth_m if contact.depth_m is not None else "surface",
            "zone": contact.zone,
            "segment": contact.segment,
            "source": contact.surface_path or "constant",
        }
        for contact in contacts
    ]


def render_property_modeling_markdown(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> str:
    cubes = list_property_cubes(root, project_id)
    contacts = list_fluid_contacts(root, project_id)
    geometry = list_geometry_properties(root, project_id)
    manifest = build_property_modeling_manifest(root, project_id)
    lines = [
        "# Property Modeling Workspace Report",
        "",
        f"Project: `{manifest.project_id}`",
        f"Generated: `{manifest.generated_at}`",
        "",
        "## Summary",
        f"- Properties: {manifest.property_count}",
        f"- Fluid contacts: {manifest.contact_count}",
        f"- Geometry properties: {manifest.geometry_count}",
        f"- Discrete properties: {manifest.discrete_count}",
        f"- Continuous properties: {manifest.continuous_count}",
        "",
        "## Property Cubes",
        "| Name | Type | Unit | Source | Algorithm | Status |",
        "|---|---|---|---|---|---|",
    ]
    for cube in cubes:
        lines.append(f"| {cube.name} | {cube.property_type} | {cube.unit} | {cube.source} | {cube.algorithm} | {cube.status} |")
    lines.extend(["", "## Fluid Contacts", "| Name | Type | Depth/Surface | Zone | Segment |", "|---|---|---|---|---|"])
    for contact in contacts:
        depth = contact.depth_m if contact.depth_m is not None else contact.surface_path or "not set"
        lines.append(f"| {contact.name} | {contact.contact_type} | {depth} | {contact.zone} | {contact.segment} |")
    lines.extend(["", "## Geometry", "| Name | Method | Unit | Contact |", "|---|---|---|---|"])
    for item in geometry:
        lines.append(f"| {item.name} | {item.method} | {item.unit} | {item.contact_name} |")
    if manifest.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in manifest.warnings)
    return "\n".join(lines) + "\n"
