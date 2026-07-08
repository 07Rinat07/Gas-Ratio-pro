from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id


PROJECT_EXPORTS_DIR_NAME = "exports"
PROJECT_EXPORTS_MANIFEST_FILE_NAME = "exports.json"
PROJECT_EXPORTS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProjectExportRecord:
    id: str
    label: str
    kind: str
    file_name: str
    mime_type: str
    saved_at: str
    size_bytes: int
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", value.strip()).strip("-").lower()
    return slug or "export"


def _safe_export_id(value: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", value):
        raise ValueError("Некорректный идентификатор экспорта проекта.")
    return value


def _safe_file_name(value: str) -> str:
    file_name = Path(str(value)).name.strip()
    if not file_name:
        return "export.bin"
    safe_name = re.sub(r"[^0-9A-Za-zА-Яа-я_.-]+", "_", file_name).strip("._")
    return safe_name or "export.bin"


def _exports_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_EXPORTS_DIR_NAME


def _manifest_path(root: Path | str, project_id: str) -> Path:
    return _exports_dir(root, project_id) / PROJECT_EXPORTS_MANIFEST_FILE_NAME


def _export_dir(root: Path | str, project_id: str, export_id: str) -> Path:
    return _exports_dir(root, project_id) / _safe_export_id(export_id)


def _record_from_dict(raw: dict[str, Any]) -> ProjectExportRecord:
    return ProjectExportRecord(
        id=str(raw.get("id", "")),
        label=str(raw.get("label", "")) or "Экспорт",
        kind=str(raw.get("kind", "")),
        file_name=str(raw.get("file_name", "")) or "export.bin",
        mime_type=str(raw.get("mime_type", "")) or "application/octet-stream",
        saved_at=str(raw.get("saved_at", "")),
        size_bytes=int(raw.get("size_bytes", 0) or 0),
        source=str(raw.get("source", "")),
        metadata=dict(raw.get("metadata", {})),
    )


def _record_to_dict(record: ProjectExportRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "label": record.label,
        "kind": record.kind,
        "file_name": record.file_name,
        "mime_type": record.mime_type,
        "saved_at": record.saved_at,
        "size_bytes": record.size_bytes,
        "source": record.source,
        "metadata": record.metadata,
    }


def _read_manifest(root: Path | str, project_id: str) -> tuple[ProjectExportRecord, ...]:
    path = _manifest_path(root, project_id)
    if not path.exists():
        return ()

    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("exports", ()) if isinstance(payload, dict) else ()
    return tuple(_record_from_dict(record) for record in records)


def _write_manifest(root: Path | str, project_id: str, records: tuple[ProjectExportRecord, ...]) -> Path:
    path = _manifest_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_EXPORTS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "exports": [_record_to_dict(record) for record in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_project_exports(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectExportRecord, ...]:
    try:
        records = _read_manifest(root, project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()
    return tuple(sorted(records, key=lambda record: record.saved_at, reverse=True))


def save_project_export(
    data: bytes,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    label: str = "Экспорт",
    file_name: str = "export.bin",
    mime_type: str = "application/octet-stream",
    kind: str = "",
    source: str = "",
    metadata: dict[str, Any] | None = None,
) -> ProjectExportRecord:
    if not data:
        raise ValueError("Нет данных экспорта для сохранения в проект.")

    clean_label = label.strip() or "Экспорт"
    clean_kind = kind.strip() or "export"
    clean_file_name = _safe_file_name(file_name)
    now = _utc_now()
    base_id = f"{now[:10].replace('-', '')}-{_slugify(clean_kind)}-{_slugify(clean_label)}"
    export_id = base_id
    counter = 2
    while _export_dir(root, project_id, export_id).exists():
        export_id = f"{base_id}-{counter}"
        counter += 1

    export_dir = _export_dir(root, project_id, export_id)
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / clean_file_name).write_bytes(data)

    record = ProjectExportRecord(
        id=export_id,
        label=clean_label,
        kind=clean_kind,
        file_name=clean_file_name,
        mime_type=mime_type.strip() or "application/octet-stream",
        saved_at=now,
        size_bytes=len(data),
        source=source.strip(),
        metadata=metadata or {},
    )
    records = (record, *tuple(item for item in _read_manifest(root, project_id) if item.id != record.id))
    _write_manifest(root, project_id, records)
    return record


def read_project_export_file_bytes(
    root: Path | str,
    project_id: str,
    export_id: str,
) -> bytes:
    records = {record.id: record for record in list_project_exports(root, project_id)}
    if export_id not in records:
        raise FileNotFoundError(f"Project export not found: {export_id}")
    record = records[export_id]
    return (_export_dir(root, project_id, export_id) / Path(record.file_name).name).read_bytes()
