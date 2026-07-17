"""PNG adapter for page-aware Visualization Engine SVG artifacts.

PNG is intentionally derived from the shared physical SVG pages.  The adapter
does not rebuild tracks, axes or curves, so raster exports keep the exact page
partition, scale and geometry signature used by SVG and PDF.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping

from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer


@dataclass(frozen=True, slots=True)
class PngSceneRenderResult:
    schema: str = "visualization.renderer.png.result"
    version: str = "1.0"
    renderer: str = "visualization_png_scene_renderer"
    source_schema: str = ""
    dpi: int = 300
    width_px: int = 0
    height_px: int = 0
    page_count: int = 0
    primitive_count: int = 0
    clip_count: int = 0
    print_layout_applied: bool = False
    page_size: str = ""
    geometry_signature: str = ""
    export_ready: bool = False
    png_bytes: bytes = b""
    page_pngs: tuple[bytes, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "renderer": self.renderer,
            "source_schema": self.source_schema,
            "format": "png",
            "dpi": self.dpi,
            "width_px": self.width_px,
            "height_px": self.height_px,
            "page_count": self.page_count,
            "primitive_count": self.primitive_count,
            "clip_count": self.clip_count,
            "print_layout_applied": self.print_layout_applied,
            "page_size": self.page_size,
            "geometry_signature": self.geometry_signature,
            "export_ready": self.export_ready,
            "byte_size": len(self.png_bytes),
            "sha256": sha256(self.png_bytes).hexdigest() if self.png_bytes else "",
            "page_byte_sizes": [len(item) for item in self.page_pngs],
            "page_sha256": [sha256(item).hexdigest() for item in self.page_pngs],
            "contains_raw_dataframe": False,
            "issues": list(self.issues),
        }


class VisualizationPngSceneRenderer:
    """Rasterize every shared SVG print page at an explicit physical DPI."""

    def __init__(self, svg_renderer: VisualizationSvgSceneRenderer | None = None) -> None:
        self._svg_renderer = svg_renderer or VisualizationSvgSceneRenderer()

    def render(self, source: Mapping[str, Any], *, dpi: int = 300) -> PngSceneRenderResult:
        normalized_dpi = max(72, min(int(dpi or 300), 600))
        svg_result = self._svg_renderer.render(source)
        svg_pages = tuple(svg_result.page_svgs or ((svg_result.svg,) if svg_result.svg else ()))
        issues = list(svg_result.issues)
        if not svg_result.export_ready or not svg_pages:
            issues.append("png_renderer_svg_source_unavailable")
            return PngSceneRenderResult(
                source_schema=svg_result.source_schema,
                dpi=normalized_dpi,
                primitive_count=svg_result.primitive_count,
                clip_count=svg_result.clip_count,
                print_layout_applied=svg_result.print_layout_applied,
                page_size=svg_result.page_size,
                geometry_signature=svg_result.geometry_signature,
                issues=tuple(dict.fromkeys(issues)),
            )

        try:
            import fitz  # type: ignore

            page_pngs: list[bytes] = []
            first_width = first_height = 0
            scale = normalized_dpi / 72.0
            for page_index, svg in enumerate(svg_pages, start=1):
                document = fitz.open(stream=svg.encode("utf-8"), filetype="svg")
                try:
                    if document.page_count < 1:
                        issues.append(f"png_renderer_svg_page_empty:{page_index}")
                        continue
                    page = document.load_page(0)
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    if not page_pngs:
                        first_width, first_height = int(pixmap.width), int(pixmap.height)
                    page_pngs.append(pixmap.tobytes("png"))
                finally:
                    document.close()
        except ImportError:
            issues.append("png_renderer_pymupdf_unavailable")
            page_pngs = []
            first_width = first_height = 0
        except Exception as exc:
            issues.append(f"png_renderer_error:{type(exc).__name__}")
            page_pngs = []
            first_width = first_height = 0

        ready = len(page_pngs) == len(svg_pages) and all(item.startswith(b"\x89PNG\r\n\x1a\n") for item in page_pngs)
        if len(page_pngs) != len(svg_pages):
            issues.append(f"png_renderer_page_count_mismatch:{len(svg_pages)}:{len(page_pngs)}")
        return PngSceneRenderResult(
            source_schema=svg_result.source_schema,
            dpi=normalized_dpi,
            width_px=first_width,
            height_px=first_height,
            page_count=len(page_pngs),
            primitive_count=svg_result.primitive_count,
            clip_count=svg_result.clip_count,
            print_layout_applied=svg_result.print_layout_applied,
            page_size=svg_result.page_size,
            geometry_signature=svg_result.geometry_signature,
            export_ready=ready,
            png_bytes=page_pngs[0] if page_pngs else b"",
            page_pngs=tuple(page_pngs),
            issues=tuple(dict.fromkeys(issues)),
        )


__all__ = ["PngSceneRenderResult", "VisualizationPngSceneRenderer"]

