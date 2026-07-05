from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from projects.repository import safe_project_id

PROJECT_INDEX_FILE_NAME = "project_index.json"
PROJECT_INDEX_SCHEMA_VERSION = 1
_INDEX_EXCLUDED_NAMES = {PROJECT_INDEX_FILE_NAME}
_INDEX_EXCLUDED_DIRS = {"__pycache__", ".pytest_cache"}


@dataclass(frozen=True)
class ProjectFileIndexEntry:
    """One file registered in the metadata-only project file index."""

    id: str
    relative_path: str
    name: str
    kind: str
    size_bytes: int
    modified_at: str
    checksum_sha256: str
    well_id: str = ""
    dataset_type: str = ""
    status: str = "present"
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def status_label(self) -> str:
        labels = {
            "present": "на месте",
            "missing": "отсутствует",
            "changed": "изменен",
            "warning": "требует проверки",
        }
        return labels.get(self.status, self.status)




@dataclass(frozen=True)
class ProjectDuplicateFileGroup:
    """Files that likely represent the same project asset."""

    reason: str
    match_key: str
    entries: tuple[ProjectFileIndexEntry, ...]

    @property
    def duplicate_count(self) -> int:
        return max(len(self.entries) - 1, 0)

    @property
    def reason_label(self) -> str:
        labels = {
            "checksum": "одинаковая SHA-256",
            "name_size": "одинаковое имя и размер",
        }
        return labels.get(self.reason, self.reason)

    @property
    def recommendation(self) -> str:
        if self.reason == "checksum":
            return "Оставьте один исходный файл или dataset, остальные можно удалить/заархивировать после проверки ссылок."
        if self.reason == "name_size":
            return "Проверьте содержимое файлов: имя и размер совпадают, но контрольная сумма может отличаться."
        return "Проверьте группу вручную перед удалением или объединением."


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _index_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_INDEX_FILE_NAME


def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _classify_file(relative_path: str) -> tuple[str, str]:
    normalized = relative_path.replace("\\", "/")
    parts = tuple(part.lower() for part in normalized.split("/"))
    suffix = Path(normalized).suffix.lower()

    if "las" in parts or suffix == ".las":
        return "LAS", "LAS"
    if "csv" in parts or suffix == ".csv":
        return "CSV", "CSV"
    if "excel" in parts or suffix in {".xlsx", ".xls", ".xlsm"}:
        return "Excel", "Excel"
    if "core" in parts:
        return "Core", "Core"
    if "mud_log" in parts or "mud-log" in parts:
        return "Mud Log", "Mud Log"
    if "production" in parts:
        return "Production", "Production"
    if "exports" in parts or suffix in {".html", ".pdf", ".png", ".svg", ".zip"}:
        return "Export", ""
    if suffix == ".json":
        return "Metadata", ""
    return "File", ""


def _well_id_from_path(relative_path: str) -> str:
    parts = tuple(relative_path.replace("\\", "/").split("/"))
    lowered = tuple(part.lower() for part in parts)
    for marker in ("wells", "las"):
        if marker in lowered:
            index = lowered.index(marker)
            if index + 1 < len(parts):
                return parts[index + 1]
    return ""


def _entry_to_dict(entry: ProjectFileIndexEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "relative_path": entry.relative_path,
        "name": entry.name,
        "kind": entry.kind,
        "size_bytes": entry.size_bytes,
        "modified_at": entry.modified_at,
        "checksum_sha256": entry.checksum_sha256,
        "well_id": entry.well_id,
        "dataset_type": entry.dataset_type,
        "status": entry.status,
        "warnings": list(entry.warnings),
        "metadata": dict(entry.metadata),
    }


def _entry_from_dict(raw: dict[str, Any]) -> ProjectFileIndexEntry:
    return ProjectFileIndexEntry(
        id=str(raw.get("id", "")),
        relative_path=str(raw.get("relative_path", "")),
        name=str(raw.get("name", "")),
        kind=str(raw.get("kind", "File")),
        size_bytes=int(raw.get("size_bytes", 0) or 0),
        modified_at=str(raw.get("modified_at", "")),
        checksum_sha256=str(raw.get("checksum_sha256", "")),
        well_id=str(raw.get("well_id", "")),
        dataset_type=str(raw.get("dataset_type", "")),
        status=str(raw.get("status", "present")),
        warnings=tuple(str(item) for item in raw.get("warnings", ()) if str(item)),
        metadata=dict(raw.get("metadata") or {}),
    )


