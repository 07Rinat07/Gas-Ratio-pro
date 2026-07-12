from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from projects.repository import safe_project_id

PROJECT_INDEX_FILE_NAME = "project_index.json"
PROJECT_FILE_VERSIONS_FILE_NAME = "project_file_versions.json"
PROJECT_UUID_REGISTRY_FILE_NAME = "project_uuids.json"
PROJECT_INDEX_SCHEMA_VERSION = 1
PROJECT_FILE_VERSIONS_SCHEMA_VERSION = 1
PROJECT_UUID_REGISTRY_SCHEMA_VERSION = 1
_INDEX_EXCLUDED_NAMES = {PROJECT_INDEX_FILE_NAME, PROJECT_FILE_VERSIONS_FILE_NAME, PROJECT_UUID_REGISTRY_FILE_NAME}
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
class ProjectFileVersionRecord:
    """One immutable metadata version for a file tracked by Project Database."""

    id: str
    version_number: int
    relative_path: str
    name: str
    kind: str
    size_bytes: int
    modified_at: str
    checksum_sha256: str
    created_at: str
    author: str = "local"
    status: str = "active"
    change_summary: str = "Initial version"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectFileVersionAsset:
    """Version history for one logical project file path."""

    asset_key: str
    relative_path: str
    name: str
    kind: str
    active_version_id: str
    versions: tuple[ProjectFileVersionRecord, ...]

    @property
    def active_version(self) -> ProjectFileVersionRecord | None:
        for version in self.versions:
            if version.id == self.active_version_id:
                return version
        return self.versions[-1] if self.versions else None

    @property
    def version_count(self) -> int:
        return len(self.versions)


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


@dataclass(frozen=True)
class ProjectUuidEntry:
    """Stable UUID assigned to one logical project object."""

    logical_key: str
    object_type: str
    object_id: str
    uuid: str
    status: str = "active"
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def status_label(self) -> str:
        labels = {
            "active": "активный",
            "restored": "восстановлен",
            "warning": "требует проверки",
        }
        return labels.get(self.status, self.status)


@dataclass(frozen=True)
class ProjectUuidRegistrySummary:
    """Compact result of automatic UUID registry refresh."""

    entries: tuple[ProjectUuidEntry, ...]
    created_count: int = 0
    restored_count: int = 0
    duplicate_uuid_count: int = 0

    @property
    def total_count(self) -> int:
        return len(self.entries)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _index_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_INDEX_FILE_NAME


def _file_versions_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_FILE_VERSIONS_FILE_NAME


def _uuid_registry_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_UUID_REGISTRY_FILE_NAME


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


def _asset_key_from_entry(entry: ProjectFileIndexEntry) -> str:
    return entry.relative_path.replace("\\", "/").strip().lower()


def _version_id(entry: ProjectFileIndexEntry, version_number: int) -> str:
    seed = f"{_asset_key_from_entry(entry)}::{entry.checksum_sha256}::{version_number}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _version_record_to_dict(record: ProjectFileVersionRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "version_number": record.version_number,
        "relative_path": record.relative_path,
        "name": record.name,
        "kind": record.kind,
        "size_bytes": record.size_bytes,
        "modified_at": record.modified_at,
        "checksum_sha256": record.checksum_sha256,
        "created_at": record.created_at,
        "author": record.author,
        "status": record.status,
        "change_summary": record.change_summary,
        "metadata": dict(record.metadata),
    }


def _version_record_from_dict(raw: dict[str, Any]) -> ProjectFileVersionRecord:
    return ProjectFileVersionRecord(
        id=str(raw.get("id", "")),
        version_number=int(raw.get("version_number", 0) or 0),
        relative_path=str(raw.get("relative_path", "")),
        name=str(raw.get("name", "")),
        kind=str(raw.get("kind", "File")),
        size_bytes=int(raw.get("size_bytes", 0) or 0),
        modified_at=str(raw.get("modified_at", "")),
        checksum_sha256=str(raw.get("checksum_sha256", "")),
        created_at=str(raw.get("created_at", "")),
        author=str(raw.get("author", "local")),
        status=str(raw.get("status", "active")),
        change_summary=str(raw.get("change_summary", "")),
        metadata=dict(raw.get("metadata") or {}),
    )


