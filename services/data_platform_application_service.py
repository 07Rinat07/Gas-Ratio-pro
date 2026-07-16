"""Application boundary for lightweight dataset registration."""
from __future__ import annotations

from pathlib import Path

from core.build_info import BUILD_VERSION
from core.data_platform import (
    ArtifactStore,
    DatasetManifest,
    DatasetManifestRepository,
    DatasetProvenance,
    DataFormatRegistry,
    default_format_registry,
)


class DataPlatformApplicationService:
    def __init__(self, projects_root: Path | str, *, formats: DataFormatRegistry | None = None) -> None:
        self.projects_root = Path(projects_root)
        self.formats = formats or default_format_registry()
        self.artifacts = ArtifactStore(self.projects_root)
        self.manifests = DatasetManifestRepository(self.projects_root)

    def register_source_file(self, *, project_id: str, source: Path | str, format_id: str | None = None, well_id: str = "", actor: str = "", metadata: dict[str, str | int | float | bool | None] | None = None) -> DatasetManifest:
        source_path = Path(source)
        capability = self.formats.require(format_id) if format_id else self.formats.detect(source_path)
        if capability is None:
            raise ValueError(f"unable to detect a registered format for {source_path.name}")
        if not capability.supports_import:
            raise ValueError(f"format does not support import: {capability.format_id}")
        location = self.artifacts.store_file(project_id=project_id, source=source_path, kind="source")
        manifest = DatasetManifest.create(
            project_id=project_id,
            well_id=well_id,
            format_id=capability.format_id,
            artifact_path=location.relative_path,
            checksum_sha256=location.checksum_sha256,
            size_bytes=location.size_bytes,
            source_name=source_path.name,
            metadata=metadata or {},
            provenance=DatasetProvenance(operation="import", actor=actor, application_version=BUILD_VERSION),
        )
        self.manifests.save(manifest)
        return manifest

    def snapshot(self, project_id: str) -> dict[str, object]:
        return {
            "status": "ok",
            "formats": self.formats.snapshot(),
            "datasets": self.manifests.snapshot(project_id),
        }
