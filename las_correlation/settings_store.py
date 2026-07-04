from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from las_correlation.settings import LasCorrelationSettings, settings_from_dict, settings_to_dict
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id


CORRELATION_SETTINGS_FILE_NAME = "correlation_settings.json"
SETTINGS_SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _settings_path(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / CORRELATION_SETTINGS_FILE_NAME


def save_project_correlation_settings(
    settings: LasCorrelationSettings,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> Path:
    path = _settings_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "project_id": project_id,
        "updated_at": _utc_now(),
        "settings": settings_to_dict(settings),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_project_correlation_settings(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> LasCorrelationSettings | None:
    path = _settings_path(root, project_id)
    if not path.exists():
        return None

    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return settings_from_dict(payload.get("settings"))


def project_correlation_settings_exists(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> bool:
    return _settings_path(root, project_id).exists()
