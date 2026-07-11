"""Renderer-neutral LAS Viewer navigation workflow.

The service exposes product-level zoom, pan, fit and reset operations while
reusing the existing shared interaction controller. It also returns compact
performance telemetry so UI adapters can verify that large-LAS navigation uses
viewport filtering, downsampling and the bounded viewport cache without storing
raw dataframes in session state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from services.las_viewer_shared_interaction import (
    LasViewerSharedInteractionController,
    LasViewerSharedInteractionResult,
)
from services.visualization_viewport_controller import ViewportCommand


@dataclass(frozen=True, slots=True)
class LasViewerNavigationProfile:
    operation: str
    source_point_count: int
    visible_point_count: int
    rendered_primitive_count: int
    cache_hit: bool
    cache_entries: int
    viewport_start: float
    viewport_stop: float

    @property
    def stable_large_las(self) -> bool:
        return (
            self.source_point_count >= self.visible_point_count >= 0
            and self.cache_entries >= 0
            and self.viewport_stop > self.viewport_start
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.navigation.profile",
            "version": "1.0",
            "operation": self.operation,
            "source_point_count": self.source_point_count,
            "visible_point_count": self.visible_point_count,
            "rendered_primitive_count": self.rendered_primitive_count,
            "cache_hit": self.cache_hit,
            "cache_entries": self.cache_entries,
            "viewport_start": self.viewport_start,
            "viewport_stop": self.viewport_stop,
            "stable_large_las": self.stable_large_las,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerNavigationResult:
    interaction: LasViewerSharedInteractionResult
    profile: LasViewerNavigationProfile

    @property
    def ok(self) -> bool:
        return self.interaction.ok and self.profile.stable_large_las

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.navigation.result",
            "version": "1.0",
            "interaction": self.interaction.to_dict(),
            "profile": self.profile.to_dict(),
            "ok": self.ok,
            "renderer_neutral": True,
            "raw_dataframe_included": False,
        }


class LasViewerNavigationController:
    """Product-level navigation API over the shared LAS Viewer viewport."""

    def __init__(
        self,
        payload: Mapping[str, Any],
        *,
        interaction_controller: LasViewerSharedInteractionController | None = None,
    ) -> None:
        self._payload = dict(payload)
        self._interaction = interaction_controller or LasViewerSharedInteractionController(payload)
        depth_range = payload.get("depth_range") or {}
        self._source_start = float(depth_range.get("start"))
        self._source_stop = float(depth_range.get("stop"))
        if self._source_stop <= self._source_start:
            raise ValueError("LAS Viewer navigation requires an increasing depth range")

    @property
    def interaction_controller(self) -> LasViewerSharedInteractionController:
        return self._interaction

    def render(self) -> LasViewerNavigationResult:
        return self._result("render", self._interaction.render())

    def zoom(self, factor: float, *, anchor_depth: float | None = None) -> LasViewerNavigationResult:
        command = ViewportCommand.zoom(factor, anchor_domain=anchor_depth, source="las-viewer.navigation")
        return self._result("zoom", self._interaction.execute_viewport(command))

    def zoom_at_screen(self, factor: float, screen_coordinate: float) -> LasViewerNavigationResult:
        command = ViewportCommand.zoom_at_screen(
            factor,
            screen_coordinate,
            source="las-viewer.navigation",
        )
        return self._result("zoom_at_screen", self._interaction.execute_viewport(command))

    def pan_depth(self, delta: float) -> LasViewerNavigationResult:
        command = ViewportCommand.pan_domain(delta, source="las-viewer.navigation")
        return self._result("pan", self._interaction.execute_viewport(command))

    def pan_pixels(self, delta_pixels: float) -> LasViewerNavigationResult:
        command = ViewportCommand.pan_pixels(delta_pixels, source="las-viewer.navigation")
        return self._result("pan_pixels", self._interaction.execute_viewport(command))

    def fit(self, depth_start: float | None = None, depth_stop: float | None = None) -> LasViewerNavigationResult:
        start = self._source_start if depth_start is None else float(depth_start)
        stop = self._source_stop if depth_stop is None else float(depth_stop)
        command = ViewportCommand.fit(start, stop, source="las-viewer.navigation")
        return self._result("fit", self._interaction.execute_viewport(command))

    def reset(self) -> LasViewerNavigationResult:
        command = ViewportCommand.reset(source="las-viewer.navigation")
        return self._result("reset", self._interaction.execute_viewport(command))

    def _result(
        self,
        operation: str,
        interaction: LasViewerSharedInteractionResult,
    ) -> LasViewerNavigationResult:
        viewport_result = interaction.render_result["viewport_result"]
        profile = viewport_result["profile"]
        viewport = interaction.viewer_state["interaction"]["viewport"]
        navigation_profile = LasViewerNavigationProfile(
            operation=operation,
            source_point_count=int(profile.get("source_point_count") or 0),
            visible_point_count=int(profile.get("visible_point_count") or 0),
            rendered_primitive_count=len(interaction.render_model.primitives),
            cache_hit=bool(profile.get("cache_hit", False)),
            cache_entries=int(profile.get("cache_entries") or 0),
            viewport_start=float(viewport["domain_start"]),
            viewport_stop=float(viewport["domain_stop"]),
        )
        return LasViewerNavigationResult(interaction, navigation_profile)
