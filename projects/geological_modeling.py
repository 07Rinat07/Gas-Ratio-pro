from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Any, Iterable

from projects.formation_manager import FormationObject, list_formation_objects
from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

PROJECT_GEOLOGICAL_MODELING_FILE_NAME = "geological_modeling.json"
GEOLOGICAL_ZONE_TYPES = {"formation", "reservoir", "seal", "source", "aquifer", "pay", "non_pay"}
CROSS_SECTION_NODE_TYPES = {"well", "top", "contact", "horizon", "fault", "zone"}


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


def _clean_zone_type(value: Any) -> str:
    zone_type = _clean_text(value, "Тип зоны", max_length=40).lower() or "formation"
    if zone_type not in GEOLOGICAL_ZONE_TYPES:
        raise ValueError(f"Тип зоны должен быть одним из: {', '.join(sorted(GEOLOGICAL_ZONE_TYPES))}.")
    return zone_type


def _clean_node_type(value: Any) -> str:
    node_type = _clean_text(value, "Тип узла", max_length=40).lower() or "well"
    if node_type not in CROSS_SECTION_NODE_TYPES:
        raise ValueError(f"Тип узла должен быть одним из: {', '.join(sorted(CROSS_SECTION_NODE_TYPES))}.")
    return node_type


@dataclass(frozen=True)
class StratigraphicZone:
    """Stratigraphic or reservoir interval prepared for cross-section/geological model work."""

    name: str
    top_name: str
    base_name: str
    well_id: str = ""
    top_md_m: float | None = None
    base_md_m: float | None = None
    zone_type: str = "formation"
    color: str = ""
    note: str = ""

    @property
    def thickness_m(self) -> float | None:
        if self.top_md_m is None or self.base_md_m is None:
            return None
        return round(max(0.0, self.base_md_m - self.top_md_m), 6)


@dataclass(frozen=True)
class ReservoirZone:
    """Reservoir quality summary tied to a stratigraphic zone."""

    zone_name: str
    well_id: str = ""
    gross_m: float = 0.0
    net_m: float = 0.0
    avg_vsh: float | None = None
    avg_phie: float | None = None
    avg_sw: float | None = None
    quality: str = "unknown"
    note: str = ""

    @property
    def ntg(self) -> float:
        return round(self.net_m / self.gross_m, 6) if self.gross_m > 0 else 0.0


@dataclass(frozen=True)
class CrossSectionNode:
    """Geometry/control point for a future geological cross-section renderer."""

    id: str
    name: str
    node_type: str = "well"
    well_id: str = ""
    x: float = 0.0
    md_m: float | None = None
    tvd_m: float | None = None
    color: str = ""
    note: str = ""


@dataclass(frozen=True)
class GeologicalModelSummary:
    zones: int
    reservoir_zones: int
    nodes: int
    wells: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class GeologicalModelState:
    zones: tuple[StratigraphicZone, ...]
    reservoir_zones: tuple[ReservoirZone, ...]
    cross_section_nodes: tuple[CrossSectionNode, ...]
    summary: GeologicalModelSummary


def _project_dir(root: Any, project_id: str) -> Any:
    from pathlib import Path

    return Path(root) / safe_project_id(project_id)


def _geological_modeling_path(root: Any, project_id: str) -> Any:
    return _project_dir(root, project_id) / PROJECT_GEOLOGICAL_MODELING_FILE_NAME


