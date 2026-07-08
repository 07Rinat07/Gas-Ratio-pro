from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECTS_ROOT, load_project, safe_project_id

WORKSPACE_FILE_NAME = "workspace.json"
DEFAULT_WORKSPACE_KIND = "general"


@dataclass(frozen=True)
class WorkspaceRecord:
    """Persistent workspace metadata stored inside a project directory."""

    id: str
    project_id: str
    name: str
    kind: str = DEFAULT_WORKSPACE_KIND
    description: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", value.strip()).strip("-").lower()
    return slug or "workspace"


def safe_workspace_id(workspace_id: str) -> str:
    """Validate a workspace identifier before it is used in a filesystem path."""

    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", workspace_id):
        raise ValueError("Некорректный идентификатор рабочего пространства.")
    return workspace_id


def _project_dir(root: Path, project_id: str) -> Path:
    return root / safe_project_id(project_id)


def _workspace_root(root: Path, project_id: str) -> Path:
    return _project_dir(root, project_id) / "workspaces"


def _workspace_dir(root: Path, project_id: str, workspace_id: str) -> Path:
    return _workspace_root(root, project_id) / safe_workspace_id(workspace_id)


def _workspace_path(root: Path, project_id: str, workspace_id: str) -> Path:
    return _workspace_dir(root, project_id, workspace_id) / WORKSPACE_FILE_NAME


def _record_to_dict(record: WorkspaceRecord) -> dict[str, Any]:
    payload = asdict(record)
    payload["settings"] = dict(record.settings or {})
    return payload


def _record_from_dict(payload: dict[str, Any]) -> WorkspaceRecord:
    return WorkspaceRecord(
        id=safe_workspace_id(str(payload.get("id") or "workspace")),
        project_id=safe_project_id(str(payload.get("project_id") or "")),
        name=str(payload.get("name") or "Workspace"),
        kind=str(payload.get("kind") or DEFAULT_WORKSPACE_KIND),
        description=str(payload.get("description") or ""),
        settings=dict(payload.get("settings") or {}),
        created_at=str(payload.get("created_at") or ""),
        updated_at=str(payload.get("updated_at") or ""),
    )


def _write_record(root: Path, record: WorkspaceRecord) -> WorkspaceRecord:
    workspace_dir = _workspace_dir(root, record.project_id, record.id)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    _workspace_path(root, record.project_id, record.id).write_text(
        json.dumps(_record_to_dict(record), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record


def list_workspaces(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = "") -> tuple[WorkspaceRecord, ...]:
    """Return persisted workspaces for one project ordered by last update time."""

    root_path = Path(root)
    clean_project_id = safe_project_id(project_id)
    workspace_root = _workspace_root(root_path, clean_project_id)
    if not workspace_root.exists():
        return ()

    records: list[WorkspaceRecord] = []
    for path in sorted(workspace_root.glob(f"*/{WORKSPACE_FILE_NAME}")):
        try:
            records.append(_record_from_dict(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return tuple(sorted(records, key=lambda item: item.updated_at, reverse=True))


def load_workspace(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = "", workspace_id: str = "") -> WorkspaceRecord:
    """Load one workspace record from project-scoped storage."""

    root_path = Path(root)
    path = _workspace_path(root_path, project_id, workspace_id)
    if not path.exists():
        raise FileNotFoundError(f"Workspace not found: {workspace_id}")
    return _record_from_dict(json.loads(path.read_text(encoding="utf-8")))


def create_workspace(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = "",
    name: str = "",
    kind: str = DEFAULT_WORKSPACE_KIND,
    description: str = "",
    settings: dict[str, Any] | None = None,
    workspace_id: str | None = None,
) -> WorkspaceRecord:
    """Create a workspace under an existing project directory."""

    root_path = Path(root)
    clean_project_id = safe_project_id(project_id)
    # Require an existing project so orphan workspace directories are not created.
    load_project(root_path, clean_project_id)

    now = _utc_now()
    clean_name = name.strip() or "Workspace"
    base_id = safe_workspace_id(workspace_id) if workspace_id else f"{now[:10].replace('-', '')}-{_slugify(clean_name)}"
    candidate_id = base_id
    counter = 2
    while _workspace_dir(root_path, clean_project_id, candidate_id).exists():
        candidate_id = f"{base_id}-{counter}"
        counter += 1

    return _write_record(
        root_path,
        WorkspaceRecord(
            id=candidate_id,
            project_id=clean_project_id,
            name=clean_name,
            kind=kind.strip() or DEFAULT_WORKSPACE_KIND,
            description=description.strip(),
            settings=dict(settings or {}),
            created_at=now,
            updated_at=now,
        ),
    )


def update_workspace(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = "",
    workspace_id: str = "",
    *,
    name: str | None = None,
    kind: str | None = None,
    description: str | None = None,
    settings: dict[str, Any] | None = None,
) -> WorkspaceRecord:
    """Update workspace metadata while preserving immutable identifiers."""

    current = load_workspace(root, project_id, workspace_id)
    updated_settings = dict(current.settings)
    if settings is not None:
        updated_settings.update(settings)
    return _write_record(
        Path(root),
        WorkspaceRecord(
            id=current.id,
            project_id=current.project_id,
            name=(name.strip() if name is not None and name.strip() else current.name),
            kind=(kind.strip() if kind is not None and kind.strip() else current.kind),
            description=(description.strip() if description is not None else current.description),
            settings=updated_settings,
            created_at=current.created_at,
            updated_at=_utc_now(),
        ),
    )


def delete_workspace(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = "", workspace_id: str = "") -> bool:
    """Delete a workspace metadata folder from project-scoped storage."""

    import shutil

    workspace_dir = _workspace_dir(Path(root), project_id, workspace_id)
    if not workspace_dir.exists():
        return False
    shutil.rmtree(workspace_dir)
    return True
