"""Backup and restore checkpoint repositories with integrity validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from services.visualization_interaction_checkpoint_repository import (
    VisualizationInteractionCheckpointRepository,
)


@dataclass(frozen=True, slots=True)
class CheckpointBackupMetadata:
    """Stable metadata for one repository backup archive."""

    path: str
    file_count: int
    size_bytes: int
    checksum_sha256: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.checkpoint-backup-metadata",
            "version": "1.0",
            "path": self.path,
            "file_count": self.file_count,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "created_at": self.created_at,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class CheckpointRestoreMetadata:
    """Result of restoring one backup archive into a repository."""

    source_path: str
    destination_directory: str
    restored_files: tuple[str, ...]
    skipped_files: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.checkpoint-backup-restore",
            "version": "1.0",
            "source_path": self.source_path,
            "destination_directory": self.destination_directory,
            "restored_files": list(self.restored_files),
            "skipped_files": list(self.skipped_files),
            "restored_count": len(self.restored_files),
            "skipped_count": len(self.skipped_files),
            "renderer_neutral": True,
        }


class VisualizationInteractionCheckpointBackupService:
    """Create and restore validated ZIP backups of compatible checkpoint files."""

    SCHEMA = "visualization.interactive.checkpoint-backup"
    VERSION = "1.0"
    MANIFEST_NAME = "manifest.json"

    def create_backup(
        self,
        repository: VisualizationInteractionCheckpointRepository,
        destination: str | os.PathLike[str],
    ) -> CheckpointBackupMetadata:
        target = Path(destination).expanduser()
        if target.exists() and target.is_dir():
            raise ValueError("checkpoint backup path points to a directory")
        target.parent.mkdir(parents=True, exist_ok=True)

        entries = repository.list_entries()
        files: list[dict[str, Any]] = []
        payloads: list[tuple[str, bytes]] = []
        for entry in sorted(entries, key=lambda item: item.name):
            content = Path(entry.path).read_bytes()
            payloads.append((entry.name, content))
            files.append(
                {
                    "name": entry.name,
                    "size_bytes": len(content),
                    "checksum_sha256": sha256(content).hexdigest(),
                    "format_version": entry.format_version,
                }
            )

        created_at = datetime.now(timezone.utc).isoformat()
        manifest = {
            "schema": self.SCHEMA,
            "version": self.VERSION,
            "created_at": created_at,
            "file_count": len(files),
            "files": files,
        }
        manifest_bytes = self._canonical_bytes(manifest)

        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False
            ) as temporary:
                temporary_name = temporary.name
            with ZipFile(temporary_name, "w", compression=ZIP_DEFLATED) as archive:
                archive.writestr(self.MANIFEST_NAME, manifest_bytes)
                for name, content in payloads:
                    archive.writestr(f"checkpoints/{name}", content)
            os.replace(temporary_name, target)
            temporary_name = None
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

        archive_bytes = target.read_bytes()
        return CheckpointBackupMetadata(
            path=str(target),
            file_count=len(files),
            size_bytes=len(archive_bytes),
            checksum_sha256=sha256(archive_bytes).hexdigest(),
            created_at=created_at,
        )

    def restore_backup(
        self,
        source: str | os.PathLike[str],
        repository: VisualizationInteractionCheckpointRepository,
        *,
        overwrite: bool = False,
    ) -> CheckpointRestoreMetadata:
        archive_path = Path(source).expanduser()
        if not archive_path.is_file():
            raise ValueError("checkpoint backup file does not exist")

        try:
            with ZipFile(archive_path, "r") as archive:
                manifest = self._load_manifest(archive)
                restored: list[str] = []
                skipped: list[str] = []
                repository.directory.mkdir(parents=True, exist_ok=True)

                for item in manifest["files"]:
                    name = str(item["name"])
                    self._validate_checkpoint_name(name)
                    member = f"checkpoints/{name}"
                    try:
                        content = archive.read(member)
                    except KeyError as exc:
                        raise ValueError(f"checkpoint backup is missing file: {name}") from exc
                    if len(content) != int(item["size_bytes"]):
                        raise ValueError(f"checkpoint backup size mismatch: {name}")
                    if sha256(content).hexdigest() != str(item["checksum_sha256"]):
                        raise ValueError(f"checkpoint backup checksum mismatch: {name}")

                    destination = repository.directory / name
                    if destination.exists() and not overwrite:
                        skipped.append(str(destination))
                        continue
                    self._atomic_write(destination, content)
                    # Validate restored content using the repository file-store contract.
                    repository._file_store.load(destination)
                    restored.append(str(destination))
        except BadZipFile as exc:
            raise ValueError("checkpoint backup is not a valid ZIP archive") from exc

        return CheckpointRestoreMetadata(
            source_path=str(archive_path),
            destination_directory=str(repository.directory),
            restored_files=tuple(restored),
            skipped_files=tuple(skipped),
        )

    def _load_manifest(self, archive: ZipFile) -> Mapping[str, Any]:
        try:
            raw = archive.read(self.MANIFEST_NAME)
        except KeyError as exc:
            raise ValueError("checkpoint backup manifest is missing") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("checkpoint backup manifest is invalid") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("checkpoint backup manifest root must be an object")
        if payload.get("schema") != self.SCHEMA or payload.get("version") != self.VERSION:
            raise ValueError("unsupported checkpoint backup format")
        files = payload.get("files")
        if not isinstance(files, list) or int(payload.get("file_count") or 0) != len(files):
            raise ValueError("checkpoint backup manifest file count mismatch")
        for item in files:
            if not isinstance(item, Mapping):
                raise ValueError("checkpoint backup manifest file entry is invalid")
        return payload

    @staticmethod
    def _validate_checkpoint_name(name: str) -> None:
        path = Path(name)
        if (
            not name
            or path.is_absolute()
            or len(path.parts) != 1
            or name in {".", ".."}
            or not name.endswith(VisualizationInteractionCheckpointRepository.SUFFIX)
        ):
            raise ValueError("checkpoint backup contains unsafe file name")

    @staticmethod
    def _atomic_write(destination: Path, content: bytes) -> None:
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
                delete=False,
            ) as temporary:
                temporary_name = temporary.name
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, destination)
            temporary_name = None
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

    @staticmethod
    def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
        return (
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
