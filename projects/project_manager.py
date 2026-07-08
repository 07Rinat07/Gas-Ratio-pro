from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.repository import PROJECT_FILE_NAME, ProjectRecord, create_project, load_project, safe_project_id

PROJECT_HISTORY_FILE_NAME = "project_history.json"
PROJECT_RECOVERY_FILE_NAME = "project_recovery.json"
PROJECT_TEMPLATES_DIR_NAME = "templates"
PROJECT_BACKUPS_DIR_NAME = "backups"
PROJECT_ARCHIVES_DIR_NAME = "archives"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class ProjectHistoryEntry:
    id: str
    action: str
    description: str
    created_at: str
    author: str = "local-user"
    object_type: str = "project"
    object_id: str = ""


@dataclass(frozen=True)
class ProjectRecoveryState:
    project_id: str
    saved_at: str
    active_step: str
    message: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ProjectTemplate:
    id: str
    name: str
    description: str
    created_at: str
    source_project_id: str
    include_structure: bool = True


@dataclass(frozen=True)
class ProjectBackupRecord:
    id: str
    project_id: str
    file_name: str
    created_at: str
    size_bytes: int
    description: str = ""


@dataclass(frozen=True)
class ProjectRestoreResult:
    """Result of a project restore operation from a managed backup archive."""

    project_id: str
    backup_id: str
    restored_path: str
    overwritten_existing: bool
    files_restored: int


def _history_from_dict(raw: dict[str, Any]) -> ProjectHistoryEntry:
    return ProjectHistoryEntry(
        id=str(raw.get("id", "")),
        action=str(raw.get("action", "")),
        description=str(raw.get("description", "")),
        created_at=str(raw.get("created_at", "")),
        author=str(raw.get("author", "local-user")),
        object_type=str(raw.get("object_type", "project")),
        object_id=str(raw.get("object_id", "")),
    )


def _history_to_dict(entry: ProjectHistoryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "action": entry.action,
        "description": entry.description,
        "created_at": entry.created_at,
        "author": entry.author,
        "object_type": entry.object_type,
        "object_id": entry.object_id,
    }


def append_project_history(
    root: Path | str,
    project_id: str,
    action: str,
    description: str,
    *,
    author: str = "local-user",
    object_type: str = "project",
    object_id: str = "",
) -> ProjectHistoryEntry:
    """Append one metadata-only project history event."""
    safe_id = safe_project_id(project_id)
    now = _utc_now()
    entry = ProjectHistoryEntry(
        id=f"{now.replace(':', '').replace('-', '')}-{len(list_project_history(root, safe_id)) + 1:04d}",
        action=action.strip() or "update",
        description=description.strip() or "Project metadata updated",
        created_at=now,
        author=author.strip() or "local-user",
        object_type=object_type.strip() or "project",
        object_id=object_id.strip(),
    )
    path = _project_dir(root, safe_id) / PROJECT_HISTORY_FILE_NAME
    existing = [_history_to_dict(item) for item in list_project_history(root, safe_id)]
    existing.insert(0, _history_to_dict(entry))
    _json_write(path, existing[:500])
    return entry


def list_project_history(root: Path | str, project_id: str) -> tuple[ProjectHistoryEntry, ...]:
    path = _project_dir(root, project_id) / PROJECT_HISTORY_FILE_NAME
    raw = _json_read(path, [])
    if not isinstance(raw, list):
        return ()
    entries = []
    for item in raw:
        if isinstance(item, dict):
            entry = _history_from_dict(item)
            if entry.id and entry.action:
                entries.append(entry)
    return tuple(entries)


