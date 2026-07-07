from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

GEOLOGICAL_MODEL_WORKSPACE_FILE_NAME = "geological_model_workspace.json"
GRID_TYPES = {"corner_point", "cartesian", "stratigraphic", "pillar", "unstructured"}
SURFACE_TYPES = {"horizon", "fault", "contact", "top", "base", "map", "custom"}
FAULT_TYPES = {"normal", "reverse", "strike_slip", "thrust", "unknown"}
MODEL_LINK_TYPES = {"well", "interval", "facies", "property_cube", "volumetrics", "surface", "fault", "contact"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _workspace_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / GEOLOGICAL_MODEL_WORKSPACE_FILE_NAME


def _clean_text(value: Any, label: str, *, required: bool = False, max_length: int = 180) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{label}: максимум {max_length} символов.")
    return text


def _to_float(value: Any, label: str, *, required: bool = False) -> float | None:
    if value is None or value == "":
        if required:
            raise ValueError(f"{label}: значение обязательно.")
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: ожидается число.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label}: значение должно быть конечным числом.")
    return round(number, 10)


def _to_int(value: Any, label: str, *, required: bool = False, default: int | None = None) -> int | None:
    if value is None or value == "":
        if required:
            raise ValueError(f"{label}: значение обязательно.")
        return default
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: ожидается целое число.") from exc
    return number


def _clean_choice(value: Any, label: str, choices: set[str], *, default: str = "") -> str:
    text = _clean_text(value if value not in (None, "") else default, label, required=True, max_length=80).lower()
    if text not in choices:
        raise ValueError(f"{label}: допустимые значения: {', '.join(sorted(choices))}.")
    return text


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
class GeologicalModel:
    model_id: str
    name: str
    description: str = ""
    coordinate_reference_system: str = ""
    status: str = "draft"
    created_at: str = ""
    author: str = ""
    version: str = "1.0"


@dataclass(frozen=True)
class GridDefinition:
    grid_id: str
    name: str
    grid_type: str = "corner_point"
    ni: int = 0
    nj: int = 0
    nk: int = 0
    dx: float | None = None
    dy: float | None = None
    dz: float | None = None
    source: str = ""
    status: str = "draft"
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HorizonDefinition:
    horizon_id: str
    name: str
    order: int = 0
    surface_id: str = ""
    stratigraphic_unit: str = ""
    note: str = ""


@dataclass(frozen=True)
class ZoneDefinition:
    zone_id: str
    name: str
    top_horizon_id: str
    base_horizon_id: str
    layer_count: int = 1
    layering_method: str = "proportional"
    note: str = ""


@dataclass(frozen=True)
class SurfaceDefinition:
    surface_id: str
    name: str
    surface_type: str = "horizon"
    file_path: str = ""
    z_unit: str = "m"
    min_z: float | None = None
    max_z: float | None = None
    source: str = ""
    status: str = "draft"


@dataclass(frozen=True)
class FaultDefinition:
    fault_id: str
    name: str
    fault_type: str = "unknown"
    surface_id: str = ""
    throw_m: float | None = None
    status: str = "draft"
    note: str = ""


@dataclass(frozen=True)
class ModelLink:
    link_id: str
    link_type: str
    target_id: str
    target_name: str = ""
    role: str = "input"
    source_module: str = ""
    note: str = ""


@dataclass(frozen=True)
class GeologicalModelManifest:
    project_id: str
    generated_at: str
    model_count: int
    grid_count: int
    horizon_count: int
    zone_count: int
    surface_count: int
    fault_count: int
    link_count: int
    warnings: tuple[str, ...] = ()


def _model_to_dict(item: GeologicalModel) -> dict[str, Any]:
    return item.__dict__.copy()


