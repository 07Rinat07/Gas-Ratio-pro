"""Export the current LAS Viewer viewport through Visualization Engine.

The service consumes the existing shared-interaction snapshot. It does not
rebuild layout in UI code and delegates validation, SVG rendering, PDF rendering
and cross-renderer QA to the established Visualization Engine contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping

from services.las_viewer_navigation import LasViewerNavigationController
from services.page_aware_static_export import build_page_aware_static_artifact
from services.las_viewer_shared_interaction import LasViewerSharedInteractionResult
from services.visualization_export_qa import VisualizationExportQaValidator
from services.visualization_page_aware_package import VisualizationPageAwarePackageBuilder
from services.visualization_pdf_render_model_renderer import VisualizationPdfRenderModelRenderer
from services.visualization_print_center_contract import VisualizationPrintCenterService
from services.visualization_render_validation import VisualizationRenderValidationPipeline
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer


@dataclass(frozen=True, slots=True)
class LasViewerExportResult:
    format: str
    viewport_start: float
    viewport_stop: float
    geometry_signature: str = ""
    export_ready: bool = False
    content: bytes = b""
    page_contents: tuple[bytes, ...] = field(default_factory=tuple)
    page_count: int = 0
    validation: Mapping[str, Any] = field(default_factory=dict)
    qa: Mapping[str, Any] = field(default_factory=dict)
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.export_ready and bool(self.content) and not self.issues and (
            not self.page_contents or all(bool(item) for item in self.page_contents)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.export.result",
            "version": "1.0",
            "format": self.format,
            "viewport": {"start": self.viewport_start, "stop": self.viewport_stop},
            "geometry_signature": self.geometry_signature,
            "export_ready": self.export_ready,
            "ok": self.ok,
            "byte_size": len(self.content),
            "page_count": self.page_count or (len(self.page_contents) if self.page_contents else (1 if self.content else 0)),
            "page_byte_sizes": [len(item) for item in self.page_contents],
            "page_sha256": [sha256(item).hexdigest() for item in self.page_contents],
            "sha256": sha256(self.content).hexdigest() if self.content else "",
            "validation": dict(self.validation),
            "qa": dict(self.qa),
            "issues": list(self.issues),
            "renderer_neutral": True,
            "raw_dataframe_included": False,
        }


@dataclass(frozen=True, slots=True)
class LasViewerExportBundle:
    svg: LasViewerExportResult
    pdf: LasViewerExportResult
    geometry_signature_match: bool
    qa: Mapping[str, Any]
    png: LasViewerExportResult | None = None
    print_center_summary: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        png_ok = self.png is None or self.png.ok
        return self.svg.ok and self.pdf.ok and png_ok and self.geometry_signature_match and bool(self.qa.get("ok"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.export.bundle",
            "version": "1.1",
            "svg": self.svg.to_dict(),
            "pdf": self.pdf.to_dict(),
            "png": self.png.to_dict() if self.png is not None else None,
            "print_center_summary": dict(self.print_center_summary),
            "geometry_signature_match": self.geometry_signature_match,
            "qa": dict(self.qa),
            "ok": self.ok,
            "renderer_neutral": True,
            "raw_dataframe_included": False,
        }


class LasViewerExportService:
    """Export the already computed current viewport without UI-side layout work."""

    def __init__(
        self,
        *,
        svg_renderer: VisualizationSvgSceneRenderer | None = None,
        pdf_renderer: VisualizationPdfRenderModelRenderer | None = None,
        qa_validator: VisualizationExportQaValidator | None = None,
    ) -> None:
        builder = VisualizationPageAwarePackageBuilder(
            svg_renderer=svg_renderer or VisualizationSvgSceneRenderer(),
            pdf_renderer=pdf_renderer or VisualizationPdfRenderModelRenderer(),
            qa_validator=qa_validator or VisualizationExportQaValidator(),
        )
        self._print_center = VisualizationPrintCenterService(builder)

    def export_current_view(
        self,
        source: LasViewerNavigationController | LasViewerSharedInteractionResult,
    ) -> LasViewerExportBundle:
        snapshot = source.render().interaction if isinstance(source, LasViewerNavigationController) else source
        pipeline = self._pipeline(snapshot)
        viewport = snapshot.viewer_state.get("interaction", {}).get("viewport", {})
        start = float(viewport.get("domain_start"))
        stop = float(viewport.get("domain_stop"))

        validation = VisualizationRenderValidationPipeline().validate(pipeline).to_dict()
        print_layout = pipeline.get("print_layout") if isinstance(pipeline.get("print_layout"), Mapping) else {}
        page_chrome = print_layout.get("page_chrome") if isinstance(print_layout.get("page_chrome"), Mapping) else {}
        locale = str(page_chrome.get("locale") or "ru")
        prepared = self._print_center.prepare(pipeline, locale=locale)
        package = prepared.package
        qa = dict(package.qa)

        svg_pages = tuple(page.svg.encode("utf-8") for page in package.pages)
        png_pages = tuple(page.png_bytes for page in package.pages)
        svg_delivery = (
            build_page_aware_static_artifact(package, format_name="svg", base_name="las_viewer")
            if package.export_ready else None
        )
        png_delivery = (
            build_page_aware_static_artifact(package, format_name="png", base_name="las_viewer")
            if package.export_ready else None
        )
        svg = LasViewerExportResult(
            format="svg",
            viewport_start=start,
            viewport_stop=stop,
            geometry_signature=package.geometry_signature,
            export_ready=package.export_ready,
            content=svg_delivery.content if svg_delivery is not None else b"",
            page_contents=svg_pages,
            page_count=package.page_count,
            validation=validation,
            qa=qa,
            issues=package.issues,
        )
        pdf = LasViewerExportResult(
            format="pdf",
            viewport_start=start,
            viewport_stop=stop,
            geometry_signature=package.geometry_signature,
            export_ready=package.export_ready,
            content=package.pdf_bytes,
            page_count=package.page_count,
            validation=validation,
            qa=qa,
            issues=package.issues,
        )
        png = LasViewerExportResult(
            format="png",
            viewport_start=start,
            viewport_stop=stop,
            geometry_signature=package.geometry_signature,
            export_ready=package.export_ready,
            content=png_delivery.content if png_delivery is not None else b"",
            page_contents=png_pages,
            page_count=package.page_count,
            validation=validation,
            qa=qa,
            issues=package.issues,
        )
        return LasViewerExportBundle(
            svg=svg,
            pdf=pdf,
            png=png,
            print_center_summary=prepared.summary.to_dict(),
            geometry_signature_match=bool(
                svg.geometry_signature
                and svg.geometry_signature == pdf.geometry_signature == png.geometry_signature
            ),
            qa=qa,
        )

    @staticmethod
    def _pipeline(snapshot: LasViewerSharedInteractionResult) -> dict[str, Any]:
        viewport_result = snapshot.render_result.get("viewport_result") or {}
        pipeline = viewport_result.get("pipeline") or {}
        if not isinstance(pipeline, Mapping) or pipeline.get("schema") != "visualization.scene.pipeline.result":
            raise ValueError("LAS Viewer export requires a Visualization Engine pipeline result")
        return dict(pipeline)
