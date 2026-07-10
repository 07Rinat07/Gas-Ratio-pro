"""Directory repository for versioned visualization interaction checkpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from services.visualization_interaction_checkpoint import (
    VisualizationInteractionCheckpointStore,
)
from services.visualization_interaction_checkpoint_file import (
    CheckpointFileMetadata,
    VisualizationInteractionCheckpointFileStore,
)


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True, slots=True)
class CheckpointRepositoryEntry:
    """One compatible checkpoint file discovered in a repository directory."""

    path: str
    name: str
    modified_at: str
    size_bytes: int
    checkpoint_count: int
    format_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.checkpoint-repository-entry",
            "version": "1.0",
            "path": self.path,
            "name": self.name,
            "modified_at": self.modified_at,
            "size_bytes": self.size_bytes,
            "checkpoint_count": self.checkpoint_count,
            "format_version": self.format_version,
            "renderer_neutral": True,
        }


class VisualizationInteractionCheckpointRepository:
    """Manage multiple checkpoint files in one directory.

    Invalid, corrupted or unsupported files are ignored during discovery so a
    single bad file cannot prevent restoration of the latest compatible state.
    """

    SUFFIX = ".interaction-checkpoints.json"

    def __init__(
        self,
        directory: str | Path,
        *,
        file_store: VisualizationInteractionCheckpointFileStore | None = None,
    ) -> None:
        self._directory = Path(directory).expanduser()
        if self._directory.exists() and not self._directory.is_dir():
            raise ValueError("checkpoint repository path must be a directory")
        self._file_store = file_store or VisualizationInteractionCheckpointFileStore()

    @property
    def directory(self) -> Path:
        return self._directory

    def save(
        self,
        store: VisualizationInteractionCheckpointStore,
        *,
        name: str = "checkpoint",
        timestamp: datetime | None = None,
    ) -> CheckpointFileMetadata:
        self._directory.mkdir(parents=True, exist_ok=True)
        moment = timestamp or datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        safe_name = _SAFE_NAME.sub("-", name.strip()).strip("-._") or "checkpoint"
        stamp = moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = self._directory / f"{stamp}-{safe_name}{self.SUFFIX}"
        return self._file_store.save(path, store)

    def list_entries(self) -> tuple[CheckpointRepositoryEntry, ...]:
        if not self._directory.exists():
            return ()
        entries: list[CheckpointRepositoryEntry] = []
        for path in sorted(self._directory.glob(f"*{self.SUFFIX}")):
            try:
                store, metadata = self._file_store.load(path)
                stat = path.stat()
            except (OSError, ValueError):
                continue
            entries.append(
                CheckpointRepositoryEntry(
                    path=str(path),
                    name=path.name,
                    modified_at=datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    size_bytes=metadata.size_bytes,
                    checkpoint_count=len(store.checkpoints),
                    format_version=metadata.format_version,
                )
            )
        entries.sort(key=lambda item: (Path(item.path).stat().st_mtime_ns, item.name), reverse=True)
        return tuple(entries)

    def load_latest(
        self,
    ) -> tuple[VisualizationInteractionCheckpointStore, CheckpointFileMetadata]:
        for entry in self.list_entries():
            try:
                return self._file_store.load(entry.path)
            except ValueError:
                continue
        raise ValueError("no compatible interaction checkpoint file available")

    def prune(self, *, keep: int) -> tuple[str, ...]:
        if int(keep) < 0:
            raise ValueError("checkpoint repository keep count cannot be negative")
        entries = self.list_entries()
        removed: list[str] = []
        for entry in entries[int(keep):]:
            path = Path(entry.path)
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            removed.append(str(path))
        return tuple(removed)
