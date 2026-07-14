from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.interpretation_intervals import DEFAULT_INTERPRETATION_ID, _safe_interpretation_id
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

INTERPRETATION_INTERVAL_DISPLAY_SCHEMA = "gas-ratio-pro/interpretation-interval-display/v1"
INTERPRETATION_INTERVAL_DISPLAY_FILE_NAME = "display_settings.json"
MIN_OVERLAY_OPACITY = 0.04
MAX_OVERLAY_OPACITY = 0.55
DEFAULT_OVERLAY_OPACITY = 0.18


@dataclass(frozen=True)
class InterpretationIntervalDisplaySettings:
    visible: bool = True
    opacity: float = DEFAULT_OVERLAY_OPACITY


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_interval_display_settings(
    *,
    visible: object = True,
    opacity: object = DEFAULT_OVERLAY_OPACITY,
) -> InterpretationIntervalDisplaySettings:
    try:
        normalized_opacity = float(opacity)
    except (TypeError, ValueError):
        normalized_opacity = DEFAULT_OVERLAY_OPACITY
    return InterpretationIntervalDisplaySettings(
        visible=bool(visible),
        opacity=max(MIN_OVERLAY_OPACITY, min(MAX_OVERLAY_OPACITY, normalized_opacity)),
    )


def interval_display_settings_path(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str = "",
    interpretation_id: str = DEFAULT_INTERPRETATION_ID,
) -> Path:
    return (
        Path(root)
        / safe_project_id(project_id)
        / "wells"
        / safe_well_id(well_id)
        / "interpretations"
        / _safe_interpretation_id(interpretation_id)
        / INTERPRETATION_INTERVAL_DISPLAY_FILE_NAME
    )


def load_interpretation_interval_display_settings(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str = "",
    interpretation_id: str = DEFAULT_INTERPRETATION_ID,
) -> InterpretationIntervalDisplaySettings:
    path = interval_display_settings_path(root, project_id, well_id, interpretation_id)
    if not path.exists():
        return InterpretationIntervalDisplaySettings()
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Не удалось прочитать настройки отображения интервалов: {path}") from exc
    if payload.get("schema") != INTERPRETATION_INTERVAL_DISPLAY_SCHEMA:
        raise ValueError("Неподдерживаемая схема настроек отображения интервалов.")
    settings = payload.get("settings", {})
    if not isinstance(settings, dict):
        settings = {}
    return normalize_interval_display_settings(
        visible=settings.get("visible", True),
        opacity=settings.get("opacity", DEFAULT_OVERLAY_OPACITY),
    )


def save_interpretation_interval_display_settings(
    settings: InterpretationIntervalDisplaySettings,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str = "",
    interpretation_id: str = DEFAULT_INTERPRETATION_ID,
) -> Path:
    normalized = normalize_interval_display_settings(
        visible=settings.visible,
        opacity=settings.opacity,
    )
    path = interval_display_settings_path(root, project_id, well_id, interpretation_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": INTERPRETATION_INTERVAL_DISPLAY_SCHEMA,
        "project_id": safe_project_id(project_id),
        "well_id": safe_well_id(well_id),
        "interpretation_id": _safe_interpretation_id(interpretation_id),
        "updated_at": _utc_now(),
        "settings": {
            "visible": normalized.visible,
            "opacity": normalized.opacity,
        },
    }
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path
