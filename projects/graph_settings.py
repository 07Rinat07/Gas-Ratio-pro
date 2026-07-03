from __future__ import annotations

import json
from dataclasses import dataclass
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


def settings_to_dict(settings: InterpretationGraphSettings) -> dict[str, Any]:
    return {
        "selected_tracks": list(settings.selected_tracks),
        "height": int(settings.height),
        "depth_range": _range_to_list(settings.depth_range),
        "gas_x_range": _range_to_list(settings.gas_x_range),
        "ratio_x_range": _range_to_list(settings.ratio_x_range),
        "pixler_x_range": _range_to_list(settings.pixler_x_range),
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
