from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECTS_ROOT, ProjectRecord, list_projects, safe_project_id

RECENT_PROJECTS_FILE_NAME = "recent_projects.json"
RECENT_PROJECTS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RecentProjectEntry:
    project_id: str
    project_name: str
    last_opened_at: str
    pinned: bool = False
    favorite: bool = False
    exists_on_disk: bool = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _history_path(root: Path | str = DEFAULT_PROJECTS_ROOT) -> Path:
    return Path(root) / RECENT_PROJECTS_FILE_NAME


def _entry_from_dict(raw: dict[str, Any], projects_by_id: dict[str, ProjectRecord]) -> RecentProjectEntry | None:
    project_id = str(raw.get("project_id", "")).strip()
    if not project_id:
        return None
    try:
        project_id = safe_project_id(project_id)
    except ValueError:
        return None
    project = projects_by_id.get(project_id)
    return RecentProjectEntry(
        project_id=project_id,
        project_name=project.name if project else str(raw.get("project_name", "")) or project_id,
        last_opened_at=str(raw.get("last_opened_at", "")),
        pinned=bool(raw.get("pinned", False)),
        favorite=bool(raw.get("favorite", False)),
        exists_on_disk=project is not None,
    )


def _entry_to_dict(entry: RecentProjectEntry) -> dict[str, Any]:
    return {
        "project_id": entry.project_id,
        "project_name": entry.project_name,
        "last_opened_at": entry.last_opened_at,
        "pinned": entry.pinned,
        "favorite": entry.favorite,
    }


def _read_raw_entries(root: Path | str) -> tuple[dict[str, Any], ...]:
    path = _history_path(root)
    if not path.exists():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return ()
    items = payload.get("recent_projects", ()) if isinstance(payload, dict) else ()
    return tuple(item for item in items if isinstance(item, dict))


def _write_entries(root: Path | str, entries: tuple[RecentProjectEntry, ...]) -> Path:
    path = _history_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": RECENT_PROJECTS_SCHEMA_VERSION,
        "updated_at": _utc_now(),
        "recent_projects": [_entry_to_dict(entry) for entry in entries],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_recent_projects(root: Path | str = DEFAULT_PROJECTS_ROOT, *, include_missing: bool = True) -> tuple[RecentProjectEntry, ...]:
    projects_by_id = {project.id: project for project in list_projects(root)}
    entries: list[RecentProjectEntry] = []
    seen: set[str] = set()
    for raw in _read_raw_entries(root):
        entry = _entry_from_dict(raw, projects_by_id)
        if entry is None or entry.project_id in seen:
            continue
        if include_missing or entry.exists_on_disk:
            entries.append(entry)
            seen.add(entry.project_id)

    # If the history file does not exist yet, use existing projects as a first useful history.
    # Once the file exists, an empty list is an intentional cleared history.
    if not entries and not _history_path(root).exists():
        entries = [
            RecentProjectEntry(project.id, project.name, project.updated_at or project.created_at, exists_on_disk=True)
            for project in list_projects(root)
        ]

    entries.sort(key=lambda item: (not item.pinned, not item.favorite, item.last_opened_at), reverse=False)
    entries.sort(key=lambda item: (item.pinned, item.favorite, item.last_opened_at), reverse=True)
    return tuple(entries)


def touch_recent_project(root: Path | str, project: ProjectRecord) -> RecentProjectEntry:
    entries = list(list_recent_projects(root, include_missing=True))
    existing = next((entry for entry in entries if entry.project_id == project.id), None)
    updated = RecentProjectEntry(
        project_id=project.id,
        project_name=project.name,
        last_opened_at=_utc_now(),
        pinned=existing.pinned if existing else False,
        favorite=existing.favorite if existing else False,
        exists_on_disk=True,
    )
    new_entries = (updated, *tuple(entry for entry in entries if entry.project_id != project.id))
    _write_entries(root, new_entries[:100])
    return updated


def remove_recent_project(root: Path | str, project_id: str) -> bool:
    clean_id = safe_project_id(project_id)
    entries = list_recent_projects(root, include_missing=True)
    filtered = tuple(entry for entry in entries if entry.project_id != clean_id)
    _write_entries(root, filtered)
    return len(filtered) != len(entries)


def clear_recent_projects(root: Path | str = DEFAULT_PROJECTS_ROOT) -> int:
    entries = list_recent_projects(root, include_missing=True)
    _write_entries(root, ())
    return len(entries)


def set_recent_project_flags(
    root: Path | str,
    project_id: str,
    *,
    pinned: bool | None = None,
    favorite: bool | None = None,
) -> RecentProjectEntry:
    clean_id = safe_project_id(project_id)
    entries = list(list_recent_projects(root, include_missing=True))
    for index, entry in enumerate(entries):
        if entry.project_id == clean_id:
            updated = RecentProjectEntry(
                project_id=entry.project_id,
                project_name=entry.project_name,
                last_opened_at=entry.last_opened_at,
                pinned=entry.pinned if pinned is None else bool(pinned),
                favorite=entry.favorite if favorite is None else bool(favorite),
                exists_on_disk=entry.exists_on_disk,
            )
            entries[index] = updated
            _write_entries(root, tuple(entries))
            return updated
    raise FileNotFoundError(f"Recent project not found: {project_id}")


def recent_projects_table_rows(entries: tuple[RecentProjectEntry, ...]) -> list[dict[str, str]]:
    return [
        {
            "Проект": entry.project_name,
            "ID": entry.project_id,
            "Последнее открытие": entry.last_opened_at,
            "Закреплен": "да" if entry.pinned else "нет",
            "Избранное": "да" if entry.favorite else "нет",
            "На диске": "да" if entry.exists_on_disk else "нет",
        }
        for entry in entries
    ]
