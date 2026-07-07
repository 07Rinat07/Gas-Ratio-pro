from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

STRUCTURAL_MODELING_WORKSPACE_FILE_NAME = "structural_modeling_workspace.json"
FAULT_TYPES = {"normal", "reverse", "strike_slip", "thrust", "unknown"}
SURFACE_ROLES = {"horizon", "fault", "contact", "top", "base", "map", "custom"}
LAYERING_METHODS = {"proportional", "parallel", "follow_top", "follow_base", "constant_thickness"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _workspace_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / STRUCTURAL_MODELING_WORKSPACE_FILE_NAME


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


def _choice(value: Any, label: str, choices: set[str], *, default: str) -> str:
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
class StructuralFramework:
    framework_id: str
    name: str
    model_id: str = ""
    description: str = ""
    coordinate_reference_system: str = ""
    status: str = "draft"
    author: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class StructuralHorizon:
    horizon_id: str
    name: str
    order: int
    surface_id: str = ""
    group_id: str = ""
    stratigraphic_unit: str = ""
    mean_depth: float | None = None
    min_depth: float | None = None
    max_depth: float | None = None
    status: str = "draft"


@dataclass(frozen=True)
class HorizonGroup:
    group_id: str
    name: str
    description: str = ""
    order: int = 0


@dataclass(frozen=True)
class StructuralFault:
    fault_id: str
    name: str
    fault_type: str = "unknown"
    surface_id: str = ""
    throw_m: float | None = None
    dip_deg: float | None = None
    azimuth_deg: float | None = None
    linked_horizon_ids: tuple[str, ...] = ()
    status: str = "draft"
    note: str = ""


@dataclass(frozen=True)
class StructuralZone:
    zone_id: str
    name: str
    top_horizon_id: str
    base_horizon_id: str
    order: int = 0
    layer_count: int = 1
    layering_method: str = "proportional"
    note: str = ""


@dataclass(frozen=True)
class StructuralLayer:
    layer_id: str
    zone_id: str
    name: str
    order: int
    thickness_m: float | None = None
    top_depth: float | None = None
    base_depth: float | None = None


@dataclass(frozen=True)
class StructuralSurface:
    surface_id: str
    name: str
    role: str = "horizon"
    file_path: str = ""
    min_z: float | None = None
    max_z: float | None = None
    source: str = ""
    status: str = "draft"


@dataclass(frozen=True)
class StructuralValidationIssue:
    severity: str
    code: str
    message: str
    object_type: str = ""
    object_id: str = ""


@dataclass(frozen=True)
class StructuralModelManifest:
    project_id: str
    generated_at: str
    framework_count: int
    horizon_count: int
    fault_count: int
    zone_count: int
    layer_count: int
    surface_count: int
    issue_count: int
    warning_count: int
    error_count: int


def _framework_to_dict(item: StructuralFramework) -> dict[str, Any]:
    return item.__dict__.copy()


def _framework_from_dict(raw: dict[str, Any]) -> StructuralFramework:
    return StructuralFramework(
        framework_id=_clean_text(raw.get("framework_id"), "Framework ID", required=True),
        name=_clean_text(raw.get("name"), "Название каркаса", required=True),
        model_id=_clean_text(raw.get("model_id"), "Model ID", max_length=120),
        description=_clean_text(raw.get("description"), "Описание", max_length=1200),
        coordinate_reference_system=_clean_text(raw.get("coordinate_reference_system"), "CRS", max_length=160),
        status=_clean_text(raw.get("status"), "Статус", max_length=60) or "draft",
        author=_clean_text(raw.get("author"), "Автор", max_length=120),
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80) or _now_iso(),
    )


def _horizon_to_dict(item: StructuralHorizon) -> dict[str, Any]:
    return item.__dict__.copy()


