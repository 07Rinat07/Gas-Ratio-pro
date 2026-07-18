"""End-to-end acceptance runner for the visible Professional Print Center.

The runner follows the same user path as the application: persist/select a
physical profile, build the page-aware preview, expose the visible view model,
attach the direct multi-page contract to the presentation model, export the
HTML/PDF/DOCX bundle, and deliver multi-page SVG/PNG static artifacts.  It
produces a JSON-safe evidence report suitable for release QA.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from typing import Any, Mapping
from zipfile import ZipFile

import pandas as pd

from core.physical_print_profiles import PhysicalPrintProfile, UserPhysicalPrintProfileStore
from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_export import (
    PresentationExportOptions,
    export_presentation_package,
    validate_presentation_bundle_export,
)
from reports.print_center import build_professional_print_center_view
from services.page_aware_static_export import build_page_aware_static_artifact
from services.report_page_aware_preview import ReportPageAwarePreviewService


@dataclass(frozen=True, slots=True)
class PrintCenterAcceptanceArtifact:
    kind: str
    file_name: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "file_name": self.file_name,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class PrintCenterAcceptanceResult:
    schema: str = "gas-ratio-pro/print-center/acceptance/v1"
    version: str = "1.0"
    profile_id: str = ""
    page_count: int = 0
    parity_gate_id: str = ""
    geometry_signature: str = ""
    checks: Mapping[str, bool] = field(default_factory=dict)
    artifacts: tuple[PrintCenterAcceptanceArtifact, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(self.checks.values()) and not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "profile_id": self.profile_id,
            "page_count": self.page_count,
            "parity_gate_id": self.parity_gate_id,
            "geometry_signature": self.geometry_signature,
            "checks": dict(self.checks),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "issues": list(self.issues),
            "ok": self.ok,
            "direct_multi_page": True,
            "single_page_fallback": False,
            "formats": ["html", "pdf", "docx", "svg", "png"],
        }


class ProfessionalPrintCenterAcceptanceRunner:
    """Execute the complete physical preview and export acceptance path."""

    def __init__(self, preview_service: ReportPageAwarePreviewService | None = None) -> None:
        self._preview = preview_service or ReportPageAwarePreviewService()

    def run(
        self,
        frame: pd.DataFrame,
        *,
        output_dir: Path | str,
        profile: PhysicalPrintProfile,
        profile_store_path: Path | str,
        project_id: str = "acceptance-project",
        source_id: str = "acceptance-well",
        title: str = "Professional Print Center acceptance",
        locale: str = "en",
        curve_limit: int = 12,
    ) -> PrintCenterAcceptanceResult:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        issues: list[str] = []
        checks: dict[str, bool] = {}
        artifacts: list[PrintCenterAcceptanceArtifact] = []

        store = UserPhysicalPrintProfileStore(profile_store_path)
        try:
            persisted = store.upsert(profile)
            selected = store.resolve(persisted.id)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return PrintCenterAcceptanceResult(
                profile_id=profile.id,
                checks={"profile_persisted_and_selected": False},
                issues=(f"profile_store_failed:{type(exc).__name__}",),
            )
        checks["profile_persisted_and_selected"] = selected == persisted

        try:
            physical = self._preview.prepare(
                frame,
                project_id=project_id,
                source_id=source_id,
                title=title,
                locale=locale,
                physical_profile=selected,
                show_page_chrome=True,
                curve_limit=curve_limit,
                raster_dpi=selected.dpi,
            )
        except Exception as exc:  # release evidence must record adapter failures
            return PrintCenterAcceptanceResult(
                profile_id=selected.id,
                checks=checks,
                issues=(f"physical_preview_failed:{type(exc).__name__}",),
            )

        package = physical.prepared.package
        preview = package.preview_contract(title=title)
        view = build_professional_print_center_view(
            physical.prepared,
            project_id=project_id,
            locale=locale,
            title=title,
            output_format="bundle",
        )
        checks.update(
            {
                "physical_package_ready": physical.export_ready,
                "parity_gate_passed": bool(package.parity_gate.get("ok")),
                "visible_view_ready": view.export_ready,
                "visible_view_has_every_page": view.page_count == package.page_count and view.page_count > 0,
                "direct_preview_contract": (
                    preview.get("schema") == "visualization.preview.page-aware"
                    and preview.get("direct_multi_page") is True
                    and preview.get("single_page_fallback") is False
                    and len(preview.get("pages", ())) == package.page_count
                ),
            }
        )

        report = build_hydrocarbon_report_payload(frame, include_plot=False, locale=locale)
        model = report.presentation_model
        if model is None:
            issues.append("presentation_model_missing")
        else:
            model = replace(model, visualization_payloads=(physical.report_payload,))
            try:
                export = export_presentation_package(
                    model,
                    kind="bundle",
                    options=PresentationExportOptions(
                        output_dir=output,
                        base_name="print-center-acceptance",
                        include_figures=True,
                    ),
                )
                validation = validate_presentation_bundle_export(export.manifest_path)
                checks["document_bundle_valid"] = validation.ok
                manifest = json.loads(export.manifest_path.read_text(encoding="utf-8"))
                checks["bundle_uses_same_page_count"] = (
                    int(_mapping(manifest.get("visualization")).get("total_pages") or 0) == package.page_count
                )
                for kind, path in export.files.items():
                    artifacts.append(_path_artifact(kind, path))
                artifacts.append(_path_artifact("bundle_manifest", export.manifest_path))
                checks.update(self._inspect_document_outputs(export.files, package.page_count))
            except Exception as exc:
                issues.append(f"document_bundle_export_failed:{type(exc).__name__}")
                checks.setdefault("document_bundle_valid", False)

        for format_name in ("svg", "png"):
            try:
                static = build_page_aware_static_artifact(
                    package,
                    format_name=format_name,
                    base_name="print-center-acceptance",
                )
                path = output / static.file_name
                path.write_bytes(static.content)
                artifacts.append(_path_artifact(format_name, path))
                checks[f"{format_name}_static_delivery_valid"] = self._inspect_static_artifact(
                    static.content,
                    bundled=static.bundled,
                    expected_page_count=package.page_count,
                )
            except Exception as exc:
                issues.append(f"{format_name}_static_delivery_failed:{type(exc).__name__}")
                checks[f"{format_name}_static_delivery_valid"] = False

        result = PrintCenterAcceptanceResult(
            profile_id=selected.id,
            page_count=package.page_count,
            parity_gate_id=str(package.parity_gate.get("gate_id") or ""),
            geometry_signature=package.geometry_signature,
            checks=checks,
            artifacts=tuple(artifacts),
            issues=tuple(dict.fromkeys(issues)),
        )
        report_path = output / "print-center-acceptance-report.json"
        report_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return replace(result, artifacts=(*result.artifacts, _path_artifact("acceptance_report", report_path)))

    @staticmethod
    def _inspect_document_outputs(files: Mapping[str, Path], expected_page_count: int) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        html_path = files.get("html")
        pdf_path = files.get("pdf")
        docx_path = files.get("docx")
        if html_path is not None and html_path.exists():
            html = html_path.read_text(encoding="utf-8")
            checks["html_contains_every_preview_page"] = html.count("visualization-preview-page") >= expected_page_count
        else:
            checks["html_contains_every_preview_page"] = False
        if pdf_path is not None and pdf_path.exists():
            pdf = pdf_path.read_bytes()
            checks["pdf_is_valid"] = pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-2048:]
        else:
            checks["pdf_is_valid"] = False
        if docx_path is not None and docx_path.exists():
            try:
                with ZipFile(docx_path) as archive:
                    media = [name for name in archive.namelist() if name.startswith("word/media/")]
                    document_xml = archive.read("word/document.xml")
                checks["docx_contains_every_preview_page"] = len(media) >= expected_page_count and bool(document_xml)
            except Exception:
                checks["docx_contains_every_preview_page"] = False
        else:
            checks["docx_contains_every_preview_page"] = False
        return checks

    @staticmethod
    def _inspect_static_artifact(content: bytes, *, bundled: bool, expected_page_count: int) -> bool:
        if expected_page_count == 1:
            return not bundled and bool(content)
        if not bundled:
            return False
        try:
            with ZipFile(BytesIO(content)) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                files = tuple(manifest.get("files", ()))
                return (
                    int(manifest.get("page_count") or 0) == expected_page_count
                    and manifest.get("single_page_fallback") is False
                    and len(files) == expected_page_count
                    and all(str(name) in archive.namelist() for name in files)
                )
        except Exception:
            return False


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _path_artifact(kind: str, path: Path) -> PrintCenterAcceptanceArtifact:
    content = path.read_bytes()
    return PrintCenterAcceptanceArtifact(
        kind=kind,
        file_name=path.name,
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
    )


__all__ = [
    "PrintCenterAcceptanceArtifact",
    "PrintCenterAcceptanceResult",
    "ProfessionalPrintCenterAcceptanceRunner",
]