def _model_from_dict(raw: dict[str, Any]) -> GeologicalModel:
    return GeologicalModel(
        model_id=_clean_text(raw.get("model_id"), "Model ID", required=True),
        name=_clean_text(raw.get("name"), "Название модели", required=True),
        description=_clean_text(raw.get("description"), "Описание", max_length=1200),
        coordinate_reference_system=_clean_text(raw.get("coordinate_reference_system"), "CRS", max_length=160),
        status=_clean_text(raw.get("status"), "Статус", max_length=60) or "draft",
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
        author=_clean_text(raw.get("author"), "Автор", max_length=120),
        version=_clean_text(raw.get("version"), "Версия", max_length=40) or "1.0",
    )


def _grid_to_dict(item: GridDefinition) -> dict[str, Any]:
    return item.__dict__.copy()


def _grid_from_dict(raw: dict[str, Any]) -> GridDefinition:
    ni = _to_int(raw.get("ni", 0), "NI", default=0) or 0
    nj = _to_int(raw.get("nj", 0), "NJ", default=0) or 0
    nk = _to_int(raw.get("nk", 0), "NK", default=0) or 0
    if min(ni, nj, nk) < 0:
        raise ValueError("Размеры грида не могут быть отрицательными.")
    return GridDefinition(
        grid_id=_clean_text(raw.get("grid_id"), "Grid ID", required=True),
        name=_clean_text(raw.get("name"), "Название грида", required=True),
        grid_type=_clean_choice(raw.get("grid_type", "corner_point"), "Тип грида", GRID_TYPES, default="corner_point"),
        ni=ni,
        nj=nj,
        nk=nk,
        dx=_to_float(raw.get("dx"), "DX"),
        dy=_to_float(raw.get("dy"), "DY"),
        dz=_to_float(raw.get("dz"), "DZ"),
        source=_clean_text(raw.get("source"), "Источник", max_length=260),
        status=_clean_text(raw.get("status"), "Статус", max_length=60) or "draft",
        parameters=raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {},
    )


def _horizon_to_dict(item: HorizonDefinition) -> dict[str, Any]:
    return item.__dict__.copy()


def _horizon_from_dict(raw: dict[str, Any]) -> HorizonDefinition:
    return HorizonDefinition(
        horizon_id=_clean_text(raw.get("horizon_id"), "Horizon ID", required=True),
        name=_clean_text(raw.get("name"), "Название горизонта", required=True),
        order=_to_int(raw.get("order", 0), "Порядок", default=0) or 0,
        surface_id=_clean_text(raw.get("surface_id"), "Surface ID", max_length=120),
        stratigraphic_unit=_clean_text(raw.get("stratigraphic_unit"), "Стратиграфия", max_length=160),
        note=_clean_text(raw.get("note"), "Примечание", max_length=600),
    )


def _zone_to_dict(item: ZoneDefinition) -> dict[str, Any]:
    return item.__dict__.copy()


def _zone_from_dict(raw: dict[str, Any]) -> ZoneDefinition:
    layers = _to_int(raw.get("layer_count", 1), "Количество слоев", required=True) or 1
    if layers <= 0:
        raise ValueError("Количество слоев должно быть больше нуля.")
    return ZoneDefinition(
        zone_id=_clean_text(raw.get("zone_id"), "Zone ID", required=True),
        name=_clean_text(raw.get("name"), "Название зоны", required=True),
        top_horizon_id=_clean_text(raw.get("top_horizon_id"), "Верхний горизонт", required=True),
        base_horizon_id=_clean_text(raw.get("base_horizon_id"), "Нижний горизонт", required=True),
        layer_count=layers,
        layering_method=_clean_text(raw.get("layering_method"), "Метод нарезки", max_length=80) or "proportional",
        note=_clean_text(raw.get("note"), "Примечание", max_length=600),
    )


def _surface_to_dict(item: SurfaceDefinition) -> dict[str, Any]:
    return item.__dict__.copy()


