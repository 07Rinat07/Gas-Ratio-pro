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

from reports.report_designer import resolve_report_document_counts_snapshot

_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")
_FILE_NAME = "report_preview_counts.json"
_BACKUP_SUFFIX = ".json.bak"
_DEFAULT_MAX_QUARANTINE_FILES = 3




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
    message: str = ""


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
    def _validated_payload(payload: object) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("report preview snapshot must be a mapping")
        normalized = dict(payload)
        signature = str(normalized.get("signature") or "").strip()
        resolution = resolve_report_document_counts_snapshot(
            normalized,
            expected_signature=signature,
        )
        if resolution.state != "current" or resolution.counts is None:
            raise ValueError(f"invalid report preview snapshot: {resolution.state}")
        return normalized

    @classmethod
    def _read_validated_file(cls, path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls._validated_payload(payload)

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
                payload = self._read_validated_file(target)
                self.maintain_quarantine(project_id)
                return ReportPreviewCountsLoadResult(
                    payload,
                    "primary",
                    message="Снимок загружен из проектного хранилища.",
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                primary_error = exc

        if backup.exists():
            try:
                payload = self._read_validated_file(backup)
                quarantined = self._quarantine_existing((target,))
                self._write_atomic(target, payload)
                self.maintain_quarantine(project_id)
                return ReportPreviewCountsLoadResult(
                    payload,
                    "backup",
                    recovered=True,
                    quarantined=quarantined,
                    message="Повреждённый основной снимок восстановлен из резервной копии.",
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
