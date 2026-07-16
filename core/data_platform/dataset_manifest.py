"""Versioned, JSON-safe metadata contracts for registered datasets."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Mapping
from uuid import uuid4

MANIFEST_SCHEMA = "gas-ratio-pro.dataset-manifest"
MANIFEST_VERSION = 1


def _required_identifier(name: str, value: object) -> str:
    text = str(value).strip()
    if not text or text in {".", ".."} or any(ch in text for ch in ("/", "\\", "\x00")):
        raise ValueError(f"{name} must be a non-empty path-safe identifier")
    return text


@dataclass(frozen=True, slots=True)
class DatasetProvenance:
    operation: str
    actor: str = ""
    source_dataset_ids: tuple[str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    application_version: str = ""

    def __post_init__(self) -> None:
        if not self.operation.strip():
            raise ValueError("provenance operation must not be empty")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["source_dataset_ids"] = list(self.source_dataset_ids)
        return payload


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    project_id: str
    format_id: str
    artifact_path: str
    checksum_sha256: str
    size_bytes: int
    version: int = 1
    well_id: str = ""
    source_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    coordinate_reference_system: str = ""
    unit_system: str = ""
    metadata: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)
    provenance: DatasetProvenance = field(default_factory=lambda: DatasetProvenance(operation="import"))
    schema: str = MANIFEST_SCHEMA
    schema_version: int = MANIFEST_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_id", _required_identifier("dataset_id", self.dataset_id))
        object.__setattr__(self, "project_id", _required_identifier("project_id", self.project_id))
        object.__setattr__(self, "format_id", _required_identifier("format_id", self.format_id).lower())
        if self.well_id:
            object.__setattr__(self, "well_id", _required_identifier("well_id", self.well_id))
        artifact = PurePosixPath(str(self.artifact_path))
        if artifact.is_absolute() or ".." in artifact.parts or not artifact.parts:
            raise ValueError("artifact_path must be a relative normalized path")
        checksum = self.checksum_sha256.strip().lower()
        if len(checksum) != 64 or any(ch not in "0123456789abcdef" for ch in checksum):
            raise ValueError("checksum_sha256 must be a 64-character hexadecimal digest")
        object.__setattr__(self, "checksum_sha256", checksum)
        if self.size_bytes < 0:
            raise ValueError("size_bytes must not be negative")
        if self.version < 1:
            raise ValueError("version must be at least 1")
        if self.schema != MANIFEST_SCHEMA or self.schema_version != MANIFEST_VERSION:
            raise ValueError("unsupported dataset manifest schema")
        object.__setattr__(self, "metadata", dict(self.metadata))

    @classmethod
    def create(cls, *, project_id: str, format_id: str, artifact_path: str, checksum_sha256: str, size_bytes: int, **kwargs: object) -> "DatasetManifest":
        return cls(
            dataset_id=f"ds-{uuid4().hex}",
            project_id=project_id,
            format_id=format_id,
            artifact_path=artifact_path,
            checksum_sha256=checksum_sha256,
            size_bytes=size_bytes,
            **kwargs,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "project_id": self.project_id,
            "well_id": self.well_id,
            "format_id": self.format_id,
            "artifact_path": self.artifact_path,
            "checksum_sha256": self.checksum_sha256,
            "size_bytes": self.size_bytes,
            "version": self.version,
            "source_name": self.source_name,
            "created_at": self.created_at,
            "coordinate_reference_system": self.coordinate_reference_system,
            "unit_system": self.unit_system,
            "metadata": dict(self.metadata),
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "DatasetManifest":
        provenance_payload = payload.get("provenance")
        if not isinstance(provenance_payload, Mapping):
            raise ValueError("manifest provenance must be an object")
        provenance = DatasetProvenance(
            operation=str(provenance_payload.get("operation", "")),
            actor=str(provenance_payload.get("actor", "")),
            source_dataset_ids=tuple(str(item) for item in provenance_payload.get("source_dataset_ids", ()) if str(item).strip()),
            created_at=str(provenance_payload.get("created_at", "")),
            application_version=str(provenance_payload.get("application_version", "")),
        )
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("manifest metadata must be an object")
        return cls(
            schema=str(payload.get("schema", "")),
            schema_version=int(payload.get("schema_version", 0)),
            dataset_id=str(payload.get("dataset_id", "")),
            project_id=str(payload.get("project_id", "")),
            well_id=str(payload.get("well_id", "")),
            format_id=str(payload.get("format_id", "")),
            artifact_path=str(payload.get("artifact_path", "")),
            checksum_sha256=str(payload.get("checksum_sha256", "")),
            size_bytes=int(payload.get("size_bytes", -1)),
            version=int(payload.get("version", 0)),
            source_name=str(payload.get("source_name", "")),
            created_at=str(payload.get("created_at", "")),
            coordinate_reference_system=str(payload.get("coordinate_reference_system", "")),
            unit_system=str(payload.get("unit_system", "")),
            metadata=dict(metadata),
            provenance=provenance,
        )
