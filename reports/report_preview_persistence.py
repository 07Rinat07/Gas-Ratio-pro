from __future__ import annotations

"""Project-scoped persistence for compact report-preview count snapshots.

Only validated JSON metadata is stored. Engineering dataframes, document models,
rendered files, and credentials are never persisted by this repository.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping

from reports.report_designer import (
    REPORT_DOCUMENT_COUNTS_SNAPSHOT_SCHEMA,
    migrate_report_document_counts_snapshot,
    resolve_report_document_counts_snapshot,
)

_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")
_FILE_NAME = "report_preview_counts.json"
_BACKUP_SUFFIX = ".json.bak"
_DEFAULT_MAX_QUARANTINE_FILES = 3




@dataclass(frozen=True)
class ReportPreviewCountsStorageHealth:
    """Read-only health summary for one project's preview metadata storage."""

    status: str
    primary_exists: bool = False
    primary_valid: bool = False
    backup_exists: bool = False
    backup_valid: bool = False
    quarantine_count: int = 0
    quarantine_bytes: int = 0
    total_bytes: int = 0
    current_schema: int = REPORT_DOCUMENT_COUNTS_SNAPSHOT_SCHEMA
    primary_schema: int | None = None
    backup_schema: int | None = None
    migration_required: bool = False
    message: str = ""


@dataclass(frozen=True)
class ReportPreviewCountsMaintenanceResult:
    """Result of bounded quarantine-file maintenance for one project."""

    kept: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReportPreviewCountsLoadResult:
    """Outcome of a durable snapshot load attempt."""

    payload: dict[str, Any] | None
    source: str
    recovered: bool = False
    quarantined: tuple[str, ...] = ()
    migrated: bool = False
    migration_persisted: bool = False
    source_schema: int | None = None
    target_schema: int = REPORT_DOCUMENT_COUNTS_SNAPSHOT_SCHEMA
    message: str = ""


@dataclass(frozen=True)
class _ValidatedSnapshot:
    payload: dict[str, Any]
    original_payload: dict[str, Any]
    source_schema: int | None
    target_schema: int
    migrated: bool


class _UnsupportedSnapshotSchemaError(ValueError):
    """Raised when an older build encounters a snapshot from a newer build."""

    def __init__(self, message: str, *, source_schema: int | None = None) -> None:
        super().__init__(message)
        self.source_schema = source_schema


