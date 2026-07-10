"""Renderer-neutral cursor readout built on viewport and hit-testing services."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping

from services.visualization_hit_testing import HitTestQuery, HitTestResult, VisualizationHitTestingEngine
from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_render_model import VisualizationRenderModel
from services.visualization_spatial_index import VisualizationSpatialIndex


@dataclass(frozen=True, slots=True)
class CursorRequest:
    x: float
    y: float
    tolerance: float = 6.0
    track_id: str = ""
    max_results: int = 8
    clamp_depth: bool = True

    @property
    def valid(self) -> bool:
        return (
            isfinite(self.x)
            and isfinite(self.y)
            and isfinite(self.tolerance)
            and self.tolerance >= 0
            and self.max_results > 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.cursor-request",
            "version": "1.0",
            "x": self.x,
            "y": self.y,
            "tolerance": self.tolerance,
            "track_id": self.track_id,
            "max_results": self.max_results,
            "clamp_depth": self.clamp_depth,
            "valid": self.valid,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class CursorReadout:
    screen_x: float
    screen_y: float
    depth: float
    depth_unit: str = ""
    track_id: str = ""
    hits: tuple[HitTestResult, ...] = field(default_factory=tuple)
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def nearest(self) -> HitTestResult | None:
        return self.hits[0] if self.hits else None

    @property
    def hit(self) -> bool:
        return bool(self.hits)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.cursor-readout",
            "version": "1.0",
            "screen_x": self.screen_x,
            "screen_y": self.screen_y,
            "depth": self.depth,
            "depth_unit": self.depth_unit,
            "track_id": self.track_id,
            "hits": [item.to_dict() for item in self.hits],
            "hit": self.hit,
            "nearest": self.nearest.to_dict() if self.nearest is not None else None,
            "diagnostics": list(self.diagnostics),
            "renderer_neutral": True,
        }


class VisualizationCursorEngine:
    """Resolve depth and nearby render primitives for a screen cursor."""

    def __init__(self, hit_testing_engine: VisualizationHitTestingEngine | None = None) -> None:
        self.hit_testing_engine = hit_testing_engine or VisualizationHitTestingEngine()

    def resolve(
        self,
        model: VisualizationRenderModel | Mapping[str, Any],
        viewport: InteractiveViewport | Mapping[str, Any],
        request: CursorRequest,
        *,
        spatial_index: VisualizationSpatialIndex | None = None,
    ) -> CursorReadout:
        if not request.valid:
            raise ValueError("cursor request is invalid")

        resolved_viewport = (
            viewport if isinstance(viewport, InteractiveViewport)
            else InteractiveViewport.from_dict(viewport)
        )
        if not resolved_viewport.valid:
            raise ValueError("viewport is invalid")

        depth = resolved_viewport.screen_to_domain(request.y, clamp=request.clamp_depth)
        response = self.hit_testing_engine.hit_test(
            model,
            HitTestQuery(
                x=request.x,
                y=request.y,
                tolerance=request.tolerance,
                track_id=request.track_id,
                max_results=request.max_results,
            ),
            spatial_index=spatial_index,
        )
        diagnostics = list(response.diagnostics)
        if not resolved_viewport.contains_screen(request.y):
            diagnostics.append("cursor_outside_viewport")

        return CursorReadout(
            screen_x=request.x,
            screen_y=request.y,
            depth=depth,
            depth_unit=resolved_viewport.unit,
            track_id=request.track_id,
            hits=response.results,
            diagnostics=tuple(dict.fromkeys(diagnostics)),
        )