def save_project_recovery_state(
    root: Path | str,
    project_id: str,
    active_step: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> ProjectRecoveryState:
    """Save a lightweight recovery checkpoint without copying raw datasets."""
    safe_id = safe_project_id(project_id)
    state = ProjectRecoveryState(
        project_id=safe_id,
        saved_at=_utc_now(),
        active_step=active_step.strip() or "workspace",
        message=message.strip() or "Autosave checkpoint",
        payload=dict(payload or {}),
    )
    _json_write(
        _project_dir(root, safe_id) / PROJECT_RECOVERY_FILE_NAME,
        {
            "project_id": state.project_id,
            "saved_at": state.saved_at,
            "active_step": state.active_step,
            "message": state.message,
            "payload": state.payload,
        },
    )
    append_project_history(root, safe_id, "autosave", state.message, object_type="recovery", object_id=state.active_step)
    return state


def load_project_recovery_state(root: Path | str, project_id: str) -> ProjectRecoveryState | None:
    raw = _json_read(_project_dir(root, project_id) / PROJECT_RECOVERY_FILE_NAME, None)
    if not isinstance(raw, dict):
        return None
    return ProjectRecoveryState(
        project_id=str(raw.get("project_id", project_id)),
        saved_at=str(raw.get("saved_at", "")),
        active_step=str(raw.get("active_step", "workspace")),
        message=str(raw.get("message", "")),
        payload=raw.get("payload", {}) if isinstance(raw.get("payload", {}), dict) else {},
    )


def clear_project_recovery_state(root: Path | str, project_id: str) -> bool:
    path = _project_dir(root, project_id) / PROJECT_RECOVERY_FILE_NAME
    if not path.exists():
        return False
    path.unlink()
    append_project_history(root, project_id, "recovery-cleared", "Recovery checkpoint cleared", object_type="recovery")
    return True


def create_project_template(
    root: Path | str,
    source_project_id: str,
    name: str,
    description: str = "",
    *,
    template_id: str | None = None,
    include_structure: bool = True,
) -> ProjectTemplate:
    source = load_project(root, source_project_id)
    now = _utc_now()
    clean_id = safe_project_id(template_id or f"{now[:10].replace('-', '')}-{source.id}-template")
    template = ProjectTemplate(
        id=clean_id,
        name=name.strip() or f"{source.name} template",
        description=description.strip(),
        created_at=now,
        source_project_id=source.id,
        include_structure=include_structure,
    )
    payload = {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "created_at": template.created_at,
        "source_project_id": template.source_project_id,
        "include_structure": template.include_structure,
        "project": {
            "name": source.name,
            "description": source.description,
        },
    }
    _json_write(Path(root) / PROJECT_TEMPLATES_DIR_NAME / f"{template.id}.json", payload)
    append_project_history(root, source.id, "template-created", f"Template created: {template.name}", object_type="template", object_id=template.id)
    return template


def _template_from_dict(raw: dict[str, Any]) -> ProjectTemplate:
    return ProjectTemplate(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")),
        description=str(raw.get("description", "")),
        created_at=str(raw.get("created_at", "")),
        source_project_id=str(raw.get("source_project_id", "")),
        include_structure=bool(raw.get("include_structure", True)),
    )


def list_project_templates(root: Path | str) -> tuple[ProjectTemplate, ...]:
    templates_dir = Path(root) / PROJECT_TEMPLATES_DIR_NAME
    if not templates_dir.exists():
        return ()
    templates: list[ProjectTemplate] = []
    for path in sorted(templates_dir.glob("*.json")):
        raw = _json_read(path, {})
        if isinstance(raw, dict):
            template = _template_from_dict(raw)
            if template.id and template.name:
                templates.append(template)
    return tuple(sorted(templates, key=lambda item: item.created_at, reverse=True))


def create_project_from_template(
    root: Path | str,
    template_id: str,
    name: str,
    description: str = "",
) -> ProjectRecord:
    template_path = Path(root) / PROJECT_TEMPLATES_DIR_NAME / f"{safe_project_id(template_id)}.json"
    raw = _json_read(template_path, {})
    if not isinstance(raw, dict) or not raw.get("id"):
        raise FileNotFoundError(f"Project template not found: {template_id}")
    project_payload = raw.get("project", {}) if isinstance(raw.get("project", {}), dict) else {}
    project = create_project(
        root,
        name=name.strip() or str(project_payload.get("name", "Project from template")),
        description=description.strip() or str(project_payload.get("description", "")),
    )
    append_project_history(root, project.id, "created-from-template", f"Created from template: {template_id}", object_type="template", object_id=template_id)
    return project


def create_project_backup(
    root: Path | str,
    project_id: str,
    description: str = "",
) -> ProjectBackupRecord:
    safe_id = safe_project_id(project_id)
    project_path = _project_dir(root, safe_id)
    if not project_path.exists():
        raise FileNotFoundError(f"Project not found: {project_id}")
    now = _utc_now()
    backups_dir = Path(root) / PROJECT_BACKUPS_DIR_NAME
    backups_dir.mkdir(parents=True, exist_ok=True)
    base_backup_id = f"{now.replace(':', '').replace('-', '')}-{safe_id}"
    backup_id = base_backup_id
    counter = 2
    while (backups_dir / f"{backup_id}.zip").exists():
        backup_id = f"{base_backup_id}-{counter}"
        counter += 1
    file_name = f"{backup_id}.zip"
    archive_base = backups_dir / backup_id
    archive_path = Path(shutil.make_archive(str(archive_base), "zip", root_dir=project_path))
    record = ProjectBackupRecord(
        id=backup_id,
        project_id=safe_id,
        file_name=file_name,
        created_at=now,
        size_bytes=archive_path.stat().st_size,
        description=description.strip(),
    )
    append_project_history(root, safe_id, "backup-created", f"Backup created: {file_name}", object_type="backup", object_id=backup_id)
    return record


def list_project_backups(root: Path | str, project_id: str | None = None) -> tuple[ProjectBackupRecord, ...]:
    backups_dir = Path(root) / PROJECT_BACKUPS_DIR_NAME
    if not backups_dir.exists():
        return ()
    records: list[ProjectBackupRecord] = []
    safe_filter = safe_project_id(project_id) if project_id else None
    for path in sorted(backups_dir.glob("*.zip")):
        stem = path.stem
        parts = stem.split("-", 1)
        detected_project_id = parts[1] if len(parts) == 2 else ""
        if safe_filter:
            if detected_project_id != safe_filter and not detected_project_id.startswith(f"{safe_filter}-"):
                continue
            detected_project_id = safe_filter
        elif detected_project_id.rsplit("-", 1)[-1].isdigit():
            detected_project_id = detected_project_id.rsplit("-", 1)[0]
        created_at = parts[0] if parts else ""
        records.append(ProjectBackupRecord(stem, detected_project_id, path.name, created_at, path.stat().st_size))
    return tuple(sorted(records, key=lambda item: item.created_at, reverse=True))



def _find_project_backup_path(root: Path | str, backup_id: str) -> Path:
    backups_dir = Path(root) / PROJECT_BACKUPS_DIR_NAME
    clean_backup_id = safe_project_id(backup_id).strip()
    path = backups_dir / f"{clean_backup_id}.zip"
    if not path.exists():
        raise FileNotFoundError(f"Project backup not found: {backup_id}")
    return path


def _safe_extract_zip(archive_path: Path, target_dir: Path) -> int:
    """Extract a ZIP archive while rejecting path traversal entries."""
    target_root = target_dir.resolve()
    files_restored = 0
    with zipfile.ZipFile(archive_path, "r") as archive:
        for member in archive.infolist():
            member_target = (target_dir / member.filename).resolve()
            if target_root != member_target and target_root not in member_target.parents:
                raise ValueError(f"Unsafe backup entry: {member.filename}")
            if member.is_dir():
                member_target.mkdir(parents=True, exist_ok=True)
                continue
            member_target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member, "r") as source, member_target.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            files_restored += 1
    return files_restored