def _surface_from_dict(raw: dict[str, Any]) -> SurfaceDefinition:
    return SurfaceDefinition(
        surface_id=_clean_text(raw.get("surface_id"), "Surface ID", required=True),
        name=_clean_text(raw.get("name"), "Название поверхности", required=True),
        surface_type=_clean_choice(raw.get("surface_type", "horizon"), "Тип поверхности", SURFACE_TYPES, default="horizon"),
        file_path=_clean_text(raw.get("file_path"), "Файл поверхности", max_length=260),
        z_unit=_clean_text(raw.get("z_unit"), "Единицы Z", max_length=40) or "m",
        min_z=_to_float(raw.get("min_z"), "Min Z"),
        max_z=_to_float(raw.get("max_z"), "Max Z"),
        source=_clean_text(raw.get("source"), "Источник", max_length=260),
        status=_clean_text(raw.get("status"), "Статус", max_length=60) or "draft",
    )


def _fault_to_dict(item: FaultDefinition) -> dict[str, Any]:
    return item.__dict__.copy()


def _fault_from_dict(raw: dict[str, Any]) -> FaultDefinition:
    return FaultDefinition(
        fault_id=_clean_text(raw.get("fault_id"), "Fault ID", required=True),
        name=_clean_text(raw.get("name"), "Название нарушения", required=True),
        fault_type=_clean_choice(raw.get("fault_type", "unknown"), "Тип нарушения", FAULT_TYPES, default="unknown"),
        surface_id=_clean_text(raw.get("surface_id"), "Surface ID", max_length=120),
        throw_m=_to_float(raw.get("throw_m"), "Амплитуда смещения"),
        status=_clean_text(raw.get("status"), "Статус", max_length=60) or "draft",
        note=_clean_text(raw.get("note"), "Примечание", max_length=600),
    )


def _link_to_dict(item: ModelLink) -> dict[str, Any]:
    return item.__dict__.copy()


def _link_from_dict(raw: dict[str, Any]) -> ModelLink:
    return ModelLink(
        link_id=_clean_text(raw.get("link_id"), "Link ID", required=True),
        link_type=_clean_choice(raw.get("link_type"), "Тип связи", MODEL_LINK_TYPES),
        target_id=_clean_text(raw.get("target_id"), "Target ID", required=True),
        target_name=_clean_text(raw.get("target_name"), "Target name", max_length=180),
        role=_clean_text(raw.get("role"), "Роль", max_length=80) or "input",
        source_module=_clean_text(raw.get("source_module"), "Модуль", max_length=120),
        note=_clean_text(raw.get("note"), "Примечание", max_length=600),
    )


_COLLECTIONS = {
    "models": (_model_from_dict, _model_to_dict, "model_id"),
    "grids": (_grid_from_dict, _grid_to_dict, "grid_id"),
    "horizons": (_horizon_from_dict, _horizon_to_dict, "horizon_id"),
    "zones": (_zone_from_dict, _zone_to_dict, "zone_id"),
    "surfaces": (_surface_from_dict, _surface_to_dict, "surface_id"),
    "faults": (_fault_from_dict, _fault_to_dict, "fault_id"),
    "links": (_link_from_dict, _link_to_dict, "link_id"),
}


