"""Atomic file persistence for visualization interaction checkpoints."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from services.visualization_interaction_checkpoint import (
    VisualizationInteractionCheckpointStore,
)


@dataclass(frozen=True, slots=True)
class CheckpointFileMetadata:
    """Stable metadata returned after saving or loading a checkpoint file."""

    path: str
    size_bytes: int
    checksum_sha256: str
    checkpoint_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.checkpoint-file-metadata",
            "version": "1.0",
            "path": self.path,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "checkpoint_count": self.checkpoint_count,
            "renderer_neutral": True,
        }


class VisualizationInteractionCheckpointFileStore:
    """Persist checkpoint stores as deterministic UTF-8 JSON files.

    Writes are atomic: data is written and fsynced to a temporary file in the
    destination directory before ``os.replace`` publishes the new snapshot.
    """

    SCHEMA = "visualization.interactive.checkpoint-file"
    VERSION = "1.0"

    def save(
        self,
        path: str | os.PathLike[str],
        store: VisualizationInteractionCheckpointStore,
    ) -> CheckpointFileMetadata:
        destination = self._resolve_path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        store_payload = store.to_dict()
        canonical_store = self._canonical_bytes(store_payload)
        envelope = {
            "schema": self.SCHEMA,
            "version": self.VERSION,
            "store": store_payload,
            "store_checksum_sha256": sha256(canonical_store).hexdigest(),
        }
        content = self._canonical_bytes(envelope)

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

        return self._metadata(destination, content, store)

    def load(
        self,
        path: str | os.PathLike[str],
    ) -> tuple[VisualizationInteractionCheckpointStore, CheckpointFileMetadata]:
        source = self._resolve_path(path)
        try:
            content = source.read_bytes()
        except FileNotFoundError as exc:
            raise ValueError(f"interaction checkpoint file does not exist: {source}") from exc
        except OSError as exc:
            raise ValueError(f"cannot read interaction checkpoint file: {source}") from exc

        try:
            payload = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("interaction checkpoint file is not valid UTF-8 JSON") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("interaction checkpoint file root must be an object")
        if payload.get("schema") != self.SCHEMA:
            raise ValueError("unsupported interaction checkpoint file schema")
        if str(payload.get("version") or "") != self.VERSION:
            raise ValueError("unsupported interaction checkpoint file version")

        raw_store = payload.get("store")
        if not isinstance(raw_store, Mapping):
            raise ValueError("interaction checkpoint file requires store payload")

        expected_checksum = str(payload.get("store_checksum_sha256") or "")
        actual_checksum = sha256(self._canonical_bytes(raw_store)).hexdigest()
        if not expected_checksum or expected_checksum != actual_checksum:
            raise ValueError("interaction checkpoint file checksum mismatch")

        store = VisualizationInteractionCheckpointStore.from_dict(raw_store)
        return store, self._metadata(source, content, store)

    @staticmethod
    def _resolve_path(path: str | os.PathLike[str]) -> Path:
        resolved = Path(path).expanduser()
        if not str(resolved).strip():
            raise ValueError("interaction checkpoint file path is required")
        if resolved.exists() and resolved.is_dir():
            raise ValueError("interaction checkpoint file path points to a directory")
        return resolved

    @staticmethod
    def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def _metadata(
        path: Path,
        content: bytes,
        store: VisualizationInteractionCheckpointStore,
    ) -> CheckpointFileMetadata:
        return CheckpointFileMetadata(
            path=str(path),
            size_bytes=len(content),
            checksum_sha256=sha256(content).hexdigest(),
            checkpoint_count=len(store.checkpoints),
        )