def _version_asset_to_dict(asset: ProjectFileVersionAsset) -> dict[str, Any]:
    return {
        "asset_key": asset.asset_key,
        "relative_path": asset.relative_path,
        "name": asset.name,
        "kind": asset.kind,
        "active_version_id": asset.active_version_id,
        "versions": [_version_record_to_dict(version) for version in asset.versions],
    }


def _version_asset_from_dict(raw: dict[str, Any]) -> ProjectFileVersionAsset:
    return ProjectFileVersionAsset(
        asset_key=str(raw.get("asset_key", "")),
        relative_path=str(raw.get("relative_path", "")),
        name=str(raw.get("name", "")),
        kind=str(raw.get("kind", "File")),
        active_version_id=str(raw.get("active_version_id", "")),
        versions=tuple(
            _version_record_from_dict(item)
            for item in raw.get("versions", ())
            if isinstance(item, dict)
        ),
    )


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


def load_project_file_versions(root: Path | str, project_id: str) -> tuple[ProjectFileVersionAsset, ...]:
    """Load metadata-only file version history for a project."""

    path = _file_versions_path(root, project_id)
    if not path.exists():
        return ()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    return tuple(
        _version_asset_from_dict(item)
        for item in raw.get("assets", ())
        if isinstance(item, dict)
    )


def update_project_file_versions(
    root: Path | str,
    project_id: str,
    *,
    author: str = "local",
) -> tuple[ProjectFileVersionAsset, ...]:
    """Update file version history from the saved project index.

    Versioning is metadata-only: the function stores checksums and file metadata
    for each logical relative path from `project_index.json`. File contents are not
    copied. A new version is appended only when the checksum for the same path was
    not seen before.
    """

    entries = tuple(entry for entry in load_project_file_index(root, project_id) if entry.status != "missing")
    existing_by_key = {asset.asset_key: asset for asset in load_project_file_versions(root, project_id)}
    now = _utc_now()
    assets: list[ProjectFileVersionAsset] = []

    for entry in sorted(entries, key=lambda item: item.relative_path):
        asset_key = _asset_key_from_entry(entry)
        existing = existing_by_key.get(asset_key)
        previous_versions = list(existing.versions) if existing else []
        matching = next((version for version in previous_versions if version.checksum_sha256 == entry.checksum_sha256), None)
        if matching:
            active_version_id = matching.id
            versions = tuple(
                ProjectFileVersionRecord(
                    id=version.id,
                    version_number=version.version_number,
                    relative_path=version.relative_path,
                    name=version.name,
                    kind=version.kind,
                    size_bytes=version.size_bytes,
                    modified_at=version.modified_at,
                    checksum_sha256=version.checksum_sha256,
                    created_at=version.created_at,
                    author=version.author,
                    status="active" if version.id == active_version_id else "archived",
                    change_summary=version.change_summary,
                    metadata=dict(version.metadata),
                )
                for version in previous_versions
            )
        else:
            version_number = len(previous_versions) + 1
            change_summary = "Initial version" if not previous_versions else "File content changed"
            new_version = ProjectFileVersionRecord(
                id=_version_id(entry, version_number),
                version_number=version_number,
                relative_path=entry.relative_path,
                name=entry.name,
                kind=entry.kind,
                size_bytes=entry.size_bytes,
                modified_at=entry.modified_at,
                checksum_sha256=entry.checksum_sha256,
                created_at=now,
                author=author.strip() or "local",
                status="active",
                change_summary=change_summary,
                metadata={
                    "well_id": entry.well_id,
                    "dataset_type": entry.dataset_type,
                    **dict(entry.metadata),
                },
            )
            versions = tuple(
                ProjectFileVersionRecord(
                    id=version.id,
                    version_number=version.version_number,
                    relative_path=version.relative_path,
                    name=version.name,
                    kind=version.kind,
                    size_bytes=version.size_bytes,
                    modified_at=version.modified_at,
                    checksum_sha256=version.checksum_sha256,
                    created_at=version.created_at,
                    author=version.author,
                    status="archived",
                    change_summary=version.change_summary,
                    metadata=dict(version.metadata),
                )
                for version in previous_versions
            ) + (new_version,)
            active_version_id = new_version.id

        assets.append(
            ProjectFileVersionAsset(
                asset_key=asset_key,
                relative_path=entry.relative_path,
                name=entry.name,
                kind=entry.kind,
                active_version_id=active_version_id,
                versions=versions,
            )
        )

    path = _file_versions_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_FILE_VERSIONS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "generated_at": now,
        "assets": [_version_asset_to_dict(asset) for asset in assets],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return tuple(assets)



