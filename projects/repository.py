from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PROJECTS_ROOT = Path("data/projects")
DEFAULT_PROJECT_ID = "default"
PROJECT_FILE_NAME = "project.json"


@dataclass(frozen=True)
class ProjectRecord:
    id: str
    name: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", value.strip()).strip("-").lower()
    return slug or "project"


def safe_project_id(project_id: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", project_id):
        raise ValueError("Некорректный идентификатор проекта.")
    return project_id


def _project_dir(root: Path, project_id: str) -> Path:
    return root / safe_project_id(project_id)


def _project_path(root: Path, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_FILE_NAME


def _project_from_dict(raw: dict[str, Any]) -> ProjectRecord:
    return ProjectRecord(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")) or "Без названия",
        description=str(raw.get("description", "")),
        created_at=str(raw.get("created_at", "")),
        updated_at=str(raw.get("updated_at", "")),
    )


def _project_to_dict(project: ProjectRecord) -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def _write_project(root: Path, project: ProjectRecord) -> ProjectRecord:
    project_dir = _project_dir(root, project.id)
    project_dir.mkdir(parents=True, exist_ok=True)
    _project_path(root, project.id).write_text(
        json.dumps(_project_to_dict(project), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return project


def load_project(root: Path | str, project_id: str) -> ProjectRecord:
    root_path = Path(root)
    path = _project_path(root_path, project_id)
    if not path.exists():
        raise FileNotFoundError(f"Project not found: {project_id}")
    return _project_from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_projects(root: Path | str = DEFAULT_PROJECTS_ROOT) -> tuple[ProjectRecord, ...]:
    root_path = Path(root)
    if not root_path.exists():
        return ()

    projects: list[ProjectRecord] = []
    for project_path in sorted(root_path.glob(f"*/{PROJECT_FILE_NAME}")):
        try:
            projects.append(_project_from_dict(json.loads(project_path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return tuple(sorted(projects, key=lambda project: project.updated_at, reverse=True))


def ensure_default_project(root: Path | str = DEFAULT_PROJECTS_ROOT) -> ProjectRecord:
    root_path = Path(root)
    try:
        return load_project(root_path, DEFAULT_PROJECT_ID)
    except FileNotFoundError:
        now = _utc_now()
        return _write_project(
            root_path,
            ProjectRecord(
                id=DEFAULT_PROJECT_ID,
                name="Основной проект",
                description="Рабочий локальный проект по умолчанию.",
                created_at=now,
                updated_at=now,
            ),
        )


def create_project(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    name: str = "",
    description: str = "",
    project_id: str | None = None,
) -> ProjectRecord:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    now = _utc_now()
    clean_name = name.strip() or "Без названия"
    base_id = safe_project_id(project_id) if project_id else f"{now[:10].replace('-', '')}-{_slugify(clean_name)}"
    candidate_id = base_id
    counter = 2
    while _project_dir(root_path, candidate_id).exists():
        candidate_id = f"{base_id}-{counter}"
        counter += 1

    return _write_project(
        root_path,
        ProjectRecord(
            id=candidate_id,
            name=clean_name,
            description=description.strip(),
            created_at=now,
            updated_at=now,
        ),
    )


def delete_project(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = "") -> bool:
    """Delete a project directory from persistent storage.

    The default project is intentionally protected because the application
    recreates it as a fallback workspace.
    """
    import shutil

    clean_project_id = safe_project_id(project_id)
    if clean_project_id == DEFAULT_PROJECT_ID:
        raise ValueError("Основной проект нельзя удалить.")
    project_dir = _project_dir(Path(root), clean_project_id)
    if not project_dir.exists():
        return False
    shutil.rmtree(project_dir)
    return True
