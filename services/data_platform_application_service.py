"""Application boundary for lightweight dataset registration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.build_info import BUILD_VERSION
from core.data_platform import (
    ArtifactStore,
    DatasetManifest,
    DatasetManifestRepository,
    DatasetProvenance,
    DataFormatRegistry,
    LasHeaderMetadataScanner,
    MetadataScanResult,
    MetadataScanner,
    default_format_registry,
    sha256_file,
)


@dataclass(frozen=True, slots=True)
class DatasetRegistrationResult:
    manifest: DatasetManifest
    duplicate_dataset_ids: tuple[str, ...] = ()
    metadata_scan: MetadataScanResult | None = None

    @property
    def is_duplicate(self) -> bool:
        return bool(self.duplicate_dataset_ids)

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.manifest.dataset_id,
            "version": self.manifest.version,
            "lineage_id": self.manifest.lineage_id,
            "duplicate_dataset_ids": list(self.duplicate_dataset_ids),
            "is_duplicate": self.is_duplicate,
            "metadata_scan": self.metadata_scan.to_dict() if self.metadata_scan else None,
        }


class DataPlatformApplicationService:
    def __init__(self, projects_root: Path | str, *, formats: DataFormatRegistry | None = None, scanners: tuple[MetadataScanner, ...] | None = None) -> None:
        self.projects_root = Path(projects_root)
        self.formats = formats or default_format_registry()
        self.artifacts = ArtifactStore(self.projects_root)
        self.manifests = DatasetManifestRepository(self.projects_root)
        scanner_items = scanners if scanners is not None else (LasHeaderMetadataScanner(),)
        self._scanners = {item.format_id: item for item in scanner_items}

    def register_source_file(self, *, project_id: str, source: Path | str, format_id: str | None = None, well_id: str = "", actor: str = "", metadata: dict[str, str | int | float | bool | None] | None = None, previous_dataset_id: str = "") -> DatasetManifest:
        return self.register_source_file_result(
            project_id=project_id,
            source=source,
            format_id=format_id,
            well_id=well_id,
            actor=actor,
            metadata=metadata,
            previous_dataset_id=previous_dataset_id,
        ).manifest

    def register_source_file_result(self, *, project_id: str, source: Path | str, format_id: str | None = None, well_id: str = "", actor: str = "", metadata: dict[str, str | int | float | bool | None] | None = None, previous_dataset_id: str = "") -> DatasetRegistrationResult:
        source_path = Path(source)
        capability = self.formats.require(format_id) if format_id else self.formats.detect(source_path)
        if capability is None:
            raise ValueError(f"unable to detect a registered format for {source_path.name}")
        if not capability.supports_import:
            raise ValueError(f"format does not support import: {capability.format_id}")

        checksum = sha256_file(source_path)
        duplicates = self.manifests.find_by_checksum(project_id, checksum)
        scan = self.scan_metadata(source_path, capability.format_id) if capability.supports_metadata_scan else None
        merged_metadata = dict(scan.metadata) if scan else {}
        merged_metadata.update(metadata or {})

        lineage_id = ""
        version = 1
        previous_id = ""
        source_dataset_ids: tuple[str, ...] = ()
        if previous_dataset_id:
            previous = self.manifests.load(project_id, previous_dataset_id)
            if previous.format_id != capability.format_id:
                raise ValueError("dataset version format must match the previous version")
            lineage_id = previous.lineage_id
            version = previous.version + 1
            previous_id = previous.dataset_id
            source_dataset_ids = (previous.dataset_id,)

        location = self.artifacts.store_file(project_id=project_id, source=source_path, kind="source")
        manifest = DatasetManifest.create(
            project_id=project_id,
            well_id=well_id,
            format_id=capability.format_id,
            artifact_path=location.relative_path,
            checksum_sha256=location.checksum_sha256,
            size_bytes=location.size_bytes,
            source_name=source_path.name,
            version=version,
            lineage_id=lineage_id,
            previous_dataset_id=previous_id,
            metadata=merged_metadata,
            provenance=DatasetProvenance(operation="import" if version == 1 else "version-import", actor=actor, source_dataset_ids=source_dataset_ids, application_version=BUILD_VERSION),
        )
        self.manifests.save(manifest)
        return DatasetRegistrationResult(
            manifest=manifest,
            duplicate_dataset_ids=tuple(item.dataset_id for item in duplicates),
            metadata_scan=scan,
        )

    def scan_metadata(self, source: Path | str, format_id: str | None = None) -> MetadataScanResult | None:
        source_path = Path(source)
        capability = self.formats.require(format_id) if format_id else self.formats.detect(source_path)
        if capability is None or not capability.supports_metadata_scan:
            return None
        scanner = self._scanners.get(capability.format_id)
        return scanner.scan(source_path) if scanner else None

    def snapshot(self, project_id: str) -> dict[str, object]:
        return {
            "status": "ok",
            "formats": self.formats.snapshot(),
            "datasets": self.manifests.snapshot(project_id),
            "metadata_scanners": sorted(self._scanners),
        }