def compact_project_file_versions(
    root: Path | str,
    project_id: str,
) -> tuple[ProjectFileVersionAsset, ...]:
    """Keep only the active metadata version for every file asset.

    File contents are never touched.  This operation is intended for Project
    Database maintenance when long-running projects accumulated obsolete
    checksum history that no longer has a corresponding restorable file copy.
    """

    assets = load_project_file_versions(root, project_id)
    compacted: list[ProjectFileVersionAsset] = []
    for asset in assets:
        active = asset.active_version
        if active is None:
            continue
        normalized = ProjectFileVersionRecord(
            id=active.id,
            version_number=1,
            relative_path=active.relative_path,
            name=active.name,
            kind=active.kind,
            size_bytes=active.size_bytes,
            modified_at=active.modified_at,
            checksum_sha256=active.checksum_sha256,
            created_at=active.created_at,
            author=active.author,
            status="active",
            change_summary="Compacted active metadata version",
            metadata=dict(active.metadata),
        )
        compacted.append(
            ProjectFileVersionAsset(
                asset_key=asset.asset_key,
                relative_path=asset.relative_path,
                name=asset.name,
                kind=asset.kind,
                active_version_id=normalized.id,
                versions=(normalized,),
            )
        )

    path = _file_versions_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_FILE_VERSIONS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "generated_at": _utc_now(),
        "assets": [_version_asset_to_dict(asset) for asset in compacted],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return tuple(compacted)

def build_project_file_versions_table(assets: tuple[ProjectFileVersionAsset, ...]) -> pd.DataFrame:
    """Build a compact table with active version information for UI/reporting."""

    rows = []
    for asset in assets:
        active = asset.active_version
        rows.append(
            {
                "Тип": asset.kind,
                "Файл": asset.name,
                "Путь": asset.relative_path,
                "Активная версия": active.version_number if active else "—",
                "Всего версий": asset.version_count,
                "SHA-256": active.checksum_sha256[:16] if active else "—",
                "Размер, байт": active.size_bytes if active else 0,
                "Автор": active.author if active else "—",
                "Создана версия": active.created_at if active else "—",
                "Изменение": active.change_summary if active else "—",
            }
        )
    return pd.DataFrame(rows)


def build_project_file_version_history_table(asset: ProjectFileVersionAsset) -> pd.DataFrame:
    """Build detailed version history for one project file asset."""

    return pd.DataFrame(
        [
            {
                "Версия": version.version_number,
                "Статус": "активная" if version.id == asset.active_version_id else "архив",
                "Файл": version.name,
                "Путь": version.relative_path,
                "Размер, байт": version.size_bytes,
                "SHA-256": version.checksum_sha256[:16],
                "Изменен файл": version.modified_at,
                "Создана версия": version.created_at,
                "Автор": version.author,
                "Изменение": version.change_summary,
            }
            for version in sorted(asset.versions, key=lambda item: item.version_number, reverse=True)
        ]
    )


def _uuid_entry_to_dict(entry: ProjectUuidEntry) -> dict[str, Any]:
    return {
        "logical_key": entry.logical_key,
        "object_type": entry.object_type,
        "object_id": entry.object_id,
        "uuid": entry.uuid,
        "status": entry.status,
        "warnings": list(entry.warnings),
        "metadata": dict(entry.metadata),
    }


def _uuid_entry_from_dict(raw: dict[str, Any]) -> ProjectUuidEntry:
    return ProjectUuidEntry(
        logical_key=str(raw.get("logical_key", "")),
        object_type=str(raw.get("object_type", "Object")),
        object_id=str(raw.get("object_id", "")),
        uuid=str(raw.get("uuid", "")),
        status=str(raw.get("status", "active")),
        warnings=tuple(str(item) for item in raw.get("warnings", ()) if str(item)),
        metadata=dict(raw.get("metadata") or {}),
    )


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value), version=4)
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def _new_uuid(existing: set[str]) -> str:
    while True:
        value = str(uuid.uuid4())
        if value not in existing:
            existing.add(value)
            return value


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _manifest_records(project_dir: Path, relative_path: str, key: str) -> tuple[dict[str, Any], ...]:
    payload = _load_json_file(project_dir / relative_path)
    return tuple(item for item in payload.get(key, ()) if isinstance(item, dict))