def _horizon_from_dict(raw: dict[str, Any]) -> StructuralHorizon:
    return StructuralHorizon(
        horizon_id=_clean_text(raw.get("horizon_id"), "Horizon ID", required=True),
        name=_clean_text(raw.get("name"), "Название горизонта", required=True),
        order=_to_int(raw.get("order", 0), "Порядок", default=0) or 0,
        surface_id=_clean_text(raw.get("surface_id"), "Surface ID", max_length=120),
        group_id=_clean_text(raw.get("group_id"), "Group ID", max_length=120),
        stratigraphic_unit=_clean_text(raw.get("stratigraphic_unit"), "Стратиграфия", max_length=160),
        mean_depth=_to_float(raw.get("mean_depth"), "Средняя глубина"),
        min_depth=_to_float(raw.get("min_depth"), "Минимальная глубина"),
        max_depth=_to_float(raw.get("max_depth"), "Максимальная глубина"),
        status=_clean_text(raw.get("status"), "Статус", max_length=60) or "draft",
    )


def _group_to_dict(item: HorizonGroup) -> dict[str, Any]:
    return item.__dict__.copy()


def _group_from_dict(raw: dict[str, Any]) -> HorizonGroup:
    return HorizonGroup(
        group_id=_clean_text(raw.get("group_id"), "Group ID", required=True),
        name=_clean_text(raw.get("name"), "Название группы", required=True),
        description=_clean_text(raw.get("description"), "Описание", max_length=600),
        order=_to_int(raw.get("order", 0), "Порядок", default=0) or 0,
    )


def _fault_to_dict(item: StructuralFault) -> dict[str, Any]:
    payload = item.__dict__.copy()
    payload["linked_horizon_ids"] = list(item.linked_horizon_ids)
    return payload


def _fault_from_dict(raw: dict[str, Any]) -> StructuralFault:
    links = raw.get("linked_horizon_ids") or []
    if isinstance(links, str):
        links = [part.strip() for part in links.split(",") if part.strip()]
    return StructuralFault(
        fault_id=_clean_text(raw.get("fault_id"), "Fault ID", required=True),
        name=_clean_text(raw.get("name"), "Название разлома", required=True),
        fault_type=_choice(raw.get("fault_type", "unknown"), "Тип разлома", FAULT_TYPES, default="unknown"),
        surface_id=_clean_text(raw.get("surface_id"), "Surface ID", max_length=120),
        throw_m=_to_float(raw.get("throw_m"), "Амплитуда смещения"),
        dip_deg=_to_float(raw.get("dip_deg"), "Угол падения"),
        azimuth_deg=_to_float(raw.get("azimuth_deg"), "Азимут"),
        linked_horizon_ids=tuple(_clean_text(x, "Horizon ID", max_length=120) for x in links if _clean_text(x, "Horizon ID", max_length=120)),
        status=_clean_text(raw.get("status"), "Статус", max_length=60) or "draft",
        note=_clean_text(raw.get("note"), "Примечание", max_length=1000),
    )


def _zone_to_dict(item: StructuralZone) -> dict[str, Any]:
    return item.__dict__.copy()


def _zone_from_dict(raw: dict[str, Any]) -> StructuralZone:
    layer_count = _to_int(raw.get("layer_count", 1), "Количество слоев", default=1) or 1
    if layer_count < 1:
        raise ValueError("Количество слоев должно быть больше нуля.")
    return StructuralZone(
        zone_id=_clean_text(raw.get("zone_id"), "Zone ID", required=True),
        name=_clean_text(raw.get("name"), "Название зоны", required=True),
        top_horizon_id=_clean_text(raw.get("top_horizon_id"), "Верхний горизонт", required=True),
        base_horizon_id=_clean_text(raw.get("base_horizon_id"), "Нижний горизонт", required=True),
        order=_to_int(raw.get("order", 0), "Порядок", default=0) or 0,
        layer_count=layer_count,
        layering_method=_choice(raw.get("layering_method", "proportional"), "Метод нарезки", LAYERING_METHODS, default="proportional"),
        note=_clean_text(raw.get("note"), "Примечание", max_length=1000),
    )


def _layer_to_dict(item: StructuralLayer) -> dict[str, Any]:
    return item.__dict__.copy()