def _json_read(path: Any, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _json_write(path: Any, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _zone_to_dict(zone: StratigraphicZone) -> dict[str, Any]:
    return dict(zone.__dict__)


def _zone_from_dict(raw: dict[str, Any]) -> StratigraphicZone:
    top = _required_float(raw.get("top_md_m"), "Top MD")
    base = _required_float(raw.get("base_md_m"), "Base MD")
    if top < 0 or base < 0:
        raise ValueError("Top/Base MD должны быть положительными.")
    if base <= top:
        raise ValueError("Base MD должен быть глубже Top MD.")
    return StratigraphicZone(
        name=_clean_text(raw.get("name"), "Название зоны", required=True),
        top_name=_clean_text(raw.get("top_name"), "Top", required=True),
        base_name=_clean_text(raw.get("base_name"), "Base", required=True),
        well_id=safe_well_id(raw.get("well_id", "")) if raw.get("well_id") else "",
        top_md_m=round(top, 6),
        base_md_m=round(base, 6),
        zone_type=_clean_zone_type(raw.get("zone_type", "formation")),
        color=_clean_text(raw.get("color"), "Цвет", max_length=32),
        note=_clean_text(raw.get("note"), "Примечание", max_length=500),
    )


def list_project_geological_zones(
    root=DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    *,
    well_id: str = "",
    zone_type: str = "",
) -> tuple[StratigraphicZone, ...]:
    """Load manually managed geological zones from project storage.

    These zones are the editable Zone Manager layer. They do not replace derived
    intervals from Formation Manager; instead, they store engineer-approved zones
    with explicit names, colors and notes.
    """

    payload = _json_read(_geological_modeling_path(root, project_id), {"zones": []})
    rows = payload.get("zones", []) if isinstance(payload, dict) else []
    zones: list[StratigraphicZone] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            zones.append(_zone_from_dict(row))
        except ValueError:
            continue
    clean_well = safe_well_id(well_id) if well_id else ""
    clean_type = _clean_zone_type(zone_type) if zone_type else ""
    if clean_well:
        zones = [zone for zone in zones if zone.well_id == clean_well]
    if clean_type:
        zones = [zone for zone in zones if zone.zone_type == clean_type]
    return tuple(sorted(zones, key=lambda z: (z.well_id, z.top_md_m or -1, z.base_md_m or -1, z.name.lower())))


def save_project_geological_zone(
    root,
    project_id: str,
    name: str,
    *,
    top_name: str,
    base_name: str,
    top_md_m: Any,
    base_md_m: Any,
    well_id: str = "",
    zone_type: str = "formation",
    color: str = "",
    note: str = "",
) -> StratigraphicZone:
    """Create or update a Zone Manager interval by ``(well_id, name)`` key."""

    zone = _zone_from_dict(
        {
            "name": name,
            "top_name": top_name,
            "base_name": base_name,
            "top_md_m": top_md_m,
            "base_md_m": base_md_m,
            "well_id": well_id,
            "zone_type": zone_type,
            "color": color,
            "note": note,
        }
    )
    existing = [
        item
        for item in list_project_geological_zones(root, project_id)
        if not (item.well_id == zone.well_id and item.name.lower() == zone.name.lower())
    ]
    _json_write(_geological_modeling_path(root, project_id), {"version": 1, "zones": [_zone_to_dict(zone), *[_zone_to_dict(item) for item in existing]]})
    append_project_history(root, project_id, "geological-zone-manager", f"Saved zone {zone.name}", object_type="geological_zone", object_id=f"{zone.well_id}:{zone.name}")
    return zone


def delete_project_geological_zone(root, project_id: str, name: str, *, well_id: str = "") -> bool:
    clean_name = _clean_text(name, "Название зоны", required=True).lower()
    clean_well = safe_well_id(well_id) if well_id else ""
    zones = list_project_geological_zones(root, project_id)
    kept = [zone for zone in zones if not (zone.name.lower() == clean_name and zone.well_id == clean_well)]
    if len(kept) == len(zones):
        return False
    _json_write(_geological_modeling_path(root, project_id), {"version": 1, "zones": [_zone_to_dict(item) for item in kept]})
    append_project_history(root, project_id, "geological-zone-manager", f"Deleted zone {name}", object_type="geological_zone", object_id=f"{clean_well}:{name}")
    return True


def merge_stratigraphic_zones(zones: Iterable[StratigraphicZone], name: str, *, zone_type: str = "formation", color: str = "", note: str = "") -> StratigraphicZone:
    selected = tuple(zones)
    if len(selected) < 2:
        raise ValueError("Для объединения нужно минимум две зоны.")
    wells = {zone.well_id for zone in selected}
    if len(wells) > 1:
        raise ValueError("Объединять можно только зоны одной скважины.")
    ordered = sorted(selected, key=lambda z: z.top_md_m if z.top_md_m is not None else -1)
    for left, right in zip(ordered, ordered[1:]):
        if left.base_md_m is None or right.top_md_m is None or abs(left.base_md_m - right.top_md_m) > 1e-6:
            raise ValueError("Для объединения зоны должны быть смежными без разрыва.")
    return StratigraphicZone(
        name=_clean_text(name, "Название зоны", required=True),
        top_name=ordered[0].top_name,
        base_name=ordered[-1].base_name,
        well_id=ordered[0].well_id,
        top_md_m=ordered[0].top_md_m,
        base_md_m=ordered[-1].base_md_m,
        zone_type=_clean_zone_type(zone_type or ordered[0].zone_type),
        color=_clean_text(color or ordered[0].color, "Цвет", max_length=32),
        note=_clean_text(note or "Merged zone", "Примечание", max_length=500),
    )


def split_stratigraphic_zone(zone: StratigraphicZone, split_md_m: Any, *, upper_name: str = "", lower_name: str = "", split_marker_name: str = "") -> tuple[StratigraphicZone, StratigraphicZone]:
    split = _required_float(split_md_m, "Глубина разделения")
    if zone.top_md_m is None or zone.base_md_m is None:
        raise ValueError("У зоны должны быть заданы Top/Base MD.")
    if split <= zone.top_md_m or split >= zone.base_md_m:
        raise ValueError("Глубина разделения должна находиться внутри зоны.")
    marker = _clean_text(split_marker_name or f"Split {split:g}", "Маркер разделения", max_length=120)
    upper = StratigraphicZone(
        name=_clean_text(upper_name or f"{zone.name} upper", "Название верхней зоны", required=True),
        top_name=zone.top_name,
        base_name=marker,
        well_id=zone.well_id,
        top_md_m=zone.top_md_m,
        base_md_m=round(split, 6),
        zone_type=zone.zone_type,
        color=zone.color,
        note=zone.note,
    )
    lower = StratigraphicZone(
        name=_clean_text(lower_name or f"{zone.name} lower", "Название нижней зоны", required=True),
        top_name=marker,
        base_name=zone.base_name,
        well_id=zone.well_id,
        top_md_m=round(split, 6),
        base_md_m=zone.base_md_m,
        zone_type=zone.zone_type,
        color=zone.color,
        note=zone.note,
    )
    return upper, lower


def build_zone_color_scheme(zones: Iterable[StratigraphicZone], palette: Iterable[str] = ()) -> dict[str, str]:
    colors = tuple(palette) or ("#4C78A8", "#F58518", "#54A24B", "#B279A2", "#E45756", "#72B7B2")
    scheme: dict[str, str] = {}
    for zone in zones:
        key = zone.name
        if zone.color:
            scheme[key] = zone.color
        elif key not in scheme:
            scheme[key] = colors[len(scheme) % len(colors)]
    return scheme


def build_zone_manager_table(zones: Iterable[StratigraphicZone]) -> tuple[dict[str, Any], ...]:
    rows = []
    for zone in zones:
        rows.append(
            {
                "Скважина": zone.well_id or "field",
                "Зона": zone.name,
                "Тип": zone.zone_type,
                "Top": zone.top_name,
                "Base": zone.base_name,
                "Top MD, м": zone.top_md_m,
                "Base MD, м": zone.base_md_m,
                "Толщина, м": zone.thickness_m,
                "Цвет": zone.color or "—",
                "Примечание": zone.note or "—",
            }
        )
    return tuple(rows)


def build_stratigraphic_zones_from_tops(
    formation_objects: Iterable[FormationObject],
    *,
    zone_type: str = "formation",
    color: str = "",
) -> tuple[StratigraphicZone, ...]:
    """Build intervals between consecutive tops for every well.

    The function keeps the original formation manager as source of truth and derives
    model-ready zones without mutating tops/markers. Only objects of type ``top``
    with a valid measured depth are used.
    """

    clean_type = _clean_zone_type(zone_type)
    tops_by_well: dict[str, list[FormationObject]] = {}
    for item in formation_objects:
        if item.object_type != "top" or item.md_m is None:
            continue
        tops_by_well.setdefault(item.well_id or "field", []).append(item)

    zones: list[StratigraphicZone] = []
    for well_id, tops in tops_by_well.items():
        ordered = sorted(tops, key=lambda item: (float(item.md_m or 0), item.name.lower()))
        for top, base in zip(ordered, ordered[1:]):
            zones.append(
                StratigraphicZone(
                    name=f"{top.name}-{base.name}",
                    top_name=top.name,
                    base_name=base.name,
                    well_id="" if well_id == "field" else well_id,
                    top_md_m=top.md_m,
                    base_md_m=base.md_m,
                    zone_type=clean_type,
                    color=color or top.color,
                    note="Derived from formation tops",
                )
            )
    return tuple(zones)


def normalize_reservoir_zones(rows: Iterable[dict[str, Any]]) -> tuple[ReservoirZone, ...]:
    zones: list[ReservoirZone] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        name = _clean_text(raw.get("zone_name") or raw.get("name"), "Название зоны", required=True)
        gross = _required_float(raw.get("gross_m", raw.get("gross", 0.0)), "Gross")
        net = _required_float(raw.get("net_m", raw.get("net", 0.0)), "Net")
        if gross < 0 or net < 0:
            raise ValueError("Gross и Net должны быть положительными.")
        if net > gross:
            raise ValueError("Net не должен превышать Gross.")
        zones.append(
            ReservoirZone(
                zone_name=name,
                well_id=safe_well_id(raw.get("well_id", "")) if raw.get("well_id") else "",
                gross_m=round(gross, 6),
                net_m=round(net, 6),
                avg_vsh=_optional_float(raw.get("avg_vsh"), "VSH"),
                avg_phie=_optional_float(raw.get("avg_phie"), "PHIE"),
                avg_sw=_optional_float(raw.get("avg_sw"), "SW"),
                quality=_classify_reservoir_quality(raw.get("quality"), raw.get("avg_vsh"), raw.get("avg_phie"), raw.get("avg_sw"), net, gross),
                note=_clean_text(raw.get("note"), "Примечание", max_length=500),
            )
        )
    return tuple(zones)


def _classify_reservoir_quality(quality: Any, vsh: Any, phie: Any, sw: Any, net: float, gross: float) -> str:
    explicit = _clean_text(quality, "Качество", max_length=40).lower()
    if explicit and explicit != "unknown":
        return explicit
    vsh_value = _optional_float(vsh, "VSH")
    phie_value = _optional_float(phie, "PHIE")
    sw_value = _optional_float(sw, "SW")
    ntg = net / gross if gross > 0 else 0.0
    if phie_value is not None and sw_value is not None and vsh_value is not None:
        if phie_value >= 0.16 and sw_value <= 0.45 and vsh_value <= 0.35 and ntg >= 0.5:
            return "good"
        if phie_value >= 0.10 and sw_value <= 0.65 and vsh_value <= 0.50 and ntg >= 0.25:
            return "fair"
        return "poor"
    if ntg >= 0.5:
        return "good"
    if ntg >= 0.25:
        return "fair"
    return "poor"


def build_cross_section_nodes(
    formation_objects: Iterable[FormationObject],
    *,
    well_spacing_m: float = 500.0,
) -> tuple[CrossSectionNode, ...]:
    spacing = _required_float(well_spacing_m, "Шаг между скважинами")
    if spacing <= 0:
        raise ValueError("Шаг между скважинами должен быть положительным.")
    well_order: list[str] = []
    for item in formation_objects:
        if item.well_id and item.well_id not in well_order:
            well_order.append(item.well_id)
    well_x = {well_id: index * spacing for index, well_id in enumerate(well_order)}

    nodes: list[CrossSectionNode] = []
    for item in formation_objects:
        node_type = "top" if item.object_type == "top" else item.object_type if item.object_type in CROSS_SECTION_NODE_TYPES else "horizon"
        x = well_x.get(item.well_id, 0.0)
        node_id = f"{node_type}-{item.well_id or 'field'}-{item.name}".lower().replace(" ", "-")
        nodes.append(
            CrossSectionNode(
                id=node_id,
                name=item.name,
                node_type=node_type,
                well_id=item.well_id,
                x=x,
                md_m=item.md_m,
                tvd_m=item.tvd_m,
                color=item.color,
                note=item.note,
            )
        )
    return tuple(nodes)


def validate_stratigraphic_zones(zones: Iterable[StratigraphicZone]) -> dict[str, tuple[str, ...]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[tuple[str, str]] = set()
    for zone in zones:
        key = (zone.well_id, zone.name.lower())
        if key in seen:
            warnings.append(f"Дублирующаяся зона: {zone.name} ({zone.well_id or 'field'}).")
        seen.add(key)
        if zone.top_md_m is None or zone.base_md_m is None:
            errors.append(f"Зона {zone.name}: не задан top/base depth.")
            continue
        if zone.base_md_m <= zone.top_md_m:
            errors.append(f"Зона {zone.name}: base должен быть глубже top.")
        if zone.thickness_m is not None and zone.thickness_m < 0.1:
            warnings.append(f"Зона {zone.name}: толщина меньше 0.1 м.")
    return {"errors": tuple(errors), "warnings": tuple(warnings)}


def build_geological_model_state(
    formation_objects: Iterable[FormationObject],
    *,
    reservoir_rows: Iterable[dict[str, Any]] = (),
    well_spacing_m: float = 500.0,
) -> GeologicalModelState:
    objects = tuple(formation_objects)
    zones = build_stratigraphic_zones_from_tops(objects)
    reservoirs = normalize_reservoir_zones(reservoir_rows)
    nodes = build_cross_section_nodes(objects, well_spacing_m=well_spacing_m)
    validation = validate_stratigraphic_zones(zones)
    wells = {item.well_id for item in objects if item.well_id}
    summary = GeologicalModelSummary(
        zones=len(zones),
        reservoir_zones=len(reservoirs),
        nodes=len(nodes),
        wells=len(wells),
        warnings=tuple((*validation["errors"], *validation["warnings"])),
    )
    return GeologicalModelState(zones=zones, reservoir_zones=reservoirs, cross_section_nodes=nodes, summary=summary)


def load_project_geological_model_state(
    root=DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    *,
    reservoir_rows: Iterable[dict[str, Any]] = (),
    well_spacing_m: float = 500.0,
) -> GeologicalModelState:
    return build_geological_model_state(
        list_formation_objects(root, project_id),
        reservoir_rows=reservoir_rows,
        well_spacing_m=well_spacing_m,
    )


def build_stratigraphic_zone_table(zones: Iterable[StratigraphicZone]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "Скважина": zone.well_id or "field",
            "Зона": zone.name,
            "Тип": zone.zone_type,
            "Top": zone.top_name,
            "Base": zone.base_name,
            "Top MD, м": zone.top_md_m,
            "Base MD, м": zone.base_md_m,
            "Толщина, м": zone.thickness_m,
            "Примечание": zone.note,
        }
        for zone in zones
    )


def build_reservoir_zone_table(zones: Iterable[ReservoirZone]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "Скважина": zone.well_id or "field",
            "Зона": zone.zone_name,
            "Gross, м": zone.gross_m,
            "Net, м": zone.net_m,
            "NTG": zone.ntg,
            "VSH": zone.avg_vsh,
            "PHIE": zone.avg_phie,
            "SW": zone.avg_sw,
            "Качество": zone.quality,
            "Примечание": zone.note,
        }
        for zone in zones
    )


def build_cross_section_node_table(nodes: Iterable[CrossSectionNode]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "ID": node.id,
            "Название": node.name,
            "Тип": node.node_type,
            "Скважина": node.well_id or "field",
            "X, м": node.x,
            "MD, м": node.md_m,
            "TVD, м": node.tvd_m,
            "Цвет": node.color,
        }
        for node in nodes
    )


def export_geological_model_csv(state: GeologicalModelState) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "well", "name", "type", "top", "base", "top_md_m", "base_md_m", "thickness_m", "x_m", "md_m", "tvd_m", "quality"])
    for zone in state.zones:
        writer.writerow(["zone", zone.well_id, zone.name, zone.zone_type, zone.top_name, zone.base_name, zone.top_md_m, zone.base_md_m, zone.thickness_m, "", "", "", ""])
    for zone in state.reservoir_zones:
        writer.writerow(["reservoir", zone.well_id, zone.zone_name, "reservoir", "", "", "", "", zone.net_m, "", "", "", zone.quality])
    for node in state.cross_section_nodes:
        writer.writerow(["node", node.well_id, node.name, node.node_type, "", "", "", "", "", node.x, node.md_m, node.tvd_m, ""])
    return output.getvalue()