def _collect_project_uuid_specs(root: Path | str, project_id: str) -> tuple[dict[str, Any], ...]:
    """Collect logical project objects that require stable UUIDs.

    The collector is intentionally metadata-only. It reads project manifests and
    saved database metadata, but it never opens source LAS/CSV/Excel/Core/Mud Log
    or Production files and never mutates project datasets.
    """

    safe_id = safe_project_id(project_id)
    project_dir = _project_dir(root, safe_id)
    specs: list[dict[str, Any]] = [
        {
            "logical_key": f"project::{safe_id}",
            "object_type": "Project",
            "object_id": safe_id,
            "metadata": {"relative_path": "project.json"},
        }
    ]

    manifest_map = (
        ("wells/las_files.json", "las_files", "LAS Version", "wells"),
        ("datasets/csv/csv_datasets.json", "csv_datasets", "CSV Dataset", "datasets/csv"),
        ("datasets/excel/excel_datasets.json", "excel_datasets", "Excel Dataset", "datasets/excel"),
        ("datasets/core/core_datasets.json", "core_datasets", "Core Dataset", "datasets/core"),
        ("datasets/mud_log/mud_log_datasets.json", "mud_log_datasets", "Mud Log Dataset", "datasets/mud_log"),
        ("datasets/production/production_datasets.json", "production_datasets", "Production Dataset", "datasets/production"),
        ("calculations/calculations.json", "calculations", "Calculation Snapshot", "calculations"),
        ("exports/exports.json", "exports", "Export", "exports"),
        ("well_cards/well_cards.json", "well_cards", "Well", "well_cards"),
        ("well_groups.json", "groups", "Well Group", "well_groups"),
        ("project_folders.json", "folders", "Project Folder", "project_folders"),
        ("project_labels.json", "labels", "Project Label", "project_labels"),
    )
    for relative_path, key, object_type, group in manifest_map:
        for record in _manifest_records(project_dir, relative_path, key):
            object_id = str(record.get("id", "")).strip()
            if not object_id:
                continue
            specs.append(
                {
                    "logical_key": f"{group}::{object_id}",
                    "object_type": object_type,
                    "object_id": object_id,
                    "metadata": {
                        "relative_path": relative_path,
                        "name": str(record.get("name") or record.get("label") or record.get("file_name") or ""),
                    },
                }
            )

    for entry in load_project_file_index(root, safe_id):
        specs.append(
            {
                "logical_key": f"file::{entry.relative_path}",
                "object_type": "Project File",
                "object_id": entry.id,
                "metadata": {
                    "relative_path": entry.relative_path,
                    "kind": entry.kind,
                    "checksum_sha256": entry.checksum_sha256,
                    "well_id": entry.well_id,
                    "dataset_type": entry.dataset_type,
                },
            }
        )

    for asset in load_project_file_versions(root, safe_id):
        specs.append(
            {
                "logical_key": f"file_version_asset::{asset.asset_key}",
                "object_type": "File Version Asset",
                "object_id": asset.asset_key,
                "metadata": {"relative_path": asset.relative_path, "kind": asset.kind},
            }
        )
        for version in asset.versions:
            specs.append(
                {
                    "logical_key": f"file_version::{asset.asset_key}::{version.version_number}",
                    "object_type": "File Version",
                    "object_id": version.id,
                    "metadata": {
                        "relative_path": version.relative_path,
                        "version_number": version.version_number,
                        "checksum_sha256": version.checksum_sha256,
                    },
                }
            )

    unique: dict[str, dict[str, Any]] = {}
    for spec in specs:
        key = str(spec.get("logical_key", "")).strip()
        if key:
            unique.setdefault(key, spec)
    return tuple(unique[key] for key in sorted(unique))


