"""Renderer-neutral LAS Viewer render pipeline.

The adapter applies the current LAS Viewer layout and interaction viewport to a
source visualization payload before delegating to ``VisualizationViewportPipeline``.
UI adapters therefore never reorder/filter tracks or curves and never calculate
visible depth geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from services.las_viewer_layout import LasViewerLayoutState
from services.las_viewer_session import LasViewerSession, LasViewerState
from services.visualization_viewport_pipeline import (
    VisualizationViewportPipeline,
    ViewportPipelineResult,
)


def _copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): item for key, item in value.items()}


@dataclass(frozen=True, slots=True)
class LasViewerRenderProfile:
    viewer_revision: int
    layout_revision: int
    source_track_count: int
    rendered_track_count: int
    source_curve_count: int
    rendered_curve_count: int
    active_track_id: str = ""
    active_curve_id: str = ""
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.render.profile",
            "version": "1.0",
            "viewer_revision": self.viewer_revision,
            "layout_revision": self.layout_revision,
            "source_track_count": self.source_track_count,
            "rendered_track_count": self.rendered_track_count,
            "source_curve_count": self.source_curve_count,
            "rendered_curve_count": self.rendered_curve_count,
            "active_track_id": self.active_track_id,
            "active_curve_id": self.active_curve_id,
            "diagnostics": list(self.diagnostics),
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRenderResult:
    viewport_result: ViewportPipelineResult
    profile: LasViewerRenderProfile
    payload: dict[str, Any]

    @property
    def ok(self) -> bool:
        return self.viewport_result.ok and not any(
            item.startswith("las_viewer_render_error:") for item in self.profile.diagnostics
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.render.result",
            "version": "1.0",
            "viewport_result": self.viewport_result.to_dict(),
            "profile": self.profile.to_dict(),
            "payload": dict(self.payload),
            "ok": self.ok,
            "renderer_neutral": True,
        }


class LasViewerRenderPipeline:
    """Apply LAS Viewer state to a visualization payload and build a render model."""

    def __init__(self, viewport_pipeline: VisualizationViewportPipeline | None = None) -> None:
        self.viewport_pipeline = viewport_pipeline or VisualizationViewportPipeline()

    def run(
        self,
        payload: Mapping[str, Any],
        viewer: LasViewerSession | LasViewerState | Mapping[str, Any],
    ) -> LasViewerRenderResult:
        state = self._resolve_state(viewer)
        prepared, profile = self.prepare_payload(payload, state)
        viewport_result = self.viewport_pipeline.run(prepared, state.interaction.viewport)
        viewport_result.pipeline.validation["las_viewer_revision"] = state.revision
        viewport_result.pipeline.validation["las_viewer_layout_revision"] = (
            state.layout.revision if state.layout is not None else 0
        )
        viewport_result.pipeline.validation["las_viewer_active_track_id"] = state.active_track_id
        viewport_result.pipeline.validation["las_viewer_active_curve_id"] = state.active_curve_id
        return LasViewerRenderResult(viewport_result, profile, prepared)

    @staticmethod
    def _resolve_state(
        viewer: LasViewerSession | LasViewerState | Mapping[str, Any],
    ) -> LasViewerState:
        if isinstance(viewer, LasViewerSession):
            return viewer.state
        if isinstance(viewer, LasViewerState):
            return viewer
        return LasViewerState.from_dict(viewer)

    @staticmethod
    def prepare_payload(
        payload: Mapping[str, Any],
        state: LasViewerState,
    ) -> tuple[dict[str, Any], LasViewerRenderProfile]:
        prepared = _copy_mapping(payload)
        tracks = [
            _copy_mapping(item)
            for item in (payload.get("tracks") or ())
            if isinstance(item, Mapping)
        ]
        curves = [
            _copy_mapping(item)
            for item in (payload.get("curves") or ())
            if isinstance(item, Mapping)
        ]
        layout = state.layout or LasViewerLayoutState(())
        layout_by_track = {item.track_id: item for item in layout.tracks}
        source_tracks = {str(item.get("id") or "").strip(): item for item in tracks}
        source_curves: dict[str, list[dict[str, Any]]] = {}
        for curve in curves:
            track_id = str(curve.get("track_id") or "").strip()
            source_curves.setdefault(track_id, []).append(curve)

        diagnostics: list[str] = []
        rendered_tracks: list[dict[str, Any]] = []
        rendered_curves: list[dict[str, Any]] = []
        visible_track_set = set(state.visible_tracks)
        visible_curve_set = set(state.visible_curves)
        if layout.tracks:
            visible_curve_set.intersection_update(layout.visible_curves)

        order = layout.track_order or state.visible_tracks
        for track_id in order:
            if track_id not in visible_track_set:
                continue
            source_track = source_tracks.get(track_id)
            if source_track is None:
                diagnostics.append(f"las_viewer_render_missing_track:{track_id}")
                continue
            layout_track = layout_by_track.get(track_id)
            track = dict(source_track)
            if layout_track is not None:
                track["width"] = layout_track.width
                track_axis = dict(track.get("axis") or {})
                track_axis.update({key: value for key, value in layout_track.scale.items() if value is not None})
                track["axis"] = track_axis
            track["visible"] = True
            track["order"] = len(rendered_tracks)
            rendered_tracks.append(track)

            curve_items = source_curves.get(track_id, [])
            curve_by_id = {
                str(item.get("mnemonic") or item.get("id") or "").strip(): item
                for item in curve_items
            }
            curve_order = (
                layout_track.curve_order if layout_track is not None else tuple(curve_by_id)
            )
            for curve_id in curve_order:
                if curve_id not in visible_curve_set:
                    continue
                source_curve = curve_by_id.get(curve_id)
                if source_curve is None:
                    diagnostics.append(f"las_viewer_render_missing_curve:{curve_id}")
                    continue
                curve = dict(source_curve)
                if layout_track is not None:
                    curve_axis = dict(curve.get("axis") or {})
                    curve_axis.update({key: value for key, value in layout_track.scale.items() if value is not None})
                    curve["axis"] = curve_axis
                curve["visible"] = True
                curve["order"] = len(rendered_curves)
                rendered_curves.append(curve)

        prepared["tracks"] = rendered_tracks
        prepared["curves"] = rendered_curves
        prepared["visible_tracks"] = [str(item.get("id") or "") for item in rendered_tracks]
        prepared["las_viewer"] = {
            "revision": state.revision,
            "layout_revision": layout.revision,
            "active_track_id": state.active_track_id,
            "active_curve_id": state.active_curve_id,
            "track_order": list(layout.track_order),
            "visible_tracks": list(state.visible_tracks),
            "visible_curves": list(state.visible_curves),
        }

        profile = LasViewerRenderProfile(
            viewer_revision=state.revision,
            layout_revision=layout.revision,
            source_track_count=len(tracks),
            rendered_track_count=len(rendered_tracks),
            source_curve_count=len(curves),
            rendered_curve_count=len(rendered_curves),
            active_track_id=state.active_track_id,
            active_curve_id=state.active_curve_id,
            diagnostics=tuple(diagnostics),
        )
        return prepared, profile