class ReportPreviewCountsRepository:
    """Persist one compact report-count snapshot per project atomically.

    The previous valid primary file is retained as a backup. If the primary is
    truncated or malformed, ``load_with_recovery`` restores the backup and
    quarantines damaged files instead of propagating broken metadata into UI.
    """

    def __init__(
        self,
        root_dir: Path | str,
        *,
        max_quarantine_files: int = _DEFAULT_MAX_QUARANTINE_FILES,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.max_quarantine_files = max(0, int(max_quarantine_files))

    def path_for(self, project_id: str) -> Path:
        safe_id = _SAFE_ID.sub("_", str(project_id or "").strip()).strip("._")
        if not safe_id:
            raise ValueError("project_id is required")
        return self.root_dir / safe_id / _FILE_NAME

    def backup_path_for(self, project_id: str) -> Path:
        return self.path_for(project_id).with_suffix(_BACKUP_SUFFIX)

    @staticmethod
    def _validated_snapshot(payload: object) -> _ValidatedSnapshot:
        if not isinstance(payload, Mapping):
            raise ValueError("report preview snapshot must be a mapping")
        original = dict(payload)
        migration = migrate_report_document_counts_snapshot(original)
        if migration.payload is None:
            if migration.state == "unsupported":
                raise _UnsupportedSnapshotSchemaError(
                    migration.message,
                    source_schema=migration.source_schema,
                )
            raise ValueError(f"invalid report preview snapshot: {migration.state}")
        normalized = dict(migration.payload)
        signature = str(normalized.get("signature") or "").strip()
        resolution = resolve_report_document_counts_snapshot(
            normalized,
            expected_signature=signature,
        )
        if resolution.state != "current" or resolution.counts is None:
            raise ValueError(f"invalid report preview snapshot: {resolution.state}")
        return _ValidatedSnapshot(
            payload=normalized,
            original_payload=original,
            source_schema=migration.source_schema,
            target_schema=migration.target_schema,
            migrated=migration.migrated,
        )

    @classmethod
    def _validated_payload(cls, payload: object) -> dict[str, Any]:
        return cls._validated_snapshot(payload).payload

    @classmethod
    def _read_validated_snapshot(cls, path: Path) -> _ValidatedSnapshot:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls._validated_snapshot(payload)

    @classmethod
    def _read_validated_file(cls, path: Path) -> dict[str, Any]:
        return cls._read_validated_snapshot(path).payload

    @staticmethod
    def _write_atomic(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(
            json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    def save(self, project_id: str, payload: Mapping[str, Any]) -> Path:
        """Validate and atomically persist a snapshot with one valid backup."""
        clean_project_id = str(project_id or "").strip()
        if not clean_project_id:
            raise ValueError("project_id is required")
        normalized = self._validated_payload(payload)

        target = self.path_for(clean_project_id)
        backup = self.backup_path_for(clean_project_id)
        if target.exists():
            try:
                previous = self._read_validated_file(target)
            except _UnsupportedSnapshotSchemaError:
                raise ValueError(
                    "cannot overwrite a report preview snapshot created by a newer application version"
                ) from None
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                previous = None
            if previous is not None:
                self._write_atomic(backup, previous)

        self._write_atomic(target, normalized)
        return target

    def load_with_recovery(self, project_id: str) -> ReportPreviewCountsLoadResult:
        """Load primary metadata, recovering from a valid backup when needed."""
        target = self.path_for(project_id)
        backup = self.backup_path_for(project_id)
        if not target.exists() and not backup.exists():
            self.maintain_quarantine(project_id)
            return ReportPreviewCountsLoadResult(None, "missing", message="Снимок ещё не сохранён.")

        primary_error: Exception | None = None
        if target.exists():
            try:
                validated = self._read_validated_snapshot(target)
                migration_persisted = False
                message = "Снимок загружен из проектного хранилища."
                if validated.migrated:
                    try:
                        # Keep the exact pre-migration payload as the rollback
                        # copy, then atomically replace the primary with the
                        # canonical current-schema representation.
                        self._write_atomic(backup, validated.original_payload)
                        self._write_atomic(target, validated.payload)
                        migration_persisted = True
                        message = (
                            f"Снимок автоматически мигрирован со схемы v{validated.source_schema} "
                            f"на v{validated.target_schema}."
                        )
                    except OSError:
                        message = (
                            f"Снимок мигрирован в памяти со схемы v{validated.source_schema} "
                            f"на v{validated.target_schema}, но обновить файл не удалось."
                        )
                self.maintain_quarantine(project_id)
                return ReportPreviewCountsLoadResult(
                    validated.payload,
                    "primary",
                    migrated=validated.migrated,
                    migration_persisted=migration_persisted,
                    source_schema=validated.source_schema,
                    target_schema=validated.target_schema,
                    message=message,
                )
            except _UnsupportedSnapshotSchemaError as exc:
                return ReportPreviewCountsLoadResult(
                    None,
                    "unsupported",
                    source_schema=exc.source_schema,
                    message=str(exc),
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                primary_error = exc

        if backup.exists():
            try:
                validated = self._read_validated_snapshot(backup)
                quarantined = self._quarantine_existing((target,))
                self._write_atomic(target, validated.payload)
                self.maintain_quarantine(project_id)
                migration_note = (
                    f" Резервная копия мигрирована со схемы v{validated.source_schema} "
                    f"на v{validated.target_schema}."
                    if validated.migrated
                    else ""
                )
                return ReportPreviewCountsLoadResult(
                    validated.payload,
                    "backup",
                    recovered=True,
                    quarantined=quarantined,
                    migrated=validated.migrated,
                    migration_persisted=validated.migrated,
                    source_schema=validated.source_schema,
                    target_schema=validated.target_schema,
                    message=(
                        "Повреждённый основной снимок восстановлен из резервной копии."
                        + migration_note
                    ),
                )
            except _UnsupportedSnapshotSchemaError as exc:
                return ReportPreviewCountsLoadResult(
                    None,
                    "unsupported",
                    source_schema=exc.source_schema,
                    message=str(exc),
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass

        quarantined = self._quarantine_existing((target, backup))
        self.maintain_quarantine(project_id)
        detail = f": {primary_error}" if primary_error is not None else ""
        return ReportPreviewCountsLoadResult(
            None,
            "quarantined",
            quarantined=quarantined,
            message=f"Повреждённые снимки изолированы; используется эвристический предпросмотр{detail}",
        )

    def load(self, project_id: str) -> dict[str, Any] | None:
        """Backward-compatible load with automatic recovery."""
        return self.load_with_recovery(project_id).payload

    def storage_health(self, project_id: str) -> ReportPreviewCountsStorageHealth:
        """Inspect metadata files without changing or recovering them."""
        target = self.path_for(project_id)
        backup = self.backup_path_for(project_id)
        quarantined = self.quarantine_paths(project_id)

        def inspect(path: Path) -> tuple[bool, bool, int, int | None, bool, bool]:
            if not path.exists():
                return False, False, 0, None, False, False
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            try:
                validated = self._read_validated_snapshot(path)
            except _UnsupportedSnapshotSchemaError as exc:
                return True, False, size, exc.source_schema, False, True
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                return True, False, size, None, False, False
            return (
                True,
                True,
                size,
                validated.source_schema,
                validated.migrated,
                False,
            )

        (
            primary_exists,
            primary_valid,
            primary_bytes,
            primary_schema,
            primary_migration,
            primary_unsupported,
        ) = inspect(target)
        (
            backup_exists,
            backup_valid,
            backup_bytes,
            backup_schema,
            backup_migration,
            backup_unsupported,
        ) = inspect(backup)
        quarantine_bytes = 0
        for path in quarantined:
            try:
                quarantine_bytes += path.stat().st_size
            except OSError:
                continue

        if primary_unsupported or (not primary_valid and backup_unsupported):
            status = "unsupported"
            message = "Снимок создан более новой версией приложения и оставлен без изменений."
        elif primary_valid and primary_migration:
            status = "migration_available"
            message = "Основной снимок корректен и будет автоматически обновлён до текущей схемы."
        elif primary_valid:
            status = "healthy"
            message = "Основной снимок корректен."
        elif backup_valid:
            status = "recoverable"
            message = "Основной снимок отсутствует или повреждён; доступна корректная резервная копия."
        elif primary_exists or backup_exists:
            status = "degraded"
            message = "Метаданные предпросмотра повреждены и требуют восстановления или очистки."
        elif quarantined:
            status = "quarantined"
            message = "Активного снимка нет; обнаружены изолированные повреждённые файлы."
        else:
            status = "empty"
            message = "Снимок предпросмотра ещё не сохранён."

        return ReportPreviewCountsStorageHealth(
            status=status,
            primary_exists=primary_exists,
            primary_valid=primary_valid,
            backup_exists=backup_exists,
            backup_valid=backup_valid,
            quarantine_count=len(quarantined),
            quarantine_bytes=quarantine_bytes,
            total_bytes=primary_bytes + backup_bytes + quarantine_bytes,
            primary_schema=primary_schema,
            backup_schema=backup_schema,
            migration_required=primary_migration or backup_migration,
            message=message,
        )


    def _quarantine_existing(self, paths: tuple[Path, ...]) -> tuple[str, ...]:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        quarantined: list[str] = []
        for index, path in enumerate(paths):
            if not path.exists():
                continue
            suffix = f".corrupt-{stamp}"
            if index:
                suffix += f"-{index}"
            destination = path.with_name(path.name + suffix)
            path.replace(destination)
            quarantined.append(str(destination))
        return tuple(quarantined)

    def quarantine_paths(self, project_id: str) -> tuple[Path, ...]:
        """Return project quarantine files newest-first."""
        directory = self.path_for(project_id).parent
        if not directory.exists():
            return ()
        candidates = [
            path
            for path in directory.iterdir()
            if path.is_file() and ".corrupt-" in path.name
            and path.name.startswith(_FILE_NAME)
        ]
        candidates.sort(
            key=lambda path: (path.stat().st_mtime_ns, path.name),
            reverse=True,
        )
        return tuple(candidates)

    def maintain_quarantine(self, project_id: str) -> ReportPreviewCountsMaintenanceResult:
        """Keep only the newest bounded set of quarantined snapshot files."""
        paths = self.quarantine_paths(project_id)
        kept = paths[: self.max_quarantine_files]
        removed: list[str] = []
        for path in paths[self.max_quarantine_files :]:
            try:
                path.unlink()
                removed.append(str(path))
            except FileNotFoundError:
                continue
        return ReportPreviewCountsMaintenanceResult(
            kept=tuple(str(path) for path in kept if path.exists()),
            removed=tuple(removed),
        )

    def purge_quarantine(self, project_id: str) -> tuple[str, ...]:
        """Delete all quarantined snapshot files for one project."""
        removed: list[str] = []
        for path in self.quarantine_paths(project_id):
            try:
                path.unlink()
                removed.append(str(path))
            except FileNotFoundError:
                continue
        return tuple(removed)

    def delete(self, project_id: str, *, include_quarantine: bool = False) -> bool:
        deleted = False
        for target in (self.path_for(project_id), self.backup_path_for(project_id)):
            if target.exists():
                target.unlink()
                deleted = True
        if include_quarantine and self.purge_quarantine(project_id):
            deleted = True
        return deleted
