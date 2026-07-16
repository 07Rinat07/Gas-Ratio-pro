"""Application boundary for lightweight dataset registration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.build_info import BUILD_VERSION
from core.data_platform import (
    ArtifactStore,
    DatasetManifest,
    DatasetManifestRepository,
    DatasetMetadataCatalog,
    DatasetProvenance,
    DataFormatRegistry,
    LasHeaderMetadataScanner,
    LasValidationFinding,
    MetadataScanResult,
    MetadataScanner,
    default_format_registry,
    sha256_file,
    validate_las_metadata,
)


@dataclass(frozen=True, slots=True)
class DatasetRegistrationResult:
    manifest: DatasetManifest
    duplicate_dataset_ids: tuple[str, ...] = ()
    metadata_scan: MetadataScanResult | None = None
    validation_findings: tuple[LasValidationFinding, ...] = ()

    @property
    def is_duplicate(self) -> bool:
        return bool(self.duplicate_dataset_ids)

    def localized_messages(self, translate) -> tuple[str, ...]:
        """Build user-facing messages without changing stable machine codes."""
        source_name = self.manifest.source_name or self.manifest.dataset_id
        metadata = dict(self.manifest.metadata)
        messages: list[str] = []
        if bool(metadata.get("legacy_las", False)):
            messages.append(translate("import.dataset.legacy_las", source_name=source_name))
        elif self.is_duplicate:
            messages.append(translate("import.dataset.duplicate", source_name=source_name, count=len(self.duplicate_dataset_ids)))
        else:
            messages.append(translate("import.dataset.success", source_name=source_name))
        blocking = sum(1 for item in self.validation_findings if item.blocking)
        warnings = sum(1 for item in self.validation_findings if not item.blocking)
        if blocking:
            messages.append(translate("import.dataset.validation_blocked"))
        elif warnings:
            messages.append(translate("import.dataset.validation_warning", count=warnings))
        for finding in self.validation_findings:
            key = f"import.validation.{finding.code}"
            translated = translate(key)
            if translated != key:
                messages.append(translated)
        return tuple(messages)

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.manifest.dataset_id,
            "version": self.manifest.version,
            "lineage_id": self.manifest.lineage_id,
            "duplicate_dataset_ids": list(self.duplicate_dataset_ids),
            "is_duplicate": self.is_duplicate,
            "metadata_scan": self.metadata_scan.to_dict() if self.metadata_scan else None,
            "validation_findings": [item.to_dict() for item in self.validation_findings],
            "validation_codes": [item.code for item in self.validation_findings],
            "import_allowed": not any(item.blocking for item in self.validation_findings),
        }


class LasImportValidationError(ValueError):
    """Raised before persistence when strict LAS validation blocks import."""

    def __init__(self, findings: tuple[LasValidationFinding, ...]) -> None:
        self.findings = tuple(findings)
        codes = ", ".join(item.code for item in self.findings if item.blocking)
        super().__init__(f"strict LAS validation blocked import: {codes}")


class DataPlatformApplicationService:
    def __init__(self, projects_root: Path | str, *, formats: DataFormatRegistry | None = None, scanners: tuple[MetadataScanner, ...] | None = None) -> None:
        self.projects_root = Path(projects_root)
        self.formats = formats or default_format_registry()
        self.artifacts = ArtifactStore(self.projects_root)
        self.manifests = DatasetManifestRepository(self.projects_root)
        self.catalog = DatasetMetadataCatalog(self.projects_root)
        scanner_items = scanners if scanners is not None else (LasHeaderMetadataScanner(),)
        self._scanners = {item.format_id: item for item in scanner_items}

    def register_source_file(self, *, project_id: str, source: Path | str, format_id: str | None = None, well_id: str = "", actor: str = "", metadata: dict[str, str | int | float | bool | None] | None = None, previous_dataset_id: str = "", import_mode: str = "tolerant") -> DatasetManifest:
        return self.register_source_file_result(
            project_id=project_id,
            source=source,
            format_id=format_id,
            well_id=well_id,
            actor=actor,
            metadata=metadata,
            previous_dataset_id=previous_dataset_id,
            import_mode=import_mode,
        ).manifest

    def register_source_file_result(self, *, project_id: str, source: Path | str, format_id: str | None = None, well_id: str = "", actor: str = "", metadata: dict[str, str | int | float | bool | None] | None = None, previous_dataset_id: str = "", import_mode: str = "tolerant") -> DatasetRegistrationResult:
        source_path = Path(source)
        capability = self.formats.require(format_id) if format_id else self.formats.detect(source_path)
        if capability is None:
            raise ValueError(f"unable to detect a registered format for {source_path.name}")
        if not capability.supports_import:
            raise ValueError(f"format does not support import: {capability.format_id}")

        checksum = sha256_file(source_path)
        duplicates = self.manifests.find_by_checksum(project_id, checksum)
        scan = self.scan_metadata(source_path, capability.format_id) if capability.supports_metadata_scan else None
        normalized_import_mode = str(import_mode or "tolerant").strip().lower()
        if normalized_import_mode not in {"tolerant", "strict"}:
            raise ValueError("import_mode must be tolerant or strict")
        validation_findings = validate_las_metadata(scan, mode=normalized_import_mode) if capability.format_id == "las" else ()
        merged_metadata = dict(scan.metadata) if scan else {}
        merged_metadata["import_mode"] = normalized_import_mode
        if validation_findings:
            merged_metadata["validation_codes"] = ",".join(item.code for item in validation_findings)
        merged_metadata.update(metadata or {})
        if normalized_import_mode == "strict" and any(item.blocking for item in validation_findings):
            raise LasImportValidationError(tuple(validation_findings))

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
        self.catalog.project(manifest)
        return DatasetRegistrationResult(
            manifest=manifest,
            duplicate_dataset_ids=tuple(item.dataset_id for item in duplicates),
            metadata_scan=scan,
            validation_findings=tuple(validation_findings),
        )

    def scan_metadata(self, source: Path | str, format_id: str | None = None) -> MetadataScanResult | None:
        source_path = Path(source)
        capability = self.formats.require(format_id) if format_id else self.formats.detect(source_path)
        if capability is None or not capability.supports_metadata_scan:
            return None
        scanner = self._scanners.get(capability.format_id)
        return scanner.scan(source_path) if scanner else None


    def list_dataset_lineage(self, project_id: str, lineage_id: str) -> tuple[dict[str, object], ...]:
        """Return a lightweight, chronological lineage projection for UI use."""
        return tuple(
            {
                "dataset_id": item.dataset_id,
                "lineage_id": item.lineage_id,
                "version": item.version,
                "previous_dataset_id": item.previous_dataset_id,
                "format_id": item.format_id,
                "source_name": item.source_name,
                "created_at": item.created_at,
                "size_bytes": item.size_bytes,
                "well_id": item.well_id,
                "compatibility_mode": str(item.metadata.get("las_compatibility_mode", "")),
                "import_mode": str(item.metadata.get("import_mode", "tolerant")),
            }
            for item in self.manifests.list_lineage(project_id, lineage_id)
        )

    def list_project_lineages(self, project_id: str) -> tuple[dict[str, object], ...]:
        """Return one lightweight record per dataset lineage for Project Explorer."""
        grouped: dict[str, list[DatasetManifest]] = {}
        for manifest in self.manifests.list(project_id):
            grouped.setdefault(manifest.lineage_id, []).append(manifest)
        rows: list[dict[str, object]] = []
        for lineage_id, items in grouped.items():
            versions = sorted(items, key=lambda item: item.version)
            latest = versions[-1]
            rows.append({
                "lineage_id": lineage_id,
                "format_id": latest.format_id,
                "source_name": latest.source_name,
                "well_id": latest.well_id,
                "version_count": len(versions),
                "latest_version": latest.version,
                "latest_dataset_id": latest.dataset_id,
                "created_at": latest.created_at,
                "compatibility_mode": str(latest.metadata.get("las_compatibility_mode", "")),
            })
        return tuple(sorted(rows, key=lambda row: (str(row["source_name"]).casefold(), str(row["lineage_id"]))))

    def reconcile_catalog(self, project_id: str) -> dict[str, object]:
        return self.catalog.reconcile(project_id, self.manifests.list(project_id))

    def snapshot(self, project_id: str) -> dict[str, object]:
        return {
            "status": "ok",
            "formats": self.formats.snapshot(),
            "datasets": self.manifests.snapshot(project_id),
            "metadata_scanners": sorted(self._scanners),
            "metadata_catalog": self.catalog.snapshot(project_id),
        }
