"""Versioned atomic file persistence for visualization interaction checkpoints."""

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
    format_version: str
    migrated_from_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.checkpoint-file-metadata",
            "version": "1.1",
            "path": self.path,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "checkpoint_count": self.checkpoint_count,
            "format_version": self.format_version,
            "migrated_from_version": self.migrated_from_version,
            "renderer_neutral": True,
        }


class VisualizationInteractionCheckpointFileStore:
    """Persist versioned checkpoint stores as deterministic UTF-8 JSON files.

    Version 2 adds explicit content metadata while retaining automatic loading
    of version 1 files. Writes remain atomic and checksummed.
    """

    SCHEMA = "visualization.interactive.checkpoint-file"
    VERSION = "2.0"
    LEGACY_VERSIONS = frozenset({"1.0"})

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
            "content_type": "visualization-interaction-checkpoints",
            "content_version": str(store_payload.get("version") or "1.0"),
            "store": store_payload,
            "store_checksum_sha256": sha256(canonical_store).hexdigest(),
        }
        content = self._canonical_bytes(envelope)
        self._atomic_write(destination, content)
        return self._metadata(destination, content, store, format_version=self.VERSION)

    def load(
        self,
        path: str | os.PathLike[str],
    ) -> tuple[VisualizationInteractionCheckpointStore, CheckpointFileMetadata]:
        source = self._resolve_path(path)
        content = self._read(source)
        payload = self._decode(content)

        if payload.get("schema") != self.SCHEMA:
            raise ValueError("unsupported interaction checkpoint file schema")

        source_version = str(payload.get("version") or "")
        migrated_from = ""
        if source_version == self.VERSION:
            normalized = payload
        elif source_version in self.LEGACY_VERSIONS:
            normalized = self._migrate_legacy(payload, source_version)
            migrated_from = source_version
        else:
            raise ValueError("unsupported interaction checkpoint file version")

        raw_store = normalized.get("store")
        if not isinstance(raw_store, Mapping):
            raise ValueError("interaction checkpoint file requires store payload")

        expected_checksum = str(normalized.get("store_checksum_sha256") or "")
        actual_checksum = sha256(self._canonical_bytes(raw_store)).hexdigest()
        if not expected_checksum or expected_checksum != actual_checksum:
            raise ValueError("interaction checkpoint file checksum mismatch")

        store = VisualizationInteractionCheckpointStore.from_dict(raw_store)
        return store, self._metadata(
            source,
            content,
            store,
            format_version=self.VERSION,
            migrated_from_version=migrated_from,
        )

    def migrate_file(
        self,
        source_path: str | os.PathLike[str],
        destination_path: str | os.PathLike[str] | None = None,
    ) -> CheckpointFileMetadata:
        """Load any supported version and write the current format atomically."""

        store, _ = self.load(source_path)
        destination = source_path if destination_path is None else destination_path
        return self.save(destination, store)

    @staticmethod
    def _migrate_legacy(payload: Mapping[str, Any], source_version: str) -> dict[str, Any]:
        if source_version != "1.0":
            raise ValueError("unsupported interaction checkpoint file migration")
        raw_store = payload.get("store")
        if not isinstance(raw_store, Mapping):
            raise ValueError("interaction checkpoint file requires store payload")
        return {
            "schema": VisualizationInteractionCheckpointFileStore.SCHEMA,
            "version": VisualizationInteractionCheckpointFileStore.VERSION,
            "content_type": "visualization-interaction-checkpoints",
            "content_version": str(raw_store.get("version") or "1.0"),
            "store": raw_store,
            "store_checksum_sha256": str(payload.get("store_checksum_sha256") or ""),
        }

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
    def _read(source: Path) -> bytes:
        try:
            return source.read_bytes()
        except FileNotFoundError as exc:
            raise ValueError(f"interaction checkpoint file does not exist: {source}") from exc
        except OSError as exc:
            raise ValueError(f"cannot read interaction checkpoint file: {source}") from exc

    @staticmethod
    def _decode(content: bytes) -> Mapping[str, Any]:
        try:
            payload = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("interaction checkpoint file is not valid UTF-8 JSON") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("interaction checkpoint file root must be an object")
        return payload

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
        *,
        format_version: str,
        migrated_from_version: str = "",
    ) -> CheckpointFileMetadata:
        return CheckpointFileMetadata(
            path=str(path),
            size_bytes=len(content),
            checksum_sha256=sha256(content).hexdigest(),
            checkpoint_count=len(store.checkpoints),
            format_version=format_version,
            migrated_from_version=migrated_from_version,
        )
