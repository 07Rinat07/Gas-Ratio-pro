"""Deterministic large-LAS regression checks for the Visualization Engine."""
from __future__ import annotations

from dataclasses import dataclass, field
import tracemalloc
from typing import Any, Mapping

from services.visualization_pdf_render_model_renderer import VisualizationPdfRenderModelRenderer
from services.visualization_renderer_parity import VisualizationRendererParityValidator
from services.visualization_scene_pipeline import VisualizationScenePipeline
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer


@dataclass(frozen=True, slots=True)
class LargeLasRegressionReport:
    schema: str = "visualization.large_las.regression"
    version: str = "1.0"
    source_point_count: int = 0
    render_point_count: int = 0
    reduction_ratio: float = 0.0
    peak_memory_bytes: int = 0
    memory_limit_bytes: int = 0
    cache_hit_on_repeat: bool = False
    cache_bytes: int = 0
    cache_max_bytes: int = 0
    svg_bytes: int = 0
    pdf_bytes: int = 0
    geometry_signature_match: bool = False
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "ok": self.ok,
            "source_point_count": self.source_point_count,
            "render_point_count": self.render_point_count,
            "reduction_ratio": self.reduction_ratio,
            "peak_memory_bytes": self.peak_memory_bytes,
            "memory_limit_bytes": self.memory_limit_bytes,
            "cache_hit_on_repeat": self.cache_hit_on_repeat,
            "cache_bytes": self.cache_bytes,
            "cache_max_bytes": self.cache_max_bytes,
            "svg_bytes": self.svg_bytes,
            "pdf_bytes": self.pdf_bytes,
            "geometry_signature_match": self.geometry_signature_match,
            "issues": list(self.issues),
        }


class VisualizationLargeLasRegression:
    """Execute one bounded-memory, renderer-parity regression scenario."""

    def __init__(self, pipeline: VisualizationScenePipeline | None = None) -> None:
        self.pipeline = pipeline or VisualizationScenePipeline()

    def run(
        self,
        payload: Mapping[str, Any],
        *,
        memory_limit_bytes: int = 256 * 1024 * 1024,
        minimum_reduction_ratio: float = 0.80,
    ) -> LargeLasRegressionReport:
        tracemalloc.start()
        try:
            first = self.pipeline.run(payload).to_dict()
            second = self.pipeline.run(payload).to_dict()
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        svg = VisualizationSvgSceneRenderer().render(first).to_dict()
        pdf = VisualizationPdfRenderModelRenderer().render(first).to_dict()
        parity = VisualizationRendererParityValidator().validate(first, svg).to_dict()
        performance = first["performance"]
        issues: list[str] = []
        if not first.get("ok"):
            issues.append("large_las_pipeline_validation_failed")
        if performance["reduction_ratio"] < minimum_reduction_ratio:
            issues.append("large_las_downsampling_reduction_below_threshold")
        if peak > memory_limit_bytes:
            issues.append("large_las_peak_memory_limit_exceeded")
        if performance["cache_bytes"] > performance["cache_max_bytes"]:
            issues.append("large_las_cache_byte_budget_exceeded")
        if not second["performance"]["cache_hit"]:
            issues.append("large_las_repeat_render_cache_miss")
        signatures_match = bool(svg.get("geometry_signature")) and (
            svg.get("geometry_signature") == pdf.get("geometry_signature")
        )
        if not signatures_match:
            issues.append("large_las_svg_pdf_geometry_signature_mismatch")
        if not parity.get("ok"):
            issues.append("large_las_svg_renderer_parity_failed")
        if not svg.get("svg"):
            issues.append("large_las_svg_export_empty")
        pdf_size = int(pdf.get("byte_size") or 0)
        if pdf_size <= 0 or not pdf.get("export_ready"):
            issues.append("large_las_pdf_export_empty")
        return LargeLasRegressionReport(
            source_point_count=performance["source_point_count"],
            render_point_count=performance["render_point_count"],
            reduction_ratio=performance["reduction_ratio"],
            peak_memory_bytes=peak,
            memory_limit_bytes=memory_limit_bytes,
            cache_hit_on_repeat=second["performance"]["cache_hit"],
            cache_bytes=performance["cache_bytes"],
            cache_max_bytes=performance["cache_max_bytes"],
            svg_bytes=len(svg["svg"].encode("utf-8")),
            pdf_bytes=pdf_size,
            geometry_signature_match=signatures_match,
            issues=tuple(issues),
        )


__all__ = ["LargeLasRegressionReport", "VisualizationLargeLasRegression"]
