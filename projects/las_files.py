from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id


PROJECT_WELLS_DIR_NAME = "wells"
PROJECT_LAS_MANIFEST_FILE_NAME = "las_files.json"
PROJECT_LAS_SOURCE_FILE_NAME = "source.las"
PROJECT_LAS_FILES_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProjectLasFile:
    id: str
    name: str
    original_file_name: str
    saved_at: str
    size_bytes: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", value.strip()).strip("-").lower()
    return slug or "las"


def _safe_las_file_id(value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", value):
        raise ValueError("Некорректный идентификатор LAS-файла проекта.")
    return value


def _project_wells_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_WELLS_DIR_NAME


def _manifest_path(root: Path | str, project_id: str) -> Path:
    return _project_wells_dir(root, project_id) / PROJECT_LAS_MANIFEST_FILE_NAME


def _las_file_dir(root: Path | str, project_id: str, las_file_id: str) -> Path:
    return _project_wells_dir(root, project_id) / _safe_las_file_id(las_file_id)


def _record_from_dict(raw: dict[str, Any]) -> ProjectLasFile:
    return ProjectLasFile(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")) or "Без названия",
        original_file_name=str(raw.get("original_file_name", "")) or "source.las",
        saved_at=str(raw.get("saved_at", "")),
        size_bytes=int(raw.get("size_bytes", 0) or 0),
    )


def _record_to_dict(record: ProjectLasFile) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "original_file_name": record.original_file_name,
        "saved_at": record.saved_at,
        "size_bytes": record.size_bytes,
    }


def _read_manifest(root: Path | str, project_id: str) -> tuple[ProjectLasFile, ...]:
    path = _manifest_path(root, project_id)
    if not path.exists():
        return ()

    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("las_files", ()) if isinstance(payload, dict) else ()
    return tuple(_record_from_dict(record) for record in records)


def _write_manifest(root: Path | str, project_id: str, records: tuple[ProjectLasFile, ...]) -> Path:
    path = _manifest_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_LAS_FILES_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "las_files": [_record_to_dict(record) for record in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_project_las_files(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectLasFile, ...]:
    try:
        records = _read_manifest(root, project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()
    return tuple(sorted(records, key=lambda record: record.saved_at, reverse=True))


def save_project_las_file(
    data: bytes,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    file_name: str = "source.las",
    well_name: str = "",
) -> ProjectLasFile:
    if not data:
        raise ValueError("Нет данных LAS для сохранения в проект.")

    safe_original_name = Path(str(file_name)).name or "source.las"
    clean_well_name = well_name.strip() or Path(safe_original_name).stem or "LAS"
    now = _utc_now()
    base_id = f"{now[:10].replace('-', '')}-{_slugify(clean_well_name)}"
    las_file_id = base_id
    counter = 2
    while _las_file_dir(root, project_id, las_file_id).exists():
        las_file_id = f"{base_id}-{counter}"
        counter += 1

    las_dir = _las_file_dir(root, project_id, las_file_id)
    las_dir.mkdir(parents=True, exist_ok=True)
    (las_dir / PROJECT_LAS_SOURCE_FILE_NAME).write_bytes(data)

    record = ProjectLasFile(
        id=las_file_id,
        name=clean_well_name,
        original_file_name=safe_original_name,
        saved_at=now,
        size_bytes=len(data),
    )
    records = (record, *tuple(item for item in _read_manifest(root, project_id) if item.id != record.id))
    _write_manifest(root, project_id, records)
    return record


def read_project_las_file_bytes(
    root: Path | str,
    project_id: str,
    las_file_id: str,
) -> bytes:
    records = {record.id: record for record in list_project_las_files(root, project_id)}
    if las_file_id not in records:
        raise FileNotFoundError(f"Project LAS file not found: {las_file_id}")
    return (_las_file_dir(root, project_id, las_file_id) / PROJECT_LAS_SOURCE_FILE_NAME).read_bytes()
