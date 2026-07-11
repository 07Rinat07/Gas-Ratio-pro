"""Shared depth viewport, cursor and selection orchestration for LAS Viewer.

This application-layer service binds one :class:`LasViewerSession` to the
existing render pipeline and interaction overlay engines. Every visible track
therefore consumes the same depth viewport and the same logical cursor and
selection state. UI adapters only submit renderer-neutral commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from services.las_viewer_interaction_overlay import (
    LasViewerInteractionOverlay,
    LasViewerInteractionOverlayEngine,
)
from services.las_viewer_render_pipeline import LasViewerRenderPipeline, LasViewerRenderResult
from services.las_viewer_session import LasViewerSession
from services.visualization_cursor import CursorRequest
from services.visualization_render_model import VisualizationRenderModel
from services.visualization_selection import SelectionCommand
from services.visualization_viewport_controller import ViewportCommand


@dataclass(frozen=True, slots=True)
class LasViewerSharedInteractionResult:
    """One synchronized LAS Viewer render and interaction snapshot."""

    viewer_state: Mapping[str, Any]
    render_result: Mapping[str, Any]
    overlay: LasViewerInteractionOverlay
    render_model: VisualizationRenderModel

    @property
    def ok(self) -> bool:
        return bool(self.render_result.get("ok", False))

    def to_dict(self) -> dict[str, Any]:
        interaction = self.viewer_state.get("interaction") or {}
        viewport = interaction.get("viewport") or {}
        return {
            "schema": "las.viewer.shared-interaction.result",
            "version": "1.0",
            "viewer_state": dict(self.viewer_state),
            "render_result": dict(self.render_result),
            "overlay": self.overlay.to_dict(),
            "render_model": self.render_model.to_dict(),
            "shared_depth_viewport": dict(viewport),
            "visible_tracks": list(self.viewer_state.get("visible_tracks") or ()),
            "ok": self.ok,
            "renderer_neutral": True,
            "raw_dataframe_included": False,
        }


class LasViewerSharedInteractionController:
    """Synchronize one depth viewport, cursor and selection across all tracks."""

    def __init__(
        self,
        payload: Mapping[str, Any],
        viewer: LasViewerSession | None = None,
        *,
        render_pipeline: LasViewerRenderPipeline | None = None,
        overlay_engine: LasViewerInteractionOverlayEngine | None = None,
    ) -> None:
        self._payload = dict(payload)
        self._viewer = viewer or LasViewerSession(payload)
        self._render_pipeline = render_pipeline or LasViewerRenderPipeline()
        self._overlay_engine = overlay_engine or LasViewerInteractionOverlayEngine()

    @property
    def viewer(self) -> LasViewerSession:
        return self._viewer

    def render(self) -> LasViewerSharedInteractionResult:
        """Render visible tracks and append synchronized non-printable overlays."""

        render = self._render_pipeline.run(self._payload, self._viewer)
        model = render.viewport_result.pipeline.render_model
        state = self._viewer.state
        overlay = self._overlay_engine.resolve(
            model,
            state.interaction,
            track_ids=state.visible_tracks,
        )
        combined = overlay.apply_to(model)
        metadata = dict(combined.metadata)
        metadata["las_viewer_shared_interaction"] = {
            "viewport_revision": state.interaction.revision,
            "visible_track_count": len(state.visible_tracks),
            "cursor_active": state.interaction.cursor is not None,
            "selection_count": len(state.interaction.selection.items),
            "renderer_neutral": True,
        }
        combined = VisualizationRenderModel(
            schema=combined.schema,
            version=combined.version,
            width=combined.width,
            height=combined.height,
            clip_regions=combined.clip_regions,
            primitives=combined.primitives,
            diagnostics=combined.diagnostics,
            metadata=metadata,
        )
        return LasViewerSharedInteractionResult(
            viewer_state=state.to_dict(),
            render_result=render.to_dict(),
            overlay=overlay,
            render_model=combined,
        )

    def execute_viewport(self, command: ViewportCommand | Mapping[str, Any]) -> LasViewerSharedInteractionResult:
        resolved = command if isinstance(command, ViewportCommand) else ViewportCommand.from_dict(command)
        self._viewer.interaction_session.execute_viewport(resolved)
        return self.render()

    def update_cursor(self, request: CursorRequest) -> LasViewerSharedInteractionResult:
        base = self._render_pipeline.run(self._payload, self._viewer)
        self._viewer.interaction_session.update_cursor(
            base.viewport_result.pipeline.render_model,
            request,
        )
        return self.render()

    def clear_cursor(self) -> LasViewerSharedInteractionResult:
        self._viewer.interaction_session.clear_cursor()
        return self.render()

    def execute_selection(
        self,
        command: SelectionCommand | Mapping[str, Any],
    ) -> LasViewerSharedInteractionResult:
        self._viewer.interaction_session.execute_selection(command)
        return self.render()
