from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

PROJECT_FOLDERS_FILE_NAME = "project_folders.json"
PROJECT_FOLDERS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProjectFolder:
    """Saved metadata-only Project Explorer folder.

    A folder stores references to existing project tree items by stable node id,
    for example ``well:<id>``, ``calculation:<id>`` or ``export:<id>``. It does
    not copy LAS bytes or calculation tables, so it stays safe for large local
    projects and can later be reused by drag-and-drop.
    """

    id: str
    name: str
    item_ids: tuple[str, ...] = ()
    description: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def count(self) -> int:
        return len(self.item_ids)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", value.strip()).strip("-").lower()
    return slug or "folder"


def _safe_folder_id(value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", value):
        raise ValueError("Некорректный идентификатор папки проекта.")
    return value


def _clean_item_id(value: str) -> str:
    item_id = str(value).strip()
    if not item_id or ":" not in item_id:
        raise ValueError("Некорректная ссылка на объект Project Explorer.")
    return item_id


def _folders_path(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_FOLDERS_FILE_NAME


def _folder_from_dict(raw: dict[str, Any]) -> ProjectFolder:
    raw_item_ids = raw.get("item_ids", ())
    item_ids: list[str] = []
    if isinstance(raw_item_ids, list | tuple):
        for item_id in raw_item_ids:
            try:
                item_ids.append(_clean_item_id(str(item_id)))
            except ValueError:
                continue
    return ProjectFolder(
        id=_safe_folder_id(str(raw.get("id", "") or _slugify(str(raw.get("name", ""))))),
        name=str(raw.get("name", "") or "Папка проекта"),
        item_ids=tuple(dict.fromkeys(item_ids)),
        description=str(raw.get("description", "")),
        created_at=str(raw.get("created_at", "")),
        updated_at=str(raw.get("updated_at", "")),
    )


def _folder_to_dict(folder: ProjectFolder) -> dict[str, Any]:
    return {
        "id": _safe_folder_id(folder.id),
        "name": folder.name.strip() or "Папка проекта",
        "item_ids": list(dict.fromkeys(_clean_item_id(item_id) for item_id in folder.item_ids)),
        "description": folder.description,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
    }


def _read_folders(root: Path | str, project_id: str) -> tuple[ProjectFolder, ...]:
    path = _folders_path(root, project_id)
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("folders", ()) if isinstance(payload, dict) else ()
    folders = tuple(_folder_from_dict(record) for record in records if isinstance(record, dict))
    return tuple(sorted(folders, key=lambda folder: folder.name.lower()))


def _write_folders(root: Path | str, project_id: str, folders: tuple[ProjectFolder, ...]) -> Path:
    path = _folders_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_FOLDERS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "folders": [_folder_to_dict(folder) for folder in folders],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_project_folders(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectFolder, ...]:
    """Return saved Project Explorer folders without reading project payloads."""

    try:
        return _read_folders(root, project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()


def save_project_folder(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    name: str = "",
    item_ids: tuple[str, ...] | list[str] = (),
    description: str = "",
    folder_id: str | None = None,
) -> ProjectFolder:
    """Create or replace a metadata-only Project Explorer folder."""

    clean_name = name.strip() or "Папка проекта"
    clean_folder_id = _safe_folder_id(folder_id) if folder_id else _slugify(clean_name)
    unique_item_ids = tuple(dict.fromkeys(_clean_item_id(item_id) for item_id in item_ids))
    now = _utc_now()
    existing = {folder.id: folder for folder in _read_folders(root, project_id)}
    previous = existing.get(clean_folder_id)
    folder = ProjectFolder(
        id=clean_folder_id,
        name=clean_name,
        item_ids=unique_item_ids,
        description=description.strip(),
        created_at=previous.created_at if previous else now,
        updated_at=now,
    )
    existing[clean_folder_id] = folder
    _write_folders(root, project_id, tuple(existing.values()))
    return folder


def assign_project_items_to_folder(
    root: Path | str,
    project_id: str,
    folder_id: str,
    item_ids: tuple[str, ...] | list[str],
) -> ProjectFolder:
    """Replace the item list of one saved Project Explorer folder."""

    clean_folder_id = _safe_folder_id(folder_id)
    folders = list(_read_folders(root, project_id))
    now = _utc_now()
    cleaned_item_ids = tuple(dict.fromkeys(_clean_item_id(item_id) for item_id in item_ids))
    updated: list[ProjectFolder] = []
    target_found = False

    for folder in folders:
        if folder.id == clean_folder_id:
            target_found = True
            updated.append(
                ProjectFolder(
                    id=folder.id,
                    name=folder.name,
                    item_ids=cleaned_item_ids,
                    description=folder.description,
                    created_at=folder.created_at,
                    updated_at=now,
                )
            )
        else:
            updated.append(folder)

    if not target_found:
        raise ValueError("Папка проекта не найдена.")

    _write_folders(root, project_id, tuple(updated))
    return next(folder for folder in updated if folder.id == clean_folder_id)