def _layer_from_dict(raw: dict[str, Any]) -> StructuralLayer:
    return StructuralLayer(
        layer_id=_clean_text(raw.get("layer_id"), "Layer ID", required=True),
        zone_id=_clean_text(raw.get("zone_id"), "Zone ID", required=True),
        name=_clean_text(raw.get("name"), "Название слоя", required=True),
        order=_to_int(raw.get("order", 0), "Порядок", default=0) or 0,
        thickness_m=_to_float(raw.get("thickness_m"), "Толщина"),
        top_depth=_to_float(raw.get("top_depth"), "Кровля"),
        base_depth=_to_float(raw.get("base_depth"), "Подошва"),
    )


def _surface_to_dict(item: StructuralSurface) -> dict[str, Any]:
    return item.__dict__.copy()


def _surface_from_dict(raw: dict[str, Any]) -> StructuralSurface:
    return StructuralSurface(
        surface_id=_clean_text(raw.get("surface_id"), "Surface ID", required=True),
        name=_clean_text(raw.get("name"), "Название поверхности", required=True),
        role=_choice(raw.get("role", "horizon"), "Роль поверхности", SURFACE_ROLES, default="horizon"),
        file_path=_clean_text(raw.get("file_path"), "Файл", max_length=260),
        min_z=_to_float(raw.get("min_z"), "Min Z"),
        max_z=_to_float(raw.get("max_z"), "Max Z"),
        source=_clean_text(raw.get("source"), "Источник", max_length=260),
        status=_clean_text(raw.get("status"), "Статус", max_length=60) or "draft",
    )


def _empty_workspace() -> dict[str, Any]:
    return {
        "version": "1.0",
        "frameworks": [],
        "horizon_groups": [],
        "horizons": [],
        "faults": [],
        "zones": [],
        "layers": [],
        "surfaces": [],
        "updated_at": _now_iso(),
    }


