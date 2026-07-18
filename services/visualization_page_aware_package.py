"""Unified page-aware export package for Visualization Engine.

The package is the renderer-neutral hand-off used by Print Center and report
renderers.  It renders one validated pipeline exactly once per output adapter,
keeps the shared physical page partition, and exposes a compact preview contract
that DOCX/HTML layers can consume without rebuilding visualization geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Any, Mapping

from services.visualization_cross_format_parity import VisualizationCrossFormatParityGate
from services.visualization_export_qa import VisualizationExportQaValidator
from services.visualization_pdf_render_model_renderer import VisualizationPdfRenderModelRenderer
from services.visualization_png_scene_renderer import VisualizationPngSceneRenderer
from services.visualization_renderer_parity import visualization_geometry_signature
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer


@dataclass(frozen=True, slots=True)
class VisualizationPageAsset:
    index: int
    track_ids: tuple[str, ...]
    width_pt: float
    height_pt: float
    chrome_primitive_count: int
    svg: str
    png_bytes: bytes

    @property
    def export_ready(self) -> bool:
        return bool(self.svg.startswith("<svg") and self.png_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

    def to_dict(self, *, include_payloads: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "index": self.index,
            "track_ids": list(self.track_ids),
            "width_pt": self.width_pt,
            "height_pt": self.height_pt,
            "chrome_primitive_count": self.chrome_primitive_count,
            "svg_size_bytes": len(self.svg.encode("utf-8")),
            "svg_sha256": sha256(self.svg.encode("utf-8")).hexdigest() if self.svg else "",
            "png_size_bytes": len(self.png_bytes),
            "png_sha256": sha256(self.png_bytes).hexdigest() if self.png_bytes else "",
            "export_ready": self.export_ready,
        }
        if include_payloads:
            data["svg"] = self.svg
            data["png_bytes"] = self.png_bytes
        return data


@dataclass(frozen=True, slots=True)
class VisualizationPageAwarePackage:
    schema: str = "visualization.page-aware.package"
    version: str = "1.3"
    profile_id: str = ""
    page_size: str = ""
    orientation: str = ""
    dpi: int = 0
    geometry_signature: str = ""
    track_count: int = 0
    curve_count: int = 0
    overlay_count: int = 0
    page_chrome: Mapping[str, Any] = field(default_factory=dict)
    pages: tuple[VisualizationPageAsset, ...] = field(default_factory=tuple)
    pdf_bytes: bytes = b""
    qa: Mapping[str, Any] = field(default_factory=dict)
    parity_gate: Mapping[str, Any] = field(default_factory=dict)
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def export_ready(self) -> bool:
        return (
            bool(self.pages)
            and all(page.export_ready for page in self.pages)
            and self.pdf_bytes.startswith(b"%PDF-")
            and bool(self.geometry_signature)
            and bool(self.qa.get("ok"))
            and bool(self.parity_gate.get("ok"))
            and not self.issues
        )

    def preview_contract(self, *, title: str = "LAS visualization") -> dict[str, Any]:
        """Return the direct multi-page contract consumed by document renderers.

        ``pages`` is the canonical field. ``page_svgs`` remains a compatibility
        mirror for existing bundle tooling, but page-aware consumers are not
        allowed to fall back to the first-page ``svg`` value.
        """
        pages = [
            {
                "index": page.index,
                "track_ids": list(page.track_ids),
                "width_pt": page.width_pt,
                "height_pt": page.height_pt,
                "chrome_primitive_count": page.chrome_primitive_count,
                "svg": page.svg,
            }
            for page in self.pages
        ]
        return {
            "schema": "visualization.preview.page-aware",
            "version": "1.1",
            "kind": "page_aware_svg_preview",
            "title": title,
            "format": "svg",
            "svg": self.pages[0].svg if self.pages else "",
            "pages": pages,
            "page_svgs": [page["svg"] for page in pages],
            "page_count": self.page_count,
            "page_track_ids": [page["track_ids"] for page in pages],
            "track_count": self.track_count,
            "curve_count": self.curve_count,
            "overlay_count": self.overlay_count,
            "profile_id": self.profile_id,
            "page_size": self.page_size,
            "orientation": self.orientation,
            "dpi": self.dpi,
            "geometry_signature": self.geometry_signature,
            "locale": str(self.page_chrome.get("locale") or "ru"),
            "page_chrome": dict(self.page_chrome),
            "page_chrome_enabled": bool(self.page_chrome.get("enabled")),
            "page_chrome_primitive_counts": [page.chrome_primitive_count for page in self.pages],
            "export_ready": self.export_ready,
            "parity_gate": dict(self.parity_gate),
            "cross_format_parity_passed": bool(self.parity_gate.get("ok")),
            "contains_raw_dataframe": False,
            "single_page_fallback": False,
            "legacy_svg_fallback_allowed": False,
            "direct_multi_page": True,
        }

    def to_dict(self, *, include_payloads: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema": self.schema,
            "version": self.version,
            "profile_id": self.profile_id,
            "page_size": self.page_size,
            "orientation": self.orientation,
            "dpi": self.dpi,
            "geometry_signature": self.geometry_signature,
            "track_count": self.track_count,
            "curve_count": self.curve_count,
            "overlay_count": self.overlay_count,
            "page_chrome": dict(self.page_chrome),
            "page_chrome_enabled": bool(self.page_chrome.get("enabled")),
            "page_count": self.page_count,
            "pages": [page.to_dict(include_payloads=include_payloads) for page in self.pages],
            "pdf_size_bytes": len(self.pdf_bytes),
            "pdf_sha256": sha256(self.pdf_bytes).hexdigest() if self.pdf_bytes else "",
            "qa": dict(self.qa),
            "parity_gate": dict(self.parity_gate),
            "cross_format_parity_passed": bool(self.parity_gate.get("ok")),
            "issues": list(self.issues),
            "export_ready": self.export_ready,
            "renderer_neutral": True,
            "single_pipeline_source": True,
            "single_page_fallback": False,
            "contains_raw_dataframe": False,
        }
        if include_payloads:
            data["pdf_bytes"] = self.pdf_bytes
        return data


class VisualizationPageAwarePackageBuilder:
    """Build one auditable package from one validated scene pipeline result."""

    def __init__(
        self,
        *,
        svg_renderer: VisualizationSvgSceneRenderer | None = None,
        pdf_renderer: VisualizationPdfRenderModelRenderer | None = None,
        png_renderer: VisualizationPngSceneRenderer | None = None,
        qa_validator: VisualizationExportQaValidator | None = None,
        parity_gate: VisualizationCrossFormatParityGate | None = None,
    ) -> None:
        self._svg = svg_renderer or VisualizationSvgSceneRenderer()
        self._pdf = pdf_renderer or VisualizationPdfRenderModelRenderer()
        self._png = png_renderer or VisualizationPngSceneRenderer(self._svg)
        self._qa = qa_validator or VisualizationExportQaValidator()
        self._parity_gate = parity_gate or VisualizationCrossFormatParityGate()

    def build(self, pipeline: Mapping[str, Any], *, raster_dpi: int = 300) -> VisualizationPageAwarePackage:
        issues: list[str] = []
        if str(pipeline.get("schema") or "") != "visualization.scene.pipeline.result":
            return VisualizationPageAwarePackage(issues=("page_aware_package_unsupported_pipeline_schema",))

        print_layout = _mapping(pipeline.get("print_layout"))
        layout_pages = _mapping_list(print_layout.get("pages"))
        if not bool(print_layout.get("ok")) or not layout_pages:
            issues.append("page_aware_package_print_layout_missing")

        svg = self._svg.render(pipeline)
        pdf = self._pdf.render(pipeline)
        png = self._png.render(pipeline, dpi=raster_dpi)
        qa = self._qa.validate(pipeline, svg, pdf).to_dict()

        expected_pages = len(layout_pages)
        if svg.page_count != expected_pages:
            issues.append(f"page_aware_package_svg_page_count_mismatch:{expected_pages}:{svg.page_count}")
        if pdf.page_count != expected_pages:
            issues.append(f"page_aware_package_pdf_page_count_mismatch:{expected_pages}:{pdf.page_count}")
        if png.page_count != expected_pages:
            issues.append(f"page_aware_package_png_page_count_mismatch:{expected_pages}:{png.page_count}")
        if not qa.get("ok"):
            issues.append("page_aware_package_renderer_qa_failed")

        signature = visualization_geometry_signature(pipeline)
        signatures = {value for value in (signature, svg.geometry_signature, pdf.geometry_signature, png.geometry_signature) if value}
        if len(signatures) != 1:
            issues.append("page_aware_package_geometry_signature_mismatch")

        page_assets: list[VisualizationPageAsset] = []
        for offset, page in enumerate(layout_pages):
            page_bounds = _mapping(page.get("page_bounds"))
            page_assets.append(
                VisualizationPageAsset(
                    index=int(page.get("index") or offset + 1),
                    track_ids=tuple(str(item) for item in page.get("track_ids", ()) if str(item)),
                    width_pt=_positive_float(page_bounds.get("width")),
                    height_pt=_positive_float(page_bounds.get("height")),
                    chrome_primitive_count=len(_mapping_list(page.get("chrome_primitives"))),
                    svg=svg.page_svgs[offset] if offset < len(svg.page_svgs) else "",
                    png_bytes=png.page_pngs[offset] if offset < len(png.page_pngs) else b"",
                )
            )

        issues.extend(svg.issues if not svg.export_ready else ())
        issues.extend(pdf.issues if not pdf.export_ready else ())
        issues.extend(png.issues if not png.export_ready else ())
        context = _mapping(pipeline.get("context"))
        candidate = VisualizationPageAwarePackage(
            profile_id=str(print_layout.get("profile_id") or ""),
            page_size=str(print_layout.get("page_size") or ""),
            orientation=str(print_layout.get("orientation") or ""),
            dpi=int(print_layout.get("dpi") or 0),
            geometry_signature=signature,
            track_count=int(context.get("track_count") or len({track for page in page_assets for track in page.track_ids})),
            curve_count=int(context.get("curve_count") or 0),
            overlay_count=int(context.get("overlay_count") or 0),
            page_chrome=_mapping(print_layout.get("page_chrome")),
            pages=tuple(page_assets),
            pdf_bytes=pdf.pdf_bytes,
            qa=qa,
            issues=tuple(dict.fromkeys(issues)),
        )
        parity = self._parity_gate.validate(
            pipeline,
            svg_result=svg,
            pdf_result=pdf,
            png_result=png,
            package_pages=candidate.pages,
            preview_contract=candidate.preview_contract(),
            raster_dpi=raster_dpi,
        )
        final_issues = list(candidate.issues)
        if not parity.ok:
            final_issues.append("page_aware_package_cross_format_parity_failed")
            final_issues.extend(parity.issues)
        return replace(
            candidate,
            parity_gate=parity.to_dict(),
            issues=tuple(dict.fromkeys(final_issues)),
        )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    return [dict(item) for item in value if isinstance(item, Mapping)] if isinstance(value, (list, tuple)) else []


def _positive_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if result > 0 else 0.0


__all__ = [
    "VisualizationPageAsset",
    "VisualizationPageAwarePackage",
    "VisualizationPageAwarePackageBuilder",
]