def restore_project_backup(
    root: Path | str,
    backup_id: str,
    *,
    target_project_id: str | None = None,
    overwrite: bool = False,
) -> ProjectRestoreResult:
    """Restore a project directory from a managed backup ZIP archive.

    The function restores only archives created by Project Manager 2.0 and
    validates every ZIP member before extraction. Existing projects are not
    overwritten unless ``overwrite=True`` is passed by a service/controller.
    """
    root_path = Path(root)
    archive_path = _find_project_backup_path(root_path, backup_id)
    backup_records = [record for record in list_project_backups(root_path) if record.id == archive_path.stem]
    detected_project_id = backup_records[0].project_id if backup_records else archive_path.stem.split("-", 1)[-1]
    clean_project_id = safe_project_id(target_project_id or detected_project_id)
    target_dir = _project_dir(root_path, clean_project_id)
    overwritten_existing = target_dir.exists()
    if overwritten_existing and not overwrite:
        raise FileExistsError(f"Project already exists: {clean_project_id}")

    tmp_dir = root_path / f".restore-{clean_project_id}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        files_restored = _safe_extract_zip(archive_path, tmp_dir)
        project_file = tmp_dir / PROJECT_FILE_NAME
        if not project_file.exists():
            raise ValueError("Backup does not contain project.json")

        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.move(str(tmp_dir), str(target_dir))
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)

    append_project_history(
        root_path,
        clean_project_id,
        "backup-restored",
        f"Project restored from backup: {archive_path.name}",
        object_type="backup",
        object_id=archive_path.stem,
    )
    return ProjectRestoreResult(
        project_id=clean_project_id,
        backup_id=archive_path.stem,
        restored_path=str(target_dir),
        overwritten_existing=overwritten_existing,
        files_restored=files_restored,
    )

def archive_project(root: Path | str, project_id: str, description: str = "") -> ProjectBackupRecord:
    """Create a backup and mark the project as archived through history metadata."""
    record = create_project_backup(root, project_id, description or "Project archived backup")
    append_project_history(root, project_id, "project-archived", description or "Project marked as archived", object_type="project")
    return record


def build_project_history_table(entries: tuple[ProjectHistoryEntry, ...]) -> list[dict[str, str]]:
    return [
        {
            "Дата": entry.created_at,
            "Действие": entry.action,
            "Описание": entry.description,
            "Объект": entry.object_type,
            "ID объекта": entry.object_id,
            "Автор": entry.author,
        }
        for entry in entries
    ]


def build_project_templates_table(templates: tuple[ProjectTemplate, ...]) -> list[dict[str, str]]:
    return [
        {
            "Шаблон": template.name,
            "Описание": template.description,
            "Источник": template.source_project_id,
            "Создан": template.created_at,
            "ID": template.id,
        }
        for template in templates
    ]


def build_project_backups_table(backups: tuple[ProjectBackupRecord, ...]) -> list[dict[str, str | int]]:
    return [
        {
            "Архив": backup.file_name,
            "Проект": backup.project_id,
            "Создан": backup.created_at,
            "Размер, байт": backup.size_bytes,
            "Описание": backup.description,
        }
        for backup in backups
    ]


def project_manager_status(root: Path | str, project_id: str) -> dict[str, int | bool]:
    return {
        "history_entries": len(list_project_history(root, project_id)),
        "templates": len(list_project_templates(root)),
        "backups": len(list_project_backups(root, project_id)),
        "has_recovery_state": load_project_recovery_state(root, project_id) is not None,
    }
