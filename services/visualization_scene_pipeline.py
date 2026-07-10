"""Renderer-neutral Visualization Scene Pipeline.

This module adds an explicit pipeline layer above ``VisualizationEngineCore``.
The pipeline is intentionally small and deterministic: it validates an incoming
LAS visualization payload, builds a reusable scene context, delegates scene
construction to the engine core and returns a serializable result that can be
used by UI, report and export layers without recalculating visualization data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from services.visualization_domain_model import (
    VisualizationDomainModel,
    VisualizationDomainModelAdapter,
)
from services.visualization_engine_core import VisualizationEngineCore, VisualizationScene
from services.visualization_layout_engine import VisualizationLayout, VisualizationLayoutEngine
from services.visualization_axis_grid import (
    VisualizationAxisGridEngine,
    VisualizationAxisGridModel,
)
from services.visualization_track_engine import (
    VisualizationTrackCollection,
    VisualizationTrackEngine,
)
from services.visualization_label_legend import (
    VisualizationLabelLegendEngine,
    VisualizationLabelLegendModel,
)
from services.visualization_render_model import (
    VisualizationRenderModel,
    VisualizationRenderModelBuilder,
)
from services.visualization_print_layout import (
    VisualizationPrintLayout,
    VisualizationPrintLayoutEngine,
)
from services.visualization_performance import (
    VisualizationPerformanceEngine,
    VisualizationPerformanceProfile,
)


@dataclass(frozen=True, slots=True)
class VisualizationSceneContext:
    """Prepared scene input shared by all pipeline stages."""

    source: str = "las_visualization_payload"
    payload: dict[str, Any] = field(default_factory=dict)
    track_count: int = 0
    curve_count: int = 0
    overlay_count: int = 0
    depth_curve: str = ""
    depth_unit: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "track_count": self.track_count,
            "curve_count": self.curve_count,
            "overlay_count": self.overlay_count,
            "depth_curve": self.depth_curve,
            "depth_unit": self.depth_unit,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class VisualizationScenePipelineResult:
    """Complete pipeline output consumed by renderers and QA checks."""

    schema: str = "visualization.scene.pipeline.result"
    version: str = "1.0"
    domain_model: VisualizationDomainModel = field(default_factory=VisualizationDomainModel)
    context: VisualizationSceneContext = field(default_factory=VisualizationSceneContext)
    scene: VisualizationScene = field(default_factory=VisualizationScene)
    layout: VisualizationLayout = field(default_factory=VisualizationLayout)
    axis_grid: VisualizationAxisGridModel = field(default_factory=VisualizationAxisGridModel)
    track_model: VisualizationTrackCollection = field(default_factory=VisualizationTrackCollection)
    label_legend: VisualizationLabelLegendModel = field(default_factory=VisualizationLabelLegendModel)
    print_layout: VisualizationPrintLayout = field(default_factory=VisualizationPrintLayout)
    render_model: VisualizationRenderModel = field(default_factory=VisualizationRenderModel)
    performance: VisualizationPerformanceProfile = field(default_factory=VisualizationPerformanceProfile)
    validation: dict[str, Any] = field(default_factory=dict)
    stages: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return bool(self.validation.get("ok", False))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "domain_model": self.domain_model.to_dict(),
            "context": self.context.to_dict(),
            "scene": self.scene.to_dict(),
            "layout": self.layout.to_dict(),
            "axis_grid": self.axis_grid.to_dict(),
            "track_model": self.track_model.to_dict(),
            "label_legend": self.label_legend.to_dict(),
            "print_layout": self.print_layout.to_dict(),
            "render_model": self.render_model.to_dict(),
            "performance": self.performance.to_dict(),
            "validation": dict(self.validation),
            "stages": list(self.stages),
            "ok": self.ok,
        }


class DomainModelBuilder:
    """Adapt imported visualization data to the source-neutral domain model."""

    def __init__(self, adapter: VisualizationDomainModelAdapter | None = None) -> None:
        self.adapter = adapter or VisualizationDomainModelAdapter()

    def build(self, payload: Mapping[str, Any]) -> VisualizationDomainModel:
        return self.adapter.from_payload(
            payload,
            source_type=str(payload.get("source_type") or "las"),
            source_id=str(payload.get("source_id") or payload.get("las_id") or ""),
        )


class SceneContextBuilder:
    """Normalize raw payload metadata before scene construction."""

    def build(self, domain_model: VisualizationDomainModel) -> VisualizationSceneContext:
        prepared = domain_model.to_engine_payload()
        payload = prepared
        tracks = _list(payload.get("tracks"))
        curves = _list(payload.get("curves"))
        overlays = _list(payload.get("overlays"))
        warnings: list[str] = []
        if not tracks:
            warnings.append("scene_pipeline_input_has_no_tracks")
        if not curves:
            warnings.append("scene_pipeline_input_has_no_curves")
        if not str(payload.get("depth_curve") or "").strip():
            warnings.append("scene_pipeline_input_has_no_depth_curve")
        return VisualizationSceneContext(
            payload=prepared,
            track_count=len(tracks),
            curve_count=len(curves),
            overlay_count=len(overlays),
            depth_curve=str(payload.get("depth_curve") or ""),
            depth_unit=str(payload.get("depth_unit") or ""),
            warnings=tuple(warnings),
        )


class SceneBuilder:
    """Build a core VisualizationScene from prepared context."""

    def __init__(self, engine: VisualizationEngineCore | None = None) -> None:
        self.engine = engine or VisualizationEngineCore()

    def build(self, context: VisualizationSceneContext) -> VisualizationScene:
        return self.engine.build_scene(context.payload)


class LayoutBuilder:
    """Calculate renderer-neutral geometry after scene construction."""

    def __init__(self, engine: VisualizationLayoutEngine | None = None) -> None:
        self.engine = engine or VisualizationLayoutEngine()

    def build(self, scene: VisualizationScene) -> VisualizationLayout:
        return self.engine.build(scene.to_dict())


class AxisGridBuilder:
    """Prepare depth and curve axes plus printable grid geometry."""

    def __init__(self, engine: VisualizationAxisGridEngine | None = None) -> None:
        self.engine = engine or VisualizationAxisGridEngine()

    def build(self, scene: VisualizationScene, layout: VisualizationLayout) -> VisualizationAxisGridModel:
        return self.engine.build(scene.to_dict(), layout.to_dict())


class TrackModelBuilder:
    """Resolve ordered visible tracks and shared viewport state."""

    def __init__(self, engine: VisualizationTrackEngine | None = None) -> None:
        self.engine = engine or VisualizationTrackEngine()

    def build(
        self,
        scene: VisualizationScene,
        layout: VisualizationLayout,
    ) -> VisualizationTrackCollection:
        return self.engine.build(scene.to_dict(), layout.to_dict())


class LabelLegendBuilder:
    """Prepare renderer-neutral labels and legend items."""

    def __init__(self, engine: VisualizationLabelLegendEngine | None = None) -> None:
        self.engine = engine or VisualizationLabelLegendEngine()

    def build(
        self,
        scene: VisualizationScene,
        layout: VisualizationLayout,
        track_model: VisualizationTrackCollection,
    ) -> VisualizationLabelLegendModel:
        return self.engine.build(scene.to_dict(), layout.to_dict(), track_model.to_dict())


class PrintLayoutBuilder:
    """Prepare physical page geometry for export renderers."""

    def __init__(self, engine: VisualizationPrintLayoutEngine | None = None) -> None:
        self.engine = engine or VisualizationPrintLayoutEngine()

    def build(
        self,
        layout: VisualizationLayout,
        label_legend: VisualizationLabelLegendModel,
        options: Mapping[str, Any] | None = None,
    ) -> VisualizationPrintLayout:
        return self.engine.build(layout.to_dict(), label_legend.to_dict(), options)


class RenderModelBuilder:
    """Create renderer-neutral primitives from scene and layout contracts."""

    def __init__(self, builder: VisualizationRenderModelBuilder | None = None) -> None:
        self.builder = builder or VisualizationRenderModelBuilder()

    def build(
        self,
        scene: VisualizationScene,
        layout: VisualizationLayout,
        axis_grid: VisualizationAxisGridModel,
        track_model: VisualizationTrackCollection,
        label_legend: VisualizationLabelLegendModel,
        print_layout: VisualizationPrintLayout,
        performance_options: Mapping[str, Any] | None = None,
    ) -> VisualizationRenderModel:
        return self.builder.build(
            scene.to_dict(),
            layout.to_dict(),
            axis_grid.to_dict(),
            track_model.to_dict(),
            label_legend.to_dict(),
            print_layout.to_dict(),
            performance_options,
        )


class SceneValidator:
    """Validate the scene contract without renderer-specific checks."""

    def validate(self, context: VisualizationSceneContext, scene: VisualizationScene, layout: VisualizationLayout) -> dict[str, Any]:
        scene_dict = scene.to_dict()
        tracks = _list(scene_dict.get("tracks"))
        layers = _list(scene_dict.get("layers"))
        issues = list(context.warnings)
        if not tracks:
            issues.append("scene_has_no_tracks")
        if not layers:
            issues.append("scene_has_no_layers")
        issues.extend(layout.issues)
        known_track_ids = {str(track.get("id")) for track in tracks}
        orphan_layers = [layer.get("id") for layer in layers if str(layer.get("track_id")) not in known_track_ids]
        return {
            "ok": not issues,
            "issues": issues,
            "track_count": len(tracks),
            "layer_count": len(layers),
            "orphan_layer_ids": orphan_layers,
            "renderer_neutral": True,
            "layout_ok": layout.ok,
        }


class VisualizationScenePipeline:
    """Run the renderer-neutral visualization scene pipeline."""

    STAGES = ("domain_model", "context", "scene", "layout", "axis_grid", "track_model", "label_legend", "print_layout", "performance", "render_model", "validation")

    def __init__(
        self,
        domain_model_builder: DomainModelBuilder | None = None,
        context_builder: SceneContextBuilder | None = None,
        scene_builder: SceneBuilder | None = None,
        layout_builder: LayoutBuilder | None = None,
        axis_grid_builder: AxisGridBuilder | None = None,
        track_model_builder: TrackModelBuilder | None = None,
        label_legend_builder: LabelLegendBuilder | None = None,
        print_layout_builder: PrintLayoutBuilder | None = None,
        render_model_builder: RenderModelBuilder | None = None,
        performance_engine: VisualizationPerformanceEngine | None = None,
        validator: SceneValidator | None = None,
    ) -> None:
        self.domain_model_builder = domain_model_builder or DomainModelBuilder()
        self.context_builder = context_builder or SceneContextBuilder()
        self.scene_builder = scene_builder or SceneBuilder()
        self.layout_builder = layout_builder or LayoutBuilder()
        self.axis_grid_builder = axis_grid_builder or AxisGridBuilder()
        self.track_model_builder = track_model_builder or TrackModelBuilder()
        self.label_legend_builder = label_legend_builder or LabelLegendBuilder()
        self.print_layout_builder = print_layout_builder or PrintLayoutBuilder()
        self.render_model_builder = render_model_builder or RenderModelBuilder()
        self.performance_engine = performance_engine or VisualizationPerformanceEngine()
        self.validator = validator or SceneValidator()

    def run(self, payload: Mapping[str, Any]) -> VisualizationScenePipelineResult:
        domain_model = self.domain_model_builder.build(payload)
        context = self.context_builder.build(domain_model)
        scene = self.scene_builder.build(context)
        layout = self.layout_builder.build(scene)
        axis_grid = self.axis_grid_builder.build(scene, layout)
        track_model = self.track_model_builder.build(scene, layout)
        label_legend = self.label_legend_builder.build(scene, layout, track_model)
        print_options = payload.get("print_options") if isinstance(payload.get("print_options"), Mapping) else None
        print_layout = self.print_layout_builder.build(layout, label_legend, print_options)
        cache_enabled = bool(payload.get("performance_cache", True))
        performance_options = (
            dict(payload.get("performance_options"))
            if isinstance(payload.get("performance_options"), Mapping)
            else {}
        )
        cache_key = self.performance_engine.cache_key(
            scene.to_dict(),
            layout.to_dict(),
            axis_grid.to_dict(),
            track_model.to_dict(),
            label_legend.to_dict(),
            print_layout.to_dict(),
            performance_options,
        )
        cached_render_model = self.performance_engine.lookup(cache_key) if cache_enabled else None
        cache_hit = cached_render_model is not None
        if cached_render_model is None:
            render_model = self.render_model_builder.build(
                scene,
                layout,
                axis_grid,
                track_model,
                label_legend,
                print_layout,
                performance_options,
            )
            if cache_enabled:
                self.performance_engine.store(cache_key, render_model.to_dict())
        else:
            render_model = VisualizationRenderModel.from_dict(cached_render_model)
        performance = self.performance_engine.profile(
            key=cache_key,
            cache_hit=cache_hit,
            scene=scene.to_dict(),
            render_model=render_model.to_dict(),
            enabled=cache_enabled,
        )
        validation = self.validator.validate(context, scene, layout)
        validation["axis_grid_ok"] = axis_grid.ok
        validation["axis_count"] = len(axis_grid.axes)
        validation["grid_line_count"] = len(axis_grid.grid_lines)
        validation["track_model_ok"] = track_model.ok
        validation["visible_track_count"] = len(track_model.visible_tracks)
        validation["label_legend_ok"] = label_legend.ok
        validation["print_layout_ok"] = print_layout.ok
        validation["print_page_count"] = len(print_layout.pages)
        validation["label_count"] = len(label_legend.labels)
        validation["legend_item_count"] = len(label_legend.legend_items)
        validation["render_model_ok"] = render_model.ok
        validation["render_primitive_count"] = len(render_model.primitives)
        validation["performance_ok"] = performance.ok
        validation["render_model_cache_hit"] = performance.cache_hit
        validation["render_model_cache_key"] = performance.cache_key
        return VisualizationScenePipelineResult(
            domain_model=domain_model,
            context=context,
            scene=scene,
            layout=layout,
            axis_grid=axis_grid,
            track_model=track_model,
            label_legend=label_legend,
            print_layout=print_layout,
            render_model=render_model,
            performance=performance,
            validation=validation,
            stages=self.STAGES,
        )


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []
