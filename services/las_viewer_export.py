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
from services.las_viewer_shared_interaction import LasViewerSharedInteractionResult
from services.visualization_export_qa import VisualizationExportQaValidator
from services.visualization_pdf_render_model_renderer import VisualizationPdfRenderModelRenderer
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
    validation: Mapping[str, Any] = field(default_factory=dict)
    qa: Mapping[str, Any] = field(default_factory=dict)
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.export_ready and bool(self.content) and not self.issues

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

    @property
    def ok(self) -> bool:
        return self.svg.ok and self.pdf.ok and self.geometry_signature_match and bool(self.qa.get("ok"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.export.bundle",
            "version": "1.0",
            "svg": self.svg.to_dict(),
            "pdf": self.pdf.to_dict(),
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
        self._svg = svg_renderer or VisualizationSvgSceneRenderer()
        self._pdf = pdf_renderer or VisualizationPdfRenderModelRenderer()
        self._qa = qa_validator or VisualizationExportQaValidator()

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
        svg_artifact = self._svg.render(pipeline)
        pdf_artifact = self._pdf.render(pipeline)
        qa = self._qa.validate(pipeline, svg_artifact, pdf_artifact).to_dict()

        svg_issues = tuple(dict.fromkeys(svg_artifact.issues))
        pdf_issues = tuple(dict.fromkeys(pdf_artifact.issues))
        svg = LasViewerExportResult(
            format="svg",
            viewport_start=start,
            viewport_stop=stop,
            geometry_signature=svg_artifact.geometry_signature,
            export_ready=svg_artifact.export_ready,
            content=svg_artifact.svg.encode("utf-8") if svg_artifact.svg else b"",
            validation=validation,
            qa=qa,
            issues=svg_issues,
        )
        pdf = LasViewerExportResult(
            format="pdf",
            viewport_start=start,
            viewport_stop=stop,
            geometry_signature=pdf_artifact.geometry_signature,
            export_ready=pdf_artifact.export_ready,
            content=pdf_artifact.pdf_bytes,
            validation=validation,
            qa=qa,
            issues=pdf_issues,
        )
        return LasViewerExportBundle(
            svg=svg,
            pdf=pdf,
            geometry_signature_match=bool(
                svg.geometry_signature and svg.geometry_signature == pdf.geometry_signature
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