def build_project_file_index(root: Path | str, project_id: str) -> tuple[ProjectFileIndexEntry, ...]:
    """Scan a project directory and build a metadata-only file index.

    The index stores relative paths, sizes, modification time and SHA-256 checksums.
    It does not copy project files and does not mutate datasets or well cards.
    """

    project_dir = _project_dir(root, project_id)
    if not project_dir.exists():
        return ()

    entries: list[ProjectFileIndexEntry] = []
    for path in sorted(project_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name in _INDEX_EXCLUDED_NAMES:
            continue
        if any(part in _INDEX_EXCLUDED_DIRS for part in path.parts):
            continue
        relative_path = path.relative_to(project_dir).as_posix()
        kind, dataset_type = _classify_file(relative_path)
        checksum = _sha256(path)
        stat = path.stat()
        entries.append(
            ProjectFileIndexEntry(
                id=checksum[:16],
                relative_path=relative_path,
                name=path.name,
                kind=kind,
                size_bytes=stat.st_size,
                modified_at=_iso_mtime(path),
                checksum_sha256=checksum,
                well_id=_well_id_from_path(relative_path),
                dataset_type=dataset_type,
                metadata={"suffix": path.suffix.lower()},
            )
        )
    return tuple(entries)


def save_project_file_index(root: Path | str, project_id: str) -> tuple[ProjectFileIndexEntry, ...]:
    entries = build_project_file_index(root, project_id)
    path = _index_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_INDEX_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "generated_at": _utc_now(),
        "entries": [_entry_to_dict(entry) for entry in entries],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return entries


def load_project_file_index(root: Path | str, project_id: str) -> tuple[ProjectFileIndexEntry, ...]:
    path = _index_path(root, project_id)
    if not path.exists():
        return ()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    return tuple(_entry_from_dict(item) for item in raw.get("entries", ()) if isinstance(item, dict))


def validate_project_file_index(root: Path | str, project_id: str) -> tuple[ProjectFileIndexEntry, ...]:
    """Compare saved index entries with files currently present on disk."""

    project_dir = _project_dir(root, project_id)
    checked: list[ProjectFileIndexEntry] = []
    for entry in load_project_file_index(root, project_id):
        file_path = project_dir / entry.relative_path
        warnings = list(entry.warnings)
        status = "present"
        if not file_path.exists():
            status = "missing"
            warnings.append("Файл отсутствует по сохраненному пути.")
            checksum = entry.checksum_sha256
            size = entry.size_bytes
            modified_at = entry.modified_at
        else:
            checksum = _sha256(file_path)
            size = file_path.stat().st_size
            modified_at = _iso_mtime(file_path)
            if checksum != entry.checksum_sha256 or size != entry.size_bytes:
                status = "changed"
                warnings.append("Файл изменился после последней индексации.")
        checked.append(
            ProjectFileIndexEntry(
                id=entry.id,
                relative_path=entry.relative_path,
                name=entry.name,
                kind=entry.kind,
                size_bytes=size,
                modified_at=modified_at,
                checksum_sha256=checksum,
                well_id=entry.well_id,
                dataset_type=entry.dataset_type,
                status=status,
                warnings=tuple(dict.fromkeys(warnings)),
                metadata=dict(entry.metadata),
            )
        )
    return tuple(checked)




def _group_duplicates(
    entries: tuple[ProjectFileIndexEntry, ...],
    *,
    key_getter,
    reason: str,
    skip_keys: set[str] | None = None,
) -> tuple[ProjectDuplicateFileGroup, ...]:
    skip_keys = skip_keys or set()
    grouped: dict[str, list[ProjectFileIndexEntry]] = {}
    for entry in entries:
        if entry.status == "missing":
            continue
        key = key_getter(entry)
        if not key or key in skip_keys:
            continue
        grouped.setdefault(key, []).append(entry)

    duplicate_groups: list[ProjectDuplicateFileGroup] = []
    for key, group_entries in sorted(grouped.items()):
        if len(group_entries) < 2:
            continue
        duplicate_groups.append(
            ProjectDuplicateFileGroup(
                reason=reason,
                match_key=key,
                entries=tuple(sorted(group_entries, key=lambda item: item.relative_path)),
            )
        )
    return tuple(duplicate_groups)


def detect_project_duplicate_files(
    entries: tuple[ProjectFileIndexEntry, ...],
) -> tuple[ProjectDuplicateFileGroup, ...]:
    """Detect likely duplicate files from a saved project file index.

    Exact duplicates are grouped by SHA-256 first. Name/size groups are added only
    when a file was not already reported as an exact checksum duplicate. This keeps
    the result compact while still surfacing suspicious repeated imports.
    """

    checksum_groups = _group_duplicates(
        entries,
        key_getter=lambda entry: entry.checksum_sha256,
        reason="checksum",
    )
    checksum_duplicate_ids = {
        entry.id
        for group in checksum_groups
        for entry in group.entries
    }
    name_size_groups = _group_duplicates(
        tuple(entry for entry in entries if entry.id not in checksum_duplicate_ids),
        key_getter=lambda entry: f"{entry.name.lower()}::{entry.size_bytes}",
        reason="name_size",
    )
    return tuple((*checksum_groups, *name_size_groups))


def detect_project_duplicate_files_from_index(
    root: Path | str,
    project_id: str,
) -> tuple[ProjectDuplicateFileGroup, ...]:
    """Load the saved project index and detect duplicate files."""

    return detect_project_duplicate_files(load_project_file_index(root, project_id))


def build_project_duplicate_files_table(groups: tuple[ProjectDuplicateFileGroup, ...]) -> pd.DataFrame:
    """Build a compact UI/report table for project duplicate groups."""

    return pd.DataFrame(
        [
            {
                "Причина": group.reason_label,
                "Совпадений": len(group.entries),
                "Лишних файлов": group.duplicate_count,
                "Ключ": group.match_key[:32],
                "Файлы": "\n".join(entry.relative_path for entry in group.entries),
                "Типы": ", ".join(sorted({entry.kind for entry in group.entries})),
                "Рекомендация": group.recommendation,
            }
            for group in groups
        ]
    )


def annotate_project_file_index_duplicates(
    entries: tuple[ProjectFileIndexEntry, ...],
    groups: tuple[ProjectDuplicateFileGroup, ...] | None = None,
) -> tuple[ProjectFileIndexEntry, ...]:
    """Return entries with warning/status markers for duplicate groups."""

    groups = detect_project_duplicate_files(entries) if groups is None else groups
    duplicate_reasons: dict[str, list[str]] = {}
    for group in groups:
        for entry in group.entries:
            duplicate_reasons.setdefault(entry.relative_path, []).append(
                f"Возможный дубликат: {group.reason_label}."
            )

    annotated: list[ProjectFileIndexEntry] = []
    for entry in entries:
        warnings = tuple(dict.fromkeys((*entry.warnings, *duplicate_reasons.get(entry.relative_path, ()))))
        status = "warning" if duplicate_reasons.get(entry.relative_path) and entry.status == "present" else entry.status
        annotated.append(
            ProjectFileIndexEntry(
                id=entry.id,
                relative_path=entry.relative_path,
                name=entry.name,
                kind=entry.kind,
                size_bytes=entry.size_bytes,
                modified_at=entry.modified_at,
                checksum_sha256=entry.checksum_sha256,
                well_id=entry.well_id,
                dataset_type=entry.dataset_type,
                status=status,
                warnings=warnings,
                metadata=dict(entry.metadata),
            )
        )
    return tuple(annotated)

def build_project_file_index_table(entries: tuple[ProjectFileIndexEntry, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Тип": entry.kind,
                "Файл": entry.name,
                "Путь": entry.relative_path,
                "Статус": entry.status_label,
                "Скважина ID": entry.well_id or "—",
                "Dataset": entry.dataset_type or "—",
                "Размер, байт": entry.size_bytes,
                "SHA-256": entry.checksum_sha256[:16],
                "Изменен": entry.modified_at,
                "Предупреждения": "; ".join(entry.warnings),
            }
            for entry in entries
        ]
    )
