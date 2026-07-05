from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.las_files import ProjectLasWellCard, list_project_las_wells
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

PROJECT_WELL_GROUPS_FILE_NAME = "well_groups.json"
PROJECT_WELL_GROUPS_SCHEMA_VERSION = 1
UNGROUPED_WELLS_GROUP_ID = "ungrouped"
UNGROUPED_WELLS_GROUP_NAME = "Без группы"


@dataclass(frozen=True)
class ProjectWellGroup:
    """Saved logical group of wells inside a local project."""

    id: str
    name: str
    well_ids: tuple[str, ...] = ()
    description: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def count(self) -> int:
        return len(self.well_ids)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", value.strip()).strip("-").lower()
    return slug or "group"


def _safe_group_id(value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", value):
        raise ValueError("Некорректный идентификатор группы скважин.")
    return value


def _groups_path(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_WELL_GROUPS_FILE_NAME


def _group_from_dict(raw: dict[str, Any]) -> ProjectWellGroup:
    raw_well_ids = raw.get("well_ids", ())
    well_ids = tuple(str(well_id) for well_id in raw_well_ids if str(well_id).strip())
    return ProjectWellGroup(
        id=_safe_group_id(str(raw.get("id", "") or _slugify(str(raw.get("name", ""))))),
        name=str(raw.get("name", "") or "Группа скважин"),
        well_ids=well_ids,
        description=str(raw.get("description", "")),
        created_at=str(raw.get("created_at", "")),
        updated_at=str(raw.get("updated_at", "")),
    )


def _group_to_dict(group: ProjectWellGroup) -> dict[str, Any]:
    return {
        "id": _safe_group_id(group.id),
        "name": group.name.strip() or "Группа скважин",
        "well_ids": list(dict.fromkeys(well_id for well_id in group.well_ids if well_id)),
        "description": group.description,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


def _read_groups(root: Path | str, project_id: str) -> tuple[ProjectWellGroup, ...]:
    path = _groups_path(root, project_id)
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("groups", ()) if isinstance(payload, dict) else ()
    groups = tuple(_group_from_dict(record) for record in records if isinstance(record, dict))
    return tuple(sorted(groups, key=lambda group: group.name.lower()))


def _write_groups(root: Path | str, project_id: str, groups: tuple[ProjectWellGroup, ...]) -> Path:
    path = _groups_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_WELL_GROUPS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "groups": [_group_to_dict(group) for group in groups],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_project_well_groups(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectWellGroup, ...]:
    """Return saved well groups without reading raw LAS payloads."""

    try:
        return _read_groups(root, project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()


def save_project_well_group(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    name: str = "",
    well_ids: tuple[str, ...] | list[str] = (),
    description: str = "",
    group_id: str | None = None,
) -> ProjectWellGroup:
    """Create or replace a project well group by id/name."""

    clean_name = name.strip() or "Группа скважин"
    clean_group_id = _safe_group_id(group_id) if group_id else _slugify(clean_name)
    unique_well_ids = tuple(dict.fromkeys(str(well_id) for well_id in well_ids if str(well_id).strip()))
    now = _utc_now()
    existing = {group.id: group for group in _read_groups(root, project_id)}
    previous = existing.get(clean_group_id)
    group = ProjectWellGroup(
        id=clean_group_id,
        name=clean_name,
        well_ids=unique_well_ids,
        description=description.strip(),
        created_at=previous.created_at if previous else now,
        updated_at=now,
    )
    existing[clean_group_id] = group
    _write_groups(root, project_id, tuple(existing.values()))
    return group


def assign_project_wells_to_group(
    root: Path | str,
    project_id: str,
    group_id: str,
    well_ids: tuple[str, ...] | list[str],
) -> ProjectWellGroup:
    """Assign selected wells to one group and remove them from other groups."""

    clean_group_id = _safe_group_id(group_id)
    selected = set(str(well_id) for well_id in well_ids if str(well_id).strip())
    groups = list(_read_groups(root, project_id))
    target: ProjectWellGroup | None = None
    updated: list[ProjectWellGroup] = []
    now = _utc_now()

    for group in groups:
        remaining = tuple(well_id for well_id in group.well_ids if well_id not in selected)
        if group.id == clean_group_id:
            target = group
            merged = tuple(dict.fromkeys((*remaining, *selected)))
            updated.append(
                ProjectWellGroup(
                    id=group.id,
                    name=group.name,
                    well_ids=merged,
                    description=group.description,
                    created_at=group.created_at,
                    updated_at=now,
                )
            )
        else:
            updated.append(
                ProjectWellGroup(
                    id=group.id,
                    name=group.name,
                    well_ids=remaining,
                    description=group.description,
                    created_at=group.created_at,
                    updated_at=now if remaining != group.well_ids else group.updated_at,
                )
            )

    if target is None:
        raise ValueError("Группа скважин не найдена.")

    _write_groups(root, project_id, tuple(updated))
    return next(group for group in updated if group.id == clean_group_id)


def group_project_wells(
    wells: tuple[ProjectLasWellCard, ...],
    groups: tuple[ProjectWellGroup, ...],
) -> tuple[tuple[ProjectWellGroup, tuple[ProjectLasWellCard, ...]], ...]:
    """Group well cards by saved assignments and append an ungrouped bucket."""

    if not wells:
        return ()

    wells_by_id = {well.id: well for well in wells}
    assigned: set[str] = set()
    grouped: list[tuple[ProjectWellGroup, tuple[ProjectLasWellCard, ...]]] = []

    for group in groups:
        group_wells = tuple(wells_by_id[well_id] for well_id in group.well_ids if well_id in wells_by_id)
        assigned.update(well.id for well in group_wells)
        grouped.append((group, group_wells))

    ungrouped = tuple(well for well in wells if well.id not in assigned)
    if ungrouped or not grouped:
        grouped.append(
            (
                ProjectWellGroup(
                    id=UNGROUPED_WELLS_GROUP_ID,
                    name=UNGROUPED_WELLS_GROUP_NAME,
                    well_ids=tuple(well.id for well in ungrouped),
                ),
                ungrouped,
            )
        )
    return tuple(grouped)


def list_grouped_project_wells(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[tuple[ProjectWellGroup, tuple[ProjectLasWellCard, ...]], ...]:
    wells = list_project_las_wells(root, project_id, include_archived=include_archived)
    groups = list_project_well_groups(root, project_id)
    return group_project_wells(wells, groups)