def load_geological_model_workspace(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    default = {key: [] for key in _COLLECTIONS}
    default["history"] = []
    payload = _json_read(_workspace_path(root, project_id), default)
    if not isinstance(payload, dict):
        return default
    for key in default:
        if not isinstance(payload.get(key), list):
            payload[key] = []
    return payload


def _list_items(root: Any, project_id: str, collection: str) -> tuple[Any, ...]:
    parser = _COLLECTIONS[collection][0]
    items = []
    for raw in load_geological_model_workspace(root, project_id).get(collection, []):
        if isinstance(raw, dict):
            try:
                items.append(parser(raw))
            except ValueError:
                continue
    return tuple(sorted(items, key=lambda item: getattr(item, _COLLECTIONS[collection][2]).lower()))


def _save_item(root: Any, project_id: str, collection: str, item: Any, *, replace: bool = True) -> Any:
    parser, serializer, key = _COLLECTIONS[collection]
    normalized = parser(serializer(item) if hasattr(item, "__dataclass_fields__") else item)
    payload = load_geological_model_workspace(root, project_id)
    rows = payload.get(collection, [])
    item_id = getattr(normalized, key)
    exists = any(isinstance(row, dict) and str(row.get(key, "")).strip().lower() == item_id.lower() for row in rows)
    if exists and not replace:
        raise ValueError(f"Объект '{item_id}' уже существует в коллекции {collection}.")
    rows = [row for row in rows if not (isinstance(row, dict) and str(row.get(key, "")).strip().lower() == item_id.lower())]
    rows.append(serializer(normalized))
    payload[collection] = rows
    payload.setdefault("history", []).append({"event": f"save_{collection}", "id": item_id, "at": _now_iso()})
    _json_write(_workspace_path(root, project_id), payload)
    append_project_history(root, project_id, f"geological_model.save_{collection}", f"Saved {collection}: {item_id}")
    return normalized


def list_geological_models(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[GeologicalModel, ...]:
    return _list_items(root, project_id, "models")


def save_geological_model(root, project_id: str, model: GeologicalModel | dict[str, Any], *, replace: bool = True) -> GeologicalModel:
    if isinstance(model, dict) and not model.get("created_at"):
        model = {**model, "created_at": _now_iso()}
    return _save_item(root, project_id, "models", model, replace=replace)


def list_grids(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[GridDefinition, ...]:
    return _list_items(root, project_id, "grids")


def save_grid(root, project_id: str, grid: GridDefinition | dict[str, Any], *, replace: bool = True) -> GridDefinition:
    return _save_item(root, project_id, "grids", grid, replace=replace)


def list_horizons(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[HorizonDefinition, ...]:
    return tuple(sorted(_list_items(root, project_id, "horizons"), key=lambda h: (h.order, h.name.lower())))


def save_horizon(root, project_id: str, horizon: HorizonDefinition | dict[str, Any], *, replace: bool = True) -> HorizonDefinition:
    return _save_item(root, project_id, "horizons", horizon, replace=replace)


def list_zones(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[ZoneDefinition, ...]:
    return _list_items(root, project_id, "zones")


def save_zone(root, project_id: str, zone: ZoneDefinition | dict[str, Any], *, replace: bool = True) -> ZoneDefinition:
    return _save_item(root, project_id, "zones", zone, replace=replace)


def list_surfaces(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[SurfaceDefinition, ...]:
    return _list_items(root, project_id, "surfaces")


def save_surface(root, project_id: str, surface: SurfaceDefinition | dict[str, Any], *, replace: bool = True) -> SurfaceDefinition:
    return _save_item(root, project_id, "surfaces", surface, replace=replace)


def list_faults(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[FaultDefinition, ...]:
    return _list_items(root, project_id, "faults")


def save_fault(root, project_id: str, fault: FaultDefinition | dict[str, Any], *, replace: bool = True) -> FaultDefinition:
    return _save_item(root, project_id, "faults", fault, replace=replace)


def list_model_links(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID, *, link_type: str = "") -> tuple[ModelLink, ...]:
    links = _list_items(root, project_id, "links")
    if link_type:
        clean = _clean_choice(link_type, "Тип связи", MODEL_LINK_TYPES)
        links = tuple(link for link in links if link.link_type == clean)
    return links


def save_model_link(root, project_id: str, link: ModelLink | dict[str, Any], *, replace: bool = True) -> ModelLink:
    return _save_item(root, project_id, "links", link, replace=replace)


def build_default_geological_model_seed(author: str = "") -> dict[str, Any]:
    model = GeologicalModel("geomodel_main", "Geological Model", "Integrated geological model foundation.", status="draft", created_at=_now_iso(), author=author)
    grid = GridDefinition("grid_main", "Main 3D Grid", "corner_point", ni=0, nj=0, nk=0, source="property_modeling_workspace")
    surfaces = [SurfaceDefinition("surf_top", "Top Reservoir", "horizon"), SurfaceDefinition("surf_base", "Base Reservoir", "horizon")]
    horizons = [HorizonDefinition("h_top", "Top Reservoir", 1, "surf_top"), HorizonDefinition("h_base", "Base Reservoir", 2, "surf_base")]
    zones = [ZoneDefinition("zone_reservoir", "Reservoir Zone", "h_top", "h_base", layer_count=1)]
    links = [
        ModelLink("link_property_cubes", "property_cube", "property_modeling_workspace", "Property Modeling Workspace", "input", "projects.property_modeling_workspace"),
        ModelLink("link_volumetrics", "volumetrics", "reservoir_volumetrics_workspace", "Reservoir Volumetrics", "output", "projects.reservoir_volumetrics_workspace"),
    ]
    return {
        "models": [_model_to_dict(model)],
        "grids": [_grid_to_dict(grid)],
        "horizons": [_horizon_to_dict(item) for item in horizons],
        "zones": [_zone_to_dict(item) for item in zones],
        "surfaces": [_surface_to_dict(item) for item in surfaces],
        "faults": [],
        "links": [_link_to_dict(item) for item in links],
        "history": [{"event": "seed_geological_model_workspace", "at": _now_iso()}],
    }


def seed_geological_model_workspace(root, project_id: str, *, author: str = "", overwrite: bool = False) -> dict[str, Any]:
    path = _workspace_path(root, project_id)
    if path.exists() and not overwrite:
        return load_geological_model_workspace(root, project_id)
    payload = build_default_geological_model_seed(author=author)
    _json_write(path, payload)
    append_project_history(root, project_id, "geological_model.seed", "Seeded geological model workspace")
    return payload


def validate_geological_model_workspace(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> list[dict[str, Any]]:
    horizons = {item.horizon_id for item in list_horizons(root, project_id)}
    surfaces = {item.surface_id for item in list_surfaces(root, project_id)}
    issues: list[dict[str, Any]] = []
    for horizon in list_horizons(root, project_id):
        if horizon.surface_id and horizon.surface_id not in surfaces:
            issues.append({"severity": "warning", "object": horizon.horizon_id, "message": "Horizon references missing surface."})
    for zone in list_zones(root, project_id):
        if zone.top_horizon_id not in horizons:
            issues.append({"severity": "error", "object": zone.zone_id, "message": "Zone top horizon is missing."})
        if zone.base_horizon_id not in horizons:
            issues.append({"severity": "error", "object": zone.zone_id, "message": "Zone base horizon is missing."})
        if zone.top_horizon_id == zone.base_horizon_id:
            issues.append({"severity": "error", "object": zone.zone_id, "message": "Zone top and base horizons must be different."})
    for fault in list_faults(root, project_id):
        if fault.surface_id and fault.surface_id not in surfaces:
            issues.append({"severity": "warning", "object": fault.fault_id, "message": "Fault references missing surface."})
    return issues


def build_geological_model_manifest(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> GeologicalModelManifest:
    issues = validate_geological_model_workspace(root, project_id)
    warnings = [f"{issue['severity']}: {issue['object']} - {issue['message']}" for issue in issues]
    models = list_geological_models(root, project_id)
    grids = list_grids(root, project_id)
    horizons = list_horizons(root, project_id)
    zones = list_zones(root, project_id)
    surfaces = list_surfaces(root, project_id)
    faults = list_faults(root, project_id)
    links = list_model_links(root, project_id)
    if not models:
        warnings.append("Нет объекта GeologicalModel.")
    if not grids:
        warnings.append("Нет грида геологической модели.")
    if not zones:
        warnings.append("Нет стратиграфических зон.")
    return GeologicalModelManifest(
        project_id=safe_project_id(project_id),
        generated_at=_now_iso(),
        model_count=len(models),
        grid_count=len(grids),
        horizon_count=len(horizons),
        zone_count=len(zones),
        surface_count=len(surfaces),
        fault_count=len(faults),
        link_count=len(links),
        warnings=tuple(warnings),
    )


def build_geological_model_table(models: Iterable[GeologicalModel]) -> list[dict[str, Any]]:
    return [{"model_id": m.model_id, "name": m.name, "status": m.status, "crs": m.coordinate_reference_system, "version": m.version} for m in models]


def build_grid_table(grids: Iterable[GridDefinition]) -> list[dict[str, Any]]:
    return [{"grid_id": g.grid_id, "name": g.name, "type": g.grid_type, "ni": g.ni, "nj": g.nj, "nk": g.nk, "status": g.status} for g in grids]


def build_horizon_zone_table(horizons: Iterable[HorizonDefinition], zones: Iterable[ZoneDefinition]) -> list[dict[str, Any]]:
    rows = [{"kind": "horizon", "id": h.horizon_id, "name": h.name, "top": "", "base": "", "layers": "", "order": h.order} for h in horizons]
    rows.extend({"kind": "zone", "id": z.zone_id, "name": z.name, "top": z.top_horizon_id, "base": z.base_horizon_id, "layers": z.layer_count, "order": ""} for z in zones)
    return rows


def build_surface_fault_table(surfaces: Iterable[SurfaceDefinition], faults: Iterable[FaultDefinition]) -> list[dict[str, Any]]:
    rows = [{"kind": "surface", "id": s.surface_id, "name": s.name, "type": s.surface_type, "source": s.source or s.file_path, "status": s.status} for s in surfaces]
    rows.extend({"kind": "fault", "id": f.fault_id, "name": f.name, "type": f.fault_type, "source": f.surface_id, "status": f.status} for f in faults)
    return rows


def render_geological_model_markdown(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> str:
    manifest = build_geological_model_manifest(root, project_id)
    lines = [
        "# Geological Model Workspace Report",
        "",
        f"Project: `{manifest.project_id}`",
        f"Generated: `{manifest.generated_at}`",
        "",
        "## Summary",
        f"- Geological models: {manifest.model_count}",
        f"- Grids: {manifest.grid_count}",
        f"- Horizons: {manifest.horizon_count}",
        f"- Zones: {manifest.zone_count}",
        f"- Surfaces: {manifest.surface_count}",
        f"- Faults: {manifest.fault_count}",
        f"- Links: {manifest.link_count}",
        "",
        "## Models",
        "| ID | Name | Status | CRS | Version |",
        "|---|---|---|---|---|",
    ]
    for item in list_geological_models(root, project_id):
        lines.append(f"| {item.model_id} | {item.name} | {item.status} | {item.coordinate_reference_system} | {item.version} |")
    lines.extend(["", "## Grids", "| ID | Name | Type | Size | Source | Status |", "|---|---|---|---|---|---|"])
    for grid in list_grids(root, project_id):
        lines.append(f"| {grid.grid_id} | {grid.name} | {grid.grid_type} | {grid.ni}x{grid.nj}x{grid.nk} | {grid.source} | {grid.status} |")
    lines.extend(["", "## Horizons and Zones", "| Kind | ID | Name | Top | Base | Layers |", "|---|---|---|---|---|---|"])
    for row in build_horizon_zone_table(list_horizons(root, project_id), list_zones(root, project_id)):
        lines.append(f"| {row['kind']} | {row['id']} | {row['name']} | {row['top']} | {row['base']} | {row['layers']} |")
    lines.extend(["", "## Surfaces and Faults", "| Kind | ID | Name | Type | Source | Status |", "|---|---|---|---|---|---|"])
    for row in build_surface_fault_table(list_surfaces(root, project_id), list_faults(root, project_id)):
        lines.append(f"| {row['kind']} | {row['id']} | {row['name']} | {row['type']} | {row['source']} | {row['status']} |")
    lines.extend(["", "## Model Links", "| ID | Type | Target | Role | Module |", "|---|---|---|---|---|"])
    for link in list_model_links(root, project_id):
        lines.append(f"| {link.link_id} | {link.link_type} | {link.target_name or link.target_id} | {link.role} | {link.source_module} |")
    if manifest.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in manifest.warnings)
    return "\n".join(lines) + "\n"
