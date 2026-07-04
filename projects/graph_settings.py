from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id


INTERPRETATION_GRAPH_SETTINGS_FILE_NAME = "interpretation_graph_settings.json"
INTERPRETATION_GRAPH_SETTINGS_SCHEMA_VERSION = 1
DEFAULT_INTERPRETATION_TRACKS: tuple[str, ...] = (
    "Интерпретация",
    "C1-C5",
    "Wh/Bh/Ch",
    "Pixler ratios",
)


@dataclass(frozen=True)
class InterpretationGraphSettings:
    selected_tracks: tuple[str, ...] = DEFAULT_INTERPRETATION_TRACKS
    height: int = 650
    depth_range: tuple[float, float] | None = None
    gas_x_range: tuple[float, float] | None = None
    ratio_x_range: tuple[float, float] | None = None
    pixler_x_range: tuple[float, float] | None = None
    tablet_tracks: tuple[str, ...] = ()
    tablet_x_ranges: dict[str, tuple[float, float]] = field(default_factory=dict)
    tablet_colors: dict[str, str] = field(default_factory=dict)
    tablet_fill_modes: dict[str, str] = field(default_factory=dict)
    tablet_markers: tuple[dict[str, Any], ...] = ()
    tablet_zones: tuple[dict[str, Any], ...] = ()
    tablet_fill: bool = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _settings_path(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / INTERPRETATION_GRAPH_SETTINGS_FILE_NAME


def _range_to_list(value: tuple[float, float] | None) -> list[float] | None:
    if value is None:
        return None
    return [float(value[0]), float(value[1])]


def _range_from_raw(raw: object) -> tuple[float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        return None
    try:
        first = float(raw[0])
        second = float(raw[1])
    except (TypeError, ValueError):
        return None
    if first == second:
        return None
    return (min(first, second), max(first, second))


def _ranges_to_dict(value: dict[str, tuple[float, float]] | None) -> dict[str, list[float]]:
    if not value:
        return {}
    result: dict[str, list[float]] = {}
    for key, range_value in value.items():
        normalized = _range_from_raw(range_value)
        if normalized is not None:
            result[str(key)] = _range_to_list(normalized) or []
    return result


def _ranges_from_raw(raw: object) -> dict[str, tuple[float, float]]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, tuple[float, float]] = {}
    for key, value in raw.items():
        normalized = _range_from_raw(value)
        if normalized is not None:
            result[str(key)] = normalized
    return result



def _colors_from_raw(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    colors: dict[str, str] = {}
    for key, value in raw.items():
        column = str(key).strip()
        color = str(value).strip()
        if column and color.startswith("#") and len(color) in {4, 7}:
            colors[column] = color
    return colors

def _fill_modes_from_raw(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    allowed = {"none", "to_zero", "to_left", "to_right"}
    aliases = {
        "": "none",
        "line": "none",
        "false": "none",
        "no": "none",
        "none": "none",
        "true": "to_zero",
        "zero": "to_zero",
        "to_zero": "to_zero",
        "tozerox": "to_zero",
        "left": "to_left",
        "to_left": "to_left",
        "right": "to_right",
        "to_right": "to_right",
    }
    result: dict[str, str] = {}
    for key, value in raw.items():
        column = str(key).strip()
        mode = aliases.get(str(value or "").strip().lower(), str(value or "").strip().lower())
        if column and mode in allowed:
            result[column] = mode
    return result


def _markers_from_raw(raw: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, list):
        return ()
    markers: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            depth = float(item.get("depth"))
        except (TypeError, ValueError):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            label = chr(ord("a") + len(markers))
        markers.append(
            {
                "label": label,
                "depth": depth,
                "note": str(item.get("note") or ""),
            }
        )
    return tuple(markers)



def _zones_from_raw(raw: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, list):
        return ()
    zones: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            top_depth = float(item.get("top_depth"))
            bottom_depth = float(item.get("bottom_depth"))
        except (TypeError, ValueError):
            continue
        if top_depth == bottom_depth:
            continue
        label = str(item.get("label") or "").strip() or f"Zone {len(zones) + 1}"
        color = str(item.get("color") or "#ffd966").strip()
        if not color.startswith("#"):
            color = "#ffd966"
        zones.append(
            {
                "label": label,
                "top_depth": min(top_depth, bottom_depth),
                "bottom_depth": max(top_depth, bottom_depth),
                "color": color,
                "note": str(item.get("note") or ""),
            }
        )
    return tuple(zones)

def settings_to_dict(settings: InterpretationGraphSettings) -> dict[str, Any]:
    return {
        "selected_tracks": list(settings.selected_tracks),
        "height": int(settings.height),
        "depth_range": _range_to_list(settings.depth_range),
        "gas_x_range": _range_to_list(settings.gas_x_range),
        "ratio_x_range": _range_to_list(settings.ratio_x_range),
        "pixler_x_range": _range_to_list(settings.pixler_x_range),
        "tablet_tracks": list(settings.tablet_tracks),
        "tablet_x_ranges": _ranges_to_dict(settings.tablet_x_ranges),
        "tablet_colors": dict(settings.tablet_colors),
        "tablet_fill_modes": dict(settings.tablet_fill_modes),
        "tablet_markers": list(settings.tablet_markers),
        "tablet_zones": list(settings.tablet_zones),
        "tablet_fill": bool(settings.tablet_fill),
    }


def settings_from_dict(raw: object) -> InterpretationGraphSettings:
    payload = raw if isinstance(raw, dict) else {}
    selected_tracks = tuple(str(track) for track in payload.get("selected_tracks", ()) if str(track))
    height = payload.get("height", 650)
    try:
        height_value = int(height)
    except (TypeError, ValueError):
        height_value = 650

    return InterpretationGraphSettings(
        selected_tracks=selected_tracks or DEFAULT_INTERPRETATION_TRACKS,
        height=max(420, min(1100, height_value)),
        depth_range=_range_from_raw(payload.get("depth_range")),
        gas_x_range=_range_from_raw(payload.get("gas_x_range")),
        ratio_x_range=_range_from_raw(payload.get("ratio_x_range")),
        pixler_x_range=_range_from_raw(payload.get("pixler_x_range")),
        tablet_tracks=tuple(str(track) for track in payload.get("tablet_tracks", ()) if str(track)),
        tablet_x_ranges=_ranges_from_raw(payload.get("tablet_x_ranges")),
        tablet_colors=_colors_from_raw(payload.get("tablet_colors")),
        tablet_fill_modes=_fill_modes_from_raw(payload.get("tablet_fill_modes")),
        tablet_markers=_markers_from_raw(payload.get("tablet_markers")),
        tablet_zones=_zones_from_raw(payload.get("tablet_zones")),
        tablet_fill=bool(payload.get("tablet_fill", False)),
    )


def save_project_interpretation_graph_settings(
    settings: InterpretationGraphSettings,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> Path:
    path = _settings_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": INTERPRETATION_GRAPH_SETTINGS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "settings": settings_to_dict(settings),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_project_interpretation_graph_settings(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> InterpretationGraphSettings | None:
    path = _settings_path(root, project_id)
    if not path.exists():
        return None

    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return settings_from_dict(payload.get("settings"))


def project_interpretation_graph_settings_exists(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> bool:
    return _settings_path(root, project_id).exists()