def load_structural_modeling_workspace(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> dict[str, Any]:
    workspace = _json_read(_workspace_path(root, project_id), _empty_workspace())
    default = _empty_workspace()
    for key, value in default.items():
        workspace.setdefault(key, value)
    return workspace


def _save_workspace(workspace: dict[str, Any], project_id: str, root: Any) -> dict[str, Any]:
    workspace["updated_at"] = _now_iso()
    _json_write(_workspace_path(root, project_id), workspace)
    return workspace


def _upsert(workspace: dict[str, Any], key: str, id_field: str, payload: dict[str, Any]) -> None:
    items = [item for item in workspace.get(key, []) if item.get(id_field) != payload[id_field]]
    items.append(payload)
    workspace[key] = items


def save_structural_framework(framework: StructuralFramework | dict[str, Any], project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> StructuralFramework:
    item = framework if isinstance(framework, StructuralFramework) else _framework_from_dict(framework)
    workspace = load_structural_modeling_workspace(project_id, root)
    _upsert(workspace, "frameworks", "framework_id", _framework_to_dict(item))
    _save_workspace(workspace, project_id, root)
    append_project_history(root, project_id, "structural_framework_saved", f"Сохранен структурный каркас: {item.name}", object_type="structural_framework", object_id=item.framework_id)
    return item


def list_structural_frameworks(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[StructuralFramework]:
    return [_framework_from_dict(item) for item in load_structural_modeling_workspace(project_id, root).get("frameworks", [])]


def save_horizon_group(group: HorizonGroup | dict[str, Any], project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> HorizonGroup:
    item = group if isinstance(group, HorizonGroup) else _group_from_dict(group)
    workspace = load_structural_modeling_workspace(project_id, root)
    _upsert(workspace, "horizon_groups", "group_id", _group_to_dict(item))
    _save_workspace(workspace, project_id, root)
    return item


def list_horizon_groups(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[HorizonGroup]:
    return [_group_from_dict(item) for item in load_structural_modeling_workspace(project_id, root).get("horizon_groups", [])]


def save_structural_horizon(horizon: StructuralHorizon | dict[str, Any], project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> StructuralHorizon:
    item = horizon if isinstance(horizon, StructuralHorizon) else _horizon_from_dict(horizon)
    workspace = load_structural_modeling_workspace(project_id, root)
    _upsert(workspace, "horizons", "horizon_id", _horizon_to_dict(item))
    _save_workspace(workspace, project_id, root)
    return item


def list_structural_horizons(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[StructuralHorizon]:
    return sorted([_horizon_from_dict(item) for item in load_structural_modeling_workspace(project_id, root).get("horizons", [])], key=lambda item: item.order)


def save_structural_fault(fault: StructuralFault | dict[str, Any], project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> StructuralFault:
    item = fault if isinstance(fault, StructuralFault) else _fault_from_dict(fault)
    workspace = load_structural_modeling_workspace(project_id, root)
    _upsert(workspace, "faults", "fault_id", _fault_to_dict(item))
    _save_workspace(workspace, project_id, root)
    return item


def list_structural_faults(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[StructuralFault]:
    return [_fault_from_dict(item) for item in load_structural_modeling_workspace(project_id, root).get("faults", [])]


def save_structural_zone(zone: StructuralZone | dict[str, Any], project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> StructuralZone:
    item = zone if isinstance(zone, StructuralZone) else _zone_from_dict(zone)
    workspace = load_structural_modeling_workspace(project_id, root)
    _upsert(workspace, "zones", "zone_id", _zone_to_dict(item))
    _save_workspace(workspace, project_id, root)
    return item


def list_structural_zones(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[StructuralZone]:
    return sorted([_zone_from_dict(item) for item in load_structural_modeling_workspace(project_id, root).get("zones", [])], key=lambda item: item.order)


def save_structural_layer(layer: StructuralLayer | dict[str, Any], project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> StructuralLayer:
    item = layer if isinstance(layer, StructuralLayer) else _layer_from_dict(layer)
    workspace = load_structural_modeling_workspace(project_id, root)
    _upsert(workspace, "layers", "layer_id", _layer_to_dict(item))
    _save_workspace(workspace, project_id, root)
    return item


def list_structural_layers(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[StructuralLayer]:
    return sorted([_layer_from_dict(item) for item in load_structural_modeling_workspace(project_id, root).get("layers", [])], key=lambda item: (item.zone_id, item.order))


def save_structural_surface(surface: StructuralSurface | dict[str, Any], project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> StructuralSurface:
    item = surface if isinstance(surface, StructuralSurface) else _surface_from_dict(surface)
    workspace = load_structural_modeling_workspace(project_id, root)
    _upsert(workspace, "surfaces", "surface_id", _surface_to_dict(item))
    _save_workspace(workspace, project_id, root)
    return item


def list_structural_surfaces(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[StructuralSurface]:
    return [_surface_from_dict(item) for item in load_structural_modeling_workspace(project_id, root).get("surfaces", [])]


def generate_layers_for_zone(zone: StructuralZone, top_depth: float, base_depth: float) -> list[StructuralLayer]:
    if zone.layer_count < 1:
        raise ValueError("Количество слоев должно быть больше нуля.")
    if base_depth <= top_depth:
        raise ValueError("Подошва зоны должна быть глубже кровли.")
    thickness = (base_depth - top_depth) / zone.layer_count
    layers: list[StructuralLayer] = []
    for idx in range(zone.layer_count):
        layer_top = top_depth + idx * thickness
        layer_base = layer_top + thickness
        layers.append(StructuralLayer(
            layer_id=f"{zone.zone_id}_L{idx + 1:03d}",
            zone_id=zone.zone_id,
            name=f"{zone.name} Layer {idx + 1}",
            order=idx + 1,
            thickness_m=round(thickness, 6),
            top_depth=round(layer_top, 6),
            base_depth=round(layer_base, 6),
        ))
    return layers


def validate_structural_modeling_workspace(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[StructuralValidationIssue]:
    horizons = list_structural_horizons(project_id, root)
    horizon_ids = {item.horizon_id for item in horizons}
    surface_ids = {item.surface_id for item in list_structural_surfaces(project_id, root)}
    issues: list[StructuralValidationIssue] = []

    if not horizons:
        issues.append(StructuralValidationIssue("warning", "NO_HORIZONS", "В структурной модели нет горизонтов.", "workspace"))

    previous_order: int | None = None
    for horizon in horizons:
        if previous_order is not None and horizon.order == previous_order:
            issues.append(StructuralValidationIssue("warning", "DUPLICATE_HORIZON_ORDER", f"Повторяется порядок горизонта: {horizon.order}.", "horizon", horizon.horizon_id))
        previous_order = horizon.order
        if horizon.surface_id and horizon.surface_id not in surface_ids:
            issues.append(StructuralValidationIssue("warning", "MISSING_HORIZON_SURFACE", f"Поверхность горизонта не найдена: {horizon.surface_id}.", "horizon", horizon.horizon_id))
        if horizon.min_depth is not None and horizon.max_depth is not None and horizon.min_depth > horizon.max_depth:
            issues.append(StructuralValidationIssue("error", "INVALID_HORIZON_DEPTH_RANGE", "Минимальная глубина горизонта больше максимальной.", "horizon", horizon.horizon_id))

    for zone in list_structural_zones(project_id, root):
        if zone.top_horizon_id not in horizon_ids:
            issues.append(StructuralValidationIssue("error", "MISSING_TOP_HORIZON", f"Кровля зоны не найдена: {zone.top_horizon_id}.", "zone", zone.zone_id))
        if zone.base_horizon_id not in horizon_ids:
            issues.append(StructuralValidationIssue("error", "MISSING_BASE_HORIZON", f"Подошва зоны не найдена: {zone.base_horizon_id}.", "zone", zone.zone_id))
        if zone.top_horizon_id == zone.base_horizon_id:
            issues.append(StructuralValidationIssue("error", "SAME_TOP_BASE", "Кровля и подошва зоны не могут совпадать.", "zone", zone.zone_id))
        if zone.layer_count < 1:
            issues.append(StructuralValidationIssue("error", "INVALID_LAYER_COUNT", "Количество слоев зоны должно быть больше нуля.", "zone", zone.zone_id))

    for layer in list_structural_layers(project_id, root):
        if layer.top_depth is not None and layer.base_depth is not None and layer.base_depth <= layer.top_depth:
            issues.append(StructuralValidationIssue("error", "INVALID_LAYER_DEPTH", "Подошва слоя должна быть глубже кровли.", "layer", layer.layer_id))
        if layer.thickness_m is not None and layer.thickness_m <= 0:
            issues.append(StructuralValidationIssue("error", "INVALID_LAYER_THICKNESS", "Толщина слоя должна быть положительной.", "layer", layer.layer_id))

    for fault in list_structural_faults(project_id, root):
        if fault.surface_id and fault.surface_id not in surface_ids:
            issues.append(StructuralValidationIssue("warning", "MISSING_FAULT_SURFACE", f"Поверхность разлома не найдена: {fault.surface_id}.", "fault", fault.fault_id))
        for horizon_id in fault.linked_horizon_ids:
            if horizon_id not in horizon_ids:
                issues.append(StructuralValidationIssue("warning", "MISSING_FAULT_HORIZON_LINK", f"Связанный горизонт не найден: {horizon_id}.", "fault", fault.fault_id))

    return issues


def build_structural_modeling_manifest(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> StructuralModelManifest:
    issues = validate_structural_modeling_workspace(project_id, root)
    return StructuralModelManifest(
        project_id=safe_project_id(project_id),
        generated_at=_now_iso(),
        framework_count=len(list_structural_frameworks(project_id, root)),
        horizon_count=len(list_structural_horizons(project_id, root)),
        fault_count=len(list_structural_faults(project_id, root)),
        zone_count=len(list_structural_zones(project_id, root)),
        layer_count=len(list_structural_layers(project_id, root)),
        surface_count=len(list_structural_surfaces(project_id, root)),
        issue_count=len(issues),
        warning_count=sum(1 for item in issues if item.severity == "warning"),
        error_count=sum(1 for item in issues if item.severity == "error"),
    )


def manifest_to_dict(manifest: StructuralModelManifest) -> dict[str, Any]:
    return manifest.__dict__.copy()


def build_structural_horizon_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    return [{"ID": item.horizon_id, "Название": item.name, "Порядок": item.order, "Поверхность": item.surface_id, "Группа": item.group_id, "Средняя глубина": item.mean_depth, "Статус": item.status} for item in list_structural_horizons(project_id, root)]


def build_structural_fault_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    return [{"ID": item.fault_id, "Название": item.name, "Тип": item.fault_type, "Поверхность": item.surface_id, "Смещение, м": item.throw_m, "Связанные горизонты": ", ".join(item.linked_horizon_ids), "Статус": item.status} for item in list_structural_faults(project_id, root)]


def build_structural_zone_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    return [{"ID": item.zone_id, "Название": item.name, "Кровля": item.top_horizon_id, "Подошва": item.base_horizon_id, "Слоев": item.layer_count, "Метод": item.layering_method} for item in list_structural_zones(project_id, root)]


def build_structural_layer_table(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> list[dict[str, Any]]:
    return [{"ID": item.layer_id, "Зона": item.zone_id, "Название": item.name, "Порядок": item.order, "Толщина, м": item.thickness_m, "Кровля": item.top_depth, "Подошва": item.base_depth} for item in list_structural_layers(project_id, root)]


def render_structural_modeling_markdown(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> str:
    manifest = build_structural_modeling_manifest(project_id, root)
    issues = validate_structural_modeling_workspace(project_id, root)
    lines = [
        "# Structural Modeling Workspace",
        "",
        f"Project: `{manifest.project_id}`",
        f"Generated: `{manifest.generated_at}`",
        "",
        "## Summary",
        f"- Frameworks: {manifest.framework_count}",
        f"- Horizons: {manifest.horizon_count}",
        f"- Faults: {manifest.fault_count}",
        f"- Zones: {manifest.zone_count}",
        f"- Layers: {manifest.layer_count}",
        f"- Surfaces: {manifest.surface_count}",
        f"- Validation issues: {manifest.issue_count}",
        "",
        "## Horizons",
    ]
    for row in build_structural_horizon_table(project_id, root):
        lines.append(f"- `{row['ID']}` — {row['Название']} (order={row['Порядок']})")
    lines.extend(["", "## Faults"])
    for row in build_structural_fault_table(project_id, root):
        lines.append(f"- `{row['ID']}` — {row['Название']} ({row['Тип']})")
    lines.extend(["", "## Zones"])
    for row in build_structural_zone_table(project_id, root):
        lines.append(f"- `{row['ID']}` — {row['Название']}: {row['Кровля']} → {row['Подошва']}, layers={row['Слоев']}")
    lines.extend(["", "## Validation"])
    if not issues:
        lines.append("- No validation issues.")
    for issue in issues:
        lines.append(f"- **{issue.severity.upper()}** `{issue.code}` {issue.object_type}:{issue.object_id} — {issue.message}")
    return "\n".join(lines) + "\n"


def seed_structural_modeling_workspace(project_id: str = DEFAULT_PROJECT_ID, root: Any = DEFAULT_PROJECTS_ROOT) -> dict[str, Any]:
    framework = save_structural_framework({"framework_id": "structural_base", "name": "Base Structural Framework", "description": "Foundation structural model."}, project_id, root)
    save_horizon_group({"group_id": "main", "name": "Main Stratigraphy", "order": 1}, project_id, root)
    save_structural_surface({"surface_id": "surf_top", "name": "Top Surface", "role": "horizon", "min_z": 1000, "max_z": 1100}, project_id, root)
    save_structural_surface({"surface_id": "surf_base", "name": "Base Surface", "role": "horizon", "min_z": 1200, "max_z": 1300}, project_id, root)
    save_structural_horizon({"horizon_id": "top_res", "name": "Top Reservoir", "order": 1, "surface_id": "surf_top", "group_id": "main", "mean_depth": 1050}, project_id, root)
    save_structural_horizon({"horizon_id": "base_res", "name": "Base Reservoir", "order": 2, "surface_id": "surf_base", "group_id": "main", "mean_depth": 1250}, project_id, root)
    zone = save_structural_zone({"zone_id": "reservoir_zone", "name": "Reservoir Zone", "top_horizon_id": "top_res", "base_horizon_id": "base_res", "order": 1, "layer_count": 4}, project_id, root)
    for layer in generate_layers_for_zone(zone, 1050, 1250):
        save_structural_layer(layer, project_id, root)
    save_structural_fault({"fault_id": "fault_001", "name": "Fault 001", "fault_type": "normal", "linked_horizon_ids": ["top_res", "base_res"], "throw_m": 12.5}, project_id, root)
    return load_structural_modeling_workspace(project_id, root)