def load_project_uuid_registry(root: Path | str, project_id: str) -> tuple[ProjectUuidEntry, ...]:
    """Load stable UUID assignments for project objects."""

    path = _uuid_registry_path(root, project_id)
    if not path.exists():
        return ()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return ()
    return tuple(
        _uuid_entry_from_dict(item)
        for item in raw.get("entries", ())
        if isinstance(item, dict)
    )


def update_project_uuid_registry(root: Path | str, project_id: str) -> ProjectUuidRegistrySummary:
    """Assign UUID v4 values to all currently known project objects.

    Existing valid UUIDs are preserved by logical key. Missing, invalid or
    duplicate UUIDs are regenerated and marked as restored so legacy project
    metadata can be safely normalized without rewriting old source files.
    """

    safe_id = safe_project_id(project_id)
    existing = {entry.logical_key: entry for entry in load_project_uuid_registry(root, safe_id)}
    used: set[str] = set()
    duplicate_candidates: set[str] = set()
    for entry in existing.values():
        if not _is_valid_uuid(entry.uuid):
            continue
        if entry.uuid in used:
            duplicate_candidates.add(entry.uuid)
        used.add(entry.uuid)

    entries: list[ProjectUuidEntry] = []
    created_count = 0
    restored_count = 0
    for spec in _collect_project_uuid_specs(root, safe_id):
        key = str(spec["logical_key"])
        previous = existing.get(key)
        warnings: list[str] = []
        status = "active"
        if previous and _is_valid_uuid(previous.uuid) and previous.uuid not in duplicate_candidates:
            value = previous.uuid
        else:
            value = _new_uuid(used)
            if previous:
                restored_count += 1
                status = "restored"
                warnings.append("UUID отсутствовал, был некорректным или повторялся; назначен новый UUID v4.")
            else:
                created_count += 1
        entries.append(
            ProjectUuidEntry(
                logical_key=key,
                object_type=str(spec.get("object_type", "Object")),
                object_id=str(spec.get("object_id", "")),
                uuid=value,
                status=status,
                warnings=tuple(warnings),
                metadata=dict(spec.get("metadata") or {}),
            )
        )

    path = _uuid_registry_path(root, safe_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_UUID_REGISTRY_SCHEMA_VERSION,
        "project_id": safe_id,
        "generated_at": _utc_now(),
        "entries": [_uuid_entry_to_dict(entry) for entry in entries],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return ProjectUuidRegistrySummary(
        entries=tuple(entries),
        created_count=created_count,
        restored_count=restored_count,
        duplicate_uuid_count=len(duplicate_candidates),
    )


def validate_project_uuid_registry(root: Path | str, project_id: str) -> ProjectUuidRegistrySummary:
    """Check current UUID registry without changing it."""

    entries = load_project_uuid_registry(root, project_id)
    seen: set[str] = set()
    duplicates = 0
    checked: list[ProjectUuidEntry] = []
    for entry in entries:
        warnings = list(entry.warnings)
        status = entry.status
        if not _is_valid_uuid(entry.uuid):
            status = "warning"
            warnings.append("UUID некорректен или отсутствует.")
        elif entry.uuid in seen:
            status = "warning"
            warnings.append("UUID повторяется в registry.")
            duplicates += 1
        seen.add(entry.uuid)
        checked.append(
            ProjectUuidEntry(
                logical_key=entry.logical_key,
                object_type=entry.object_type,
                object_id=entry.object_id,
                uuid=entry.uuid,
                status=status,
                warnings=tuple(dict.fromkeys(warnings)),
                metadata=dict(entry.metadata),
            )
        )
    return ProjectUuidRegistrySummary(entries=tuple(checked), duplicate_uuid_count=duplicates)


def build_project_uuid_registry_table(entries: tuple[ProjectUuidEntry, ...]) -> pd.DataFrame:
    """Build compact UUID registry table for UI/reporting."""

    return pd.DataFrame(
        [
            {
                "Тип": entry.object_type,
                "Object ID": entry.object_id,
                "UUID": entry.uuid,
                "Статус": entry.status_label,
                "Ключ": entry.logical_key,
                "Путь": str(entry.metadata.get("relative_path", "")) or "—",
                "Предупреждения": "; ".join(entry.warnings),
            }
            for entry in entries
        ]
    )


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
