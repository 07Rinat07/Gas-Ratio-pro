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


class SceneValidator:
    """Validate the scene contract without renderer-specific checks."""

    def validate(self, context: VisualizationSceneContext, scene: VisualizationScene) -> dict[str, Any]:
        scene_dict = scene.to_dict()
        tracks = _list(scene_dict.get("tracks"))
        layers = _list(scene_dict.get("layers"))
        issues = list(context.warnings)
        if not tracks:
            issues.append("scene_has_no_tracks")
        if not layers:
            issues.append("scene_has_no_layers")
        known_track_ids = {str(track.get("id")) for track in tracks}
        orphan_layers = [layer.get("id") for layer in layers if str(layer.get("track_id")) not in known_track_ids]
        return {
            "ok": not issues,
            "issues": issues,
            "track_count": len(tracks),
            "layer_count": len(layers),
            "orphan_layer_ids": orphan_layers,
            "renderer_neutral": True,
        }


class VisualizationScenePipeline:
    """Run the renderer-neutral visualization scene pipeline."""

    STAGES = ("domain_model", "context", "scene", "validation")

    def __init__(
        self,
        domain_model_builder: DomainModelBuilder | None = None,
        context_builder: SceneContextBuilder | None = None,
        scene_builder: SceneBuilder | None = None,
        validator: SceneValidator | None = None,
    ) -> None:
        self.domain_model_builder = domain_model_builder or DomainModelBuilder()
        self.context_builder = context_builder or SceneContextBuilder()
        self.scene_builder = scene_builder or SceneBuilder()
        self.validator = validator or SceneValidator()

    def run(self, payload: Mapping[str, Any]) -> VisualizationScenePipelineResult:
        domain_model = self.domain_model_builder.build(payload)
        context = self.context_builder.build(domain_model)
        scene = self.scene_builder.build(context)
        validation = self.validator.validate(context, scene)
        return VisualizationScenePipelineResult(
            domain_model=domain_model,
            context=context,
            scene=scene,
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
