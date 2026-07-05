from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

PROJECT_LABELS_FILE_NAME = "project_labels.json"
PROJECT_LABELS_SCHEMA_VERSION = 1

PROJECT_EXPLORER_LABEL_COLORS: dict[str, str] = {
    "red": "Красная",
    "orange": "Оранжевая",
    "yellow": "Желтая",
    "green": "Зеленая",
    "blue": "Синяя",
    "purple": "Фиолетовая",
    "gray": "Серая",
}
PROJECT_EXPLORER_LABEL_ICONS: dict[str, str] = {
    "red": "🔴",
    "orange": "🟠",
    "yellow": "🟡",
    "green": "🟢",
    "blue": "🔵",
    "purple": "🟣",
    "gray": "⚪",
}


@dataclass(frozen=True)
class ProjectExplorerLabel:
    """Color label assigned to a stable Project Explorer object id.

    The label is metadata-only. It references a tree node such as ``well:<id>``,
    ``las:<id>``, ``calculation:<id>`` or ``export:<id>`` and never copies raw
    LAS bytes, exported files or calculation tables.
    """

    object_id: str
    color: str
    note: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def color_name(self) -> str:
        return PROJECT_EXPLORER_LABEL_COLORS.get(self.color, self.color)

    @property
    def icon(self) -> str:
        return PROJECT_EXPLORER_LABEL_ICONS.get(self.color, "🏷️")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _labels_path(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_LABELS_FILE_NAME


def _clean_object_id(value: str) -> str:
    object_id = str(value).strip()
    if not object_id or ":" not in object_id:
        raise ValueError("Некорректная ссылка на объект Project Explorer.")
    return object_id


def _clean_color(value: str) -> str:
    color = str(value).strip().lower()
    if color not in PROJECT_EXPLORER_LABEL_COLORS:
        raise ValueError("Некорректный цвет метки Project Explorer.")
    return color


def _label_from_dict(raw: dict[str, Any]) -> ProjectExplorerLabel:
    return ProjectExplorerLabel(
        object_id=_clean_object_id(str(raw.get("object_id", ""))),
        color=_clean_color(str(raw.get("color", ""))),
        note=str(raw.get("note", "")),
        created_at=str(raw.get("created_at", "")),
        updated_at=str(raw.get("updated_at", "")),
    )


def _label_to_dict(label: ProjectExplorerLabel) -> dict[str, Any]:
    return {
        "object_id": _clean_object_id(label.object_id),
        "color": _clean_color(label.color),
        "note": label.note.strip(),
        "created_at": label.created_at,
        "updated_at": label.updated_at,
    }


def _read_labels(root: Path | str, project_id: str) -> tuple[ProjectExplorerLabel, ...]:
    path = _labels_path(root, project_id)
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("labels", ()) if isinstance(payload, dict) else ()
    labels: list[ProjectExplorerLabel] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            labels.append(_label_from_dict(record))
        except ValueError:
            continue
    return tuple(sorted(labels, key=lambda label: label.object_id))


def _write_labels(root: Path | str, project_id: str, labels: tuple[ProjectExplorerLabel, ...]) -> Path:
    path = _labels_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_LABELS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "labels": [_label_to_dict(label) for label in labels],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_project_explorer_labels(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectExplorerLabel, ...]:
    """Return saved Project Explorer color labels, ignoring corrupted records."""

    try:
        return _read_labels(root, project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()


def project_explorer_labels_by_object(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> dict[str, ProjectExplorerLabel]:
    """Return color labels indexed by stable Project Explorer object id."""

    return {label.object_id: label for label in list_project_explorer_labels(root, project_id)}


def set_project_explorer_label(
    root: Path | str,
    project_id: str,
    object_id: str,
    color: str,
    note: str = "",
) -> ProjectExplorerLabel:
    """Create or replace one color label for a Project Explorer object."""

    clean_object_id = _clean_object_id(object_id)
    clean_color = _clean_color(color)
    now = _utc_now()
    existing = {label.object_id: label for label in _read_labels(root, project_id)}
    previous = existing.get(clean_object_id)
    label = ProjectExplorerLabel(
        object_id=clean_object_id,
        color=clean_color,
        note=note.strip(),
        created_at=previous.created_at if previous else now,
        updated_at=now,
    )
    existing[clean_object_id] = label
    _write_labels(root, project_id, tuple(existing.values()))
    return label


def clear_project_explorer_label(
    root: Path | str,
    project_id: str,
    object_id: str,
) -> bool:
    """Remove a color label from one Project Explorer object."""

    clean_object_id = _clean_object_id(object_id)
    current = _read_labels(root, project_id)
    labels = tuple(label for label in current if label.object_id != clean_object_id)
    removed = len(labels) != len(current)
    _write_labels(root, project_id, labels)
    return removed
