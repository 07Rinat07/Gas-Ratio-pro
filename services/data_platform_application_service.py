"""Application boundary for lightweight dataset registration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from tempfile import NamedTemporaryFile

from core.build_info import BUILD_VERSION
from core.data_platform import (
    ArtifactStore,
    DatasetManifest,
    DatasetManifestRepository,
    DatasetMetadataCatalog,
    DatasetProvenance,
    DataFormatRegistry,
    DlisLisMetadataScanner,
    LasHeaderMetadataScanner,
    SegyHeaderMetadataScanner,
    SegyTraceHeaderInventoryAdapter,
    build_metadata_import_preview,
    LasValidationFinding,
    MetadataScanResult,
    MetadataScanner,
    default_format_registry,
    sha256_file,
    validate_las_metadata,
    FormatPlugin,
    FormatPluginRegistry,
    ImportPreviewCache,
    ImportProfile,
    ImportProfileRepository,
    compute_readiness_score,
    ImportWizardState,
    BatchImportItemResult,
    BatchImportResult,
    metadata_quick_qc,
    ImportJobManager,
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
        scanner_items = scanners if scanners is not None else (
            LasHeaderMetadataScanner(),
            DlisLisMetadataScanner("dlis"),
            DlisLisMetadataScanner("lis79"),
            SegyHeaderMetadataScanner(),
        )
        self._scanners = {item.format_id: item for item in scanner_items}
        self.plugins = FormatPluginRegistry(self.formats)
        for capability in self.formats.list():
            self.plugins.register(
                FormatPlugin(
                    capability=capability,
                    scanner=self._scanners.get(capability.format_id),
                    quick_qc=(metadata_quick_qc if capability.format_id in {"las", "dlis", "lis79", "segy"} else None),
                    importer_id=(f"{capability.format_id}-importer" if capability.supports_import else ""),
                    exporter_id=(f"{capability.format_id}-exporter" if capability.supports_export else ""),
                )
            )
        self.preview_cache = ImportPreviewCache(max_entries=32)
        self.import_profiles = ImportProfileRepository(self.projects_root)
        self.import_jobs = ImportJobManager(self.projects_root, self.run_batch_import)

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
        if scan is not None:
            plugin = self.plugins.get(capability.format_id)
            quick_qc = dict(plugin.quick_qc(scan)) if plugin and plugin.quick_qc else {"warning_count": 0, "error_count": 0}
            readiness = compute_readiness_score(
                preview_complete=scan.complete,
                warning_count=int(quick_qc.get("warning_count", 0) or 0),
                error_count=int(quick_qc.get("error_count", 0) or 0),
                metadata_field_count=len(scan.metadata),
                qc_available=bool(plugin and plugin.quick_qc),
            )
            merged_metadata.update({
                "readiness_score": int(readiness["score"]),
                "readiness_status": str(readiness["status"]),
                "quick_qc_status": str(quick_qc.get("status", "unavailable")),
                "quick_qc_warning_count": int(quick_qc.get("warning_count", 0) or 0),
                "quick_qc_error_count": int(quick_qc.get("error_count", 0) or 0),
            })
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

    def build_import_preview(self, source: Path | str, *, format_id: str | None = None, translate=lambda key, **kwargs: key, profile: ImportProfile | None = None) -> dict[str, object]:
        """Return a cached localized metadata-only preview before persistence."""
        source_path = Path(source)
        capability = self.formats.require(format_id) if format_id else self.formats.detect(source_path)
        if capability is None:
            raise ValueError("unable to detect format")
        selected_profile = profile or ImportProfile(
            profile_id=f"{capability.format_id}-default",
            name=f"{capability.display_name} Default",
            format_id=capability.format_id,
        )
        checksum = sha256_file(source_path)
        cache_key = self.preview_cache.key(checksum, selected_profile.profile_id, selected_profile.scanner_version)
        cached = self.preview_cache.get(cache_key)
        if cached is not None:
            cached["cache"] = {"hit": True, "key": cache_key}
            return cached
        result = self.scan_metadata(source_path, capability.format_id)
        if result is None:
            raise ValueError("format does not support metadata preview")
        preview = build_metadata_import_preview(result, translate)
        preview["profile"] = selected_profile.to_dict()
        plugin = self.plugins.require(capability.format_id)
        quick_qc = dict(plugin.quick_qc(result)) if plugin.quick_qc is not None else {"status": "unavailable", "warning_count": 0, "error_count": 0, "warning_codes": [], "error_codes": []}
        preview["quick_qc"] = quick_qc
        preview["readiness"] = compute_readiness_score(
            preview_complete=bool(preview.get("complete", False)),
            warning_count=int(quick_qc.get("warning_count", len(preview.get("warnings", []) or [])) or 0),
            error_count=int(quick_qc.get("error_count", 0) or 0),
            metadata_field_count=len(preview.get("fields", []) or []),
            qc_available=plugin.quick_qc is not None,
        )
        preview["cache"] = {"hit": False, "key": cache_key}
        self.preview_cache.put(cache_key, preview)
        return preview

    def new_import_wizard(self, project_id: str) -> ImportWizardState:
        return ImportWizardState(project_id=project_id)

    def run_batch_import(
        self, *, project_id: str, sources, actor: str = "", profile: ImportProfile | None = None,
        import_mode: str = "tolerant", should_cancel=None, progress_callback=None,
    ) -> BatchImportResult:
        source_items = tuple(sources)
        items = []
        total = len(source_items)
        for index, raw in enumerate(source_items):
            if should_cancel is not None and bool(should_cancel()):
                break
            source = Path(raw)
            try:
                format_id = profile.format_id if profile is not None else None
                result = self.register_source_file_result(project_id=project_id, source=source, format_id=format_id, actor=actor, import_mode=import_mode)
                items.append(BatchImportItemResult(source_name=source.name, status="success", dataset_id=result.manifest.dataset_id, format_id=result.manifest.format_id, readiness_score=int(result.manifest.metadata.get("readiness_score", 0) or 0)))
            except Exception as exc:
                items.append(BatchImportItemResult(source_name=source.name, status="failed", error_code=type(exc).__name__, message=str(exc)))
            if progress_callback is not None:
                progress_callback(index + 1, total)
        return BatchImportResult(tuple(items))


    def submit_batch_import_job(self, *, project_id: str, sources, actor: str = "") -> dict[str, object]:
        return self.import_jobs.submit(project_id=project_id, sources=sources, actor=actor).to_dict()

    def get_import_job(self, job_id: str) -> dict[str, object]:
        return self.import_jobs.get(job_id).to_dict()

    def list_import_jobs(self, *, project_id: str = "", statuses: set[str] | None = None) -> tuple[dict[str, object], ...]:
        return tuple(item.to_dict() for item in self.import_jobs.list(project_id=project_id, statuses=statuses))

    def cancel_import_job(self, job_id: str) -> dict[str, object]:
        return self.import_jobs.cancel(job_id).to_dict()

    def list_import_history(
        self, project_id: str, *, limit: int = 100, statuses: set[str] | None = None, query: str = ""
    ) -> tuple[dict[str, object], ...]:
        return self.import_jobs.history(project_id, limit=limit, statuses=statuses, query=query)

    def project_readiness_dashboard(self, project_id: str) -> dict[str, object]:
        """Return a manifest-only readiness aggregate for one project."""
        manifests = tuple(self.manifests.list(project_id))
        source_items = [
            item for item in manifests
            if item.provenance.operation not in {"quality-control", "quality-control-export"}
            and str(item.metadata.get("dataset_kind", "")) not in {"qc-report", "qc-report-export"}
        ]
        buckets = {"ready": 0, "review": 0, "blocked": 0, "unknown": 0}
        formats: dict[str, int] = {}
        scores: list[int] = []
        for item in source_items:
            status = str(item.metadata.get("readiness_status", "") or "unknown").lower()
            if status not in buckets:
                status = "unknown"
            buckets[status] += 1
            formats[item.format_id] = formats.get(item.format_id, 0) + 1
            raw_score = item.metadata.get("readiness_score")
            if raw_score not in (None, ""):
                try:
                    scores.append(max(0, min(100, int(raw_score))))
                except (TypeError, ValueError):
                    pass
        average = round(sum(scores) / len(scores), 1) if scores else 0.0
        return {
            "schema": "gas-ratio-pro/project-readiness-dashboard/v1",
            "project_id": project_id,
            "dataset_count": len(source_items),
            "average_score": average,
            "ready_count": buckets["ready"],
            "review_count": buckets["review"],
            "blocked_count": buckets["blocked"],
            "unknown_count": buckets["unknown"],
            "formats": dict(sorted(formats.items())),
        }

    def list_project_readiness_items(
        self,
        project_id: str,
        *,
        statuses: set[str] | None = None,
        formats: set[str] | None = None,
    ) -> tuple[dict[str, object], ...]:
        """Return manifest-only dataset rows filtered by readiness and format."""
        wanted_statuses = {str(value).strip().lower() for value in (statuses or set()) if str(value).strip()}
        wanted_formats = {str(value).strip().lower() for value in (formats or set()) if str(value).strip()}
        rows: list[dict[str, object]] = []
        for item in self.manifests.list(project_id):
            if item.provenance.operation in {"quality-control", "quality-control-export"}:
                continue
            if str(item.metadata.get("dataset_kind", "")) in {"qc-report", "qc-report-export"}:
                continue
            status = str(item.metadata.get("readiness_status", "") or "unknown").lower()
            format_id = str(item.format_id).lower()
            if wanted_statuses and status not in wanted_statuses:
                continue
            if wanted_formats and format_id not in wanted_formats:
                continue
            try:
                score = max(0, min(100, int(item.metadata.get("readiness_score", 0) or 0)))
            except (TypeError, ValueError):
                score = 0
            rows.append({
                "dataset_id": item.dataset_id,
                "lineage_id": item.lineage_id,
                "version": item.version,
                "source_name": item.source_name,
                "format_id": item.format_id,
                "well_id": item.well_id,
                "readiness_status": status,
                "readiness_score": score,
                "quick_qc_status": str(item.metadata.get("quick_qc_status", "")),
                "created_at": item.created_at,
            })
        return tuple(sorted(rows, key=lambda row: (str(row["source_name"]), int(row["version"]))))

    def project_correlation_readiness(self, project_id: str) -> dict[str, object]:
        """Estimate well-log correlation readiness using manifest metadata only."""
        wells: dict[str, list[DatasetManifest]] = {}
        for item in self.manifests.list(project_id):
            if item.format_id != "las" or not item.well_id:
                continue
            if item.provenance.operation in {"quality-control", "quality-control-export"}:
                continue
            wells.setdefault(item.well_id, []).append(item)
        well_rows: list[dict[str, object]] = []
        curve_sets: list[set[str]] = []
        ready_count = 0
        review_count = 0
        blocked_count = 0
        for well_id, versions in sorted(wells.items()):
            latest = max(versions, key=lambda item: item.version)
            raw_curves = latest.metadata.get("curve_mnemonics", "")
            if isinstance(raw_curves, str):
                curves = {value.strip().upper() for value in raw_curves.replace(";", ",").split(",") if value.strip()}
            elif isinstance(raw_curves, (list, tuple, set)):
                curves = {str(value).strip().upper() for value in raw_curves if str(value).strip()}
            else:
                curves = set()
            curve_sets.append(curves)
            try:
                base_score = max(0, min(100, int(latest.metadata.get("readiness_score", 0) or 0)))
            except (TypeError, ValueError):
                base_score = 0
            depth_available = all(latest.metadata.get(key) not in (None, "") for key in ("start_depth", "stop_depth"))
            curve_component = min(20, len(curves) * 4)
            score = min(100, round(base_score * 0.7 + curve_component + (10 if depth_available else 0)))
            status = "ready" if score >= 70 and len(curves) >= 2 else "review" if score >= 40 else "blocked"
            if status == "ready": ready_count += 1
            elif status == "review": review_count += 1
            else: blocked_count += 1
            well_rows.append({
                "well_id": well_id,
                "dataset_id": latest.dataset_id,
                "version": latest.version,
                "score": score,
                "status": status,
                "curve_count": len(curves),
                "curves": sorted(curves),
                "depth_available": depth_available,
            })
        shared = sorted(set.intersection(*curve_sets)) if curve_sets and all(curve_sets) else []
        eligible = ready_count >= 2 and bool(shared)
        return {
            "schema": "gas-ratio-pro/correlation-readiness/v1",
            "project_id": project_id,
            "well_count": len(well_rows),
            "ready_count": ready_count,
            "review_count": review_count,
            "blocked_count": blocked_count,
            "shared_curves": shared,
            "eligible_for_correlation": eligible,
            "wells": well_rows,
        }

    def export_import_history(
        self, project_id: str, *, format_id: str = "json", statuses: set[str] | None = None, query: str = ""
    ) -> bytes:
        return self.import_jobs.export_history(project_id, format_id=format_id, statuses=statuses, query=query)

    def cleanup_import_staging(self, project_id: str, *, include_terminal: bool = True) -> dict[str, int]:
        return self.import_jobs.cleanup_staging(project_id, include_terminal=include_terminal)

    def retry_failed_import_job(self, job_id: str, *, actor: str = "") -> dict[str, object]:
        return self.import_jobs.retry_failed(job_id, actor=actor).to_dict()

    def resume_interrupted_import_job(self, job_id: str, *, actor: str = "") -> dict[str, object]:
        return self.import_jobs.resume_interrupted(job_id, actor=actor).to_dict()

    def apply_import_retention_policy(
        self, project_id: str, *, retention_days: int = 90, keep_latest: int = 100, staging_max_age_days: int = 7
    ) -> dict[str, int]:
        return self.import_jobs.apply_retention_policy(
            project_id, retention_days=retention_days, keep_latest=keep_latest, staging_max_age_days=staging_max_age_days
        )

    def capability_matrix(self) -> dict[str, object]:
        return self.plugins.capability_matrix()

    def save_import_profile(self, project_id: str, profile: ImportProfile) -> dict[str, object]:
        self.formats.require(profile.format_id)
        path = self.import_profiles.save(project_id, profile)
        return {"project_id": project_id, "profile": profile.to_dict(), "path": str(path.relative_to(self.projects_root))}

    def list_import_profiles(self, project_id: str) -> tuple[dict[str, object], ...]:
        return tuple(item.to_dict() for item in self.import_profiles.list(project_id))

    def import_pipeline_snapshot(self) -> dict[str, object]:
        return {
            "capabilities": self.capability_matrix(),
            "preview_cache": self.preview_cache.snapshot(),
        }


    def build_dlis_selection_projection(self, source: Path | str, *, format_id: str | None = None) -> dict[str, object]:
        """Return bounded logical-file/frame/channel choices for DLIS/LIS79 UI."""
        result = self.scan_metadata(source, format_id)
        if result is None or result.format_id not in {"dlis", "lis79"}:
            raise ValueError("DLIS/LIS79 metadata is required")
        raw = str(result.metadata.get("logical_files_json", "") or "")
        logical_files = json.loads(raw) if raw else []
        if not isinstance(logical_files, list):
            logical_files = []
        return {
            "format_id": result.format_id,
            "adapter_available": bool(result.metadata.get("adapter_available", False)),
            "logical_files": logical_files,
            "warnings": list(result.warnings),
        }

    def persist_import_preview(
        self, *, project_id: str, source: Path | str, actor: str = "",
        format_id: str | None = None, translate=lambda key, **kwargs: key,
    ) -> DatasetManifest:
        """Persist one metadata-only preview as an immutable preview Dataset."""
        source_path = Path(source)
        capability = self.formats.require(format_id) if format_id else self.formats.detect(source_path)
        if capability is None:
            raise ValueError("unable to detect preview format")
        preview = self.build_import_preview(source_path, format_id=capability.format_id, translate=translate)
        payload = {
            "schema": "gas-ratio-pro/import-preview/v1",
            "source_name": source_path.name,
            "source_size_bytes": source_path.stat().st_size,
            "preview": preview,
        }
        with NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            temp_path = Path(handle.name)
        try:
            location = self.artifacts.store_file(
                project_id=project_id,
                source=temp_path,
                kind="preview",
                filename=f"{source_path.stem}-{capability.format_id}-preview.json",
            )
        finally:
            temp_path.unlink(missing_ok=True)
        manifest = DatasetManifest.create(
            project_id=project_id,
            format_id=capability.format_id,
            artifact_path=location.relative_path,
            checksum_sha256=location.checksum_sha256,
            size_bytes=location.size_bytes,
            source_name=source_path.name,
            metadata={
                "dataset_kind": "metadata-preview",
                "source_format_id": capability.format_id,
                "preview_complete": bool(preview.get("complete", False)),
                "warning_count": len(preview.get("warnings", []) or []),
            },
            provenance=DatasetProvenance(
                operation="metadata-preview",
                actor=actor,
                application_version=BUILD_VERSION,
            ),
        )
        self.manifests.save(manifest)
        self.catalog.project(manifest)
        return manifest

    def scan_segy_trace_headers(
        self, source: Path | str, *, inline_byte: int = 189, crossline_byte: int = 193,
        coordinate_scalar_byte: int = 71, x_byte: int = 73, y_byte: int = 77,
        max_traces: int = 100_000,
    ) -> MetadataScanResult:
        """Run bounded SEG-Y trace-header and coordinate diagnostics lazily."""
        return SegyTraceHeaderInventoryAdapter(
            inline_byte=inline_byte,
            crossline_byte=crossline_byte,
            coordinate_scalar_byte=coordinate_scalar_byte,
            x_byte=x_byte,
            y_byte=y_byte,
            max_traces=max_traces,
        ).scan(source)


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
                "checksum_sha256": item.checksum_sha256,
                "provenance_operation": item.provenance.operation,
                "provenance_actor": item.provenance.actor,
                "provenance_created_at": item.provenance.created_at,
                "application_version": item.provenance.application_version,
                "compatibility_mode": str(item.metadata.get("las_compatibility_mode", "")),
                "import_mode": str(item.metadata.get("import_mode", "tolerant")),
            }
            for item in self.manifests.list_lineage(project_id, lineage_id)
        )

    def _qc_summary_for_source(self, project_id: str, source_dataset_id: str) -> dict[str, object]:
        """Return the latest lightweight QC summary linked to one source Dataset."""
        candidates = [
            item for item in self.manifests.list(project_id)
            if item.provenance.operation == "quality-control"
            and source_dataset_id in item.provenance.source_dataset_ids
        ]
        if not candidates:
            return {"available": False, "status": "", "dataset_id": "", "finding_count": 0, "error_count": 0, "warning_count": 0}
        latest = max(candidates, key=lambda item: (item.created_at, item.dataset_id))
        return {
            "available": True,
            "status": str(latest.metadata.get("qc_status", "")),
            "dataset_id": latest.dataset_id,
            "finding_count": int(latest.metadata.get("finding_count", 0) or 0),
            "error_count": int(latest.metadata.get("error_count", 0) or 0),
            "warning_count": int(latest.metadata.get("warning_count", 0) or 0),
        }

    def compare_dataset_versions(self, project_id: str, left_dataset_id: str, right_dataset_id: str) -> dict[str, object]:
        """Compare two immutable versions from the same lineage using metadata only."""
        left = self.manifests.load(project_id, left_dataset_id)
        right = self.manifests.load(project_id, right_dataset_id)
        if left.lineage_id != right.lineage_id:
            raise ValueError("dataset versions must belong to the same lineage")
        keys = sorted(set(left.metadata) | set(right.metadata))
        metadata_changes = {
            key: {"left": left.metadata.get(key), "right": right.metadata.get(key)}
            for key in keys
            if left.metadata.get(key) != right.metadata.get(key)
        }
        return {
            "project_id": project_id,
            "lineage_id": left.lineage_id,
            "left_dataset_id": left.dataset_id,
            "right_dataset_id": right.dataset_id,
            "left_version": left.version,
            "right_version": right.version,
            "checksum_changed": left.checksum_sha256 != right.checksum_sha256,
            "size_delta_bytes": right.size_bytes - left.size_bytes,
            "source_name_changed": left.source_name != right.source_name,
            "metadata_change_count": len(metadata_changes),
            "metadata_changes": metadata_changes,
            "left_qc": self._qc_summary_for_source(project_id, left.dataset_id),
            "right_qc": self._qc_summary_for_source(project_id, right.dataset_id),
        }

    def read_registered_artifact(self, project_id: str, dataset_id: str, *, max_bytes: int = 64 * 1024 * 1024) -> tuple[str, str, bytes]:
        """Read one registered artifact through the manifest/path-containment boundary."""
        manifest = self.manifests.load(project_id, dataset_id)
        if manifest.size_bytes > max_bytes:
            raise ValueError("artifact exceeds the bounded download size")
        path = self.artifacts.resolve(project_id=project_id, relative_path=manifest.artifact_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        return manifest.source_name or path.name, manifest.format_id, path.read_bytes()

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
