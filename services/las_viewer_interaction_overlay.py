"""Unified renderer-neutral LAS Viewer interaction overlays.

The service composes synchronized depth-cursor and selection overlays without
placing geometry calculations in UI adapters. Resulting primitives are
non-printable and can be appended to any render backend contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from services.las_viewer_selection_synchronization import (
    LasViewerSelectionOverlay,
    LasViewerSelectionSynchronizationEngine,
)
from services.las_viewer_track_synchronization import (
    LasViewerTrackSynchronization,
    LasViewerTrackSynchronizationEngine,
)
from services.visualization_interaction_session import InteractionSessionState
from services.visualization_render_model import RenderPrimitive, VisualizationRenderModel


@dataclass(frozen=True, slots=True)
class LasViewerInteractionOverlay:
    cursor: LasViewerTrackSynchronization | None
    selection: LasViewerSelectionOverlay
    primitives: tuple[RenderPrimitive, ...]
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def empty(self) -> bool:
        return not self.primitives

    def apply_to(self, model: VisualizationRenderModel | Mapping[str, Any]) -> VisualizationRenderModel:
        resolved = model if isinstance(model, VisualizationRenderModel) else VisualizationRenderModel.from_dict(model)
        metadata = dict(resolved.metadata)
        metadata["las_viewer_interaction_overlay"] = {
            "cursor": self.cursor is not None,
            "selection_count": len(self.selection.primitives),
            "primitive_count": len(self.primitives),
        }
        return VisualizationRenderModel(
            schema=resolved.schema,
            version=resolved.version,
            width=resolved.width,
            height=resolved.height,
            clip_regions=resolved.clip_regions,
            primitives=(*resolved.primitives, *self.primitives),
            diagnostics=tuple(dict.fromkeys((*resolved.diagnostics, *self.diagnostics))),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.interaction-overlay",
            "version": "1.0",
            "cursor": self.cursor.to_dict() if self.cursor is not None else None,
            "selection": self.selection.to_dict(),
            "primitives": [item.to_dict() for item in self.primitives],
            "diagnostics": list(self.diagnostics),
            "empty": self.empty,
            "renderer_neutral": True,
        }


class LasViewerInteractionOverlayEngine:
    """Compose synchronized cursor and selection overlays for LAS Viewer."""

    CURSOR_Z = 900

    def __init__(
        self,
        track_engine: LasViewerTrackSynchronizationEngine | None = None,
        selection_engine: LasViewerSelectionSynchronizationEngine | None = None,
    ) -> None:
        self.track_engine = track_engine or LasViewerTrackSynchronizationEngine()
        self.selection_engine = selection_engine or LasViewerSelectionSynchronizationEngine()

    def resolve(
        self,
        model: VisualizationRenderModel | Mapping[str, Any],
        interaction: InteractionSessionState | Mapping[str, Any],
        *,
        track_ids: Iterable[str] | None = None,
        cursor_color: str = "#202020",
        selection_accent: str = "#ff8a00",
        synchronize_source_layers: bool = True,
    ) -> LasViewerInteractionOverlay:
        resolved_model = model if isinstance(model, VisualizationRenderModel) else VisualizationRenderModel.from_dict(model)
        resolved_interaction = (
            interaction if isinstance(interaction, InteractionSessionState)
            else InteractionSessionState.from_dict(interaction)
        )
        if not cursor_color.strip():
            raise ValueError("cursor_color cannot be empty")

        requested = tuple(track_ids or ())
        cursor_sync: LasViewerTrackSynchronization | None = None
        cursor_primitives: tuple[RenderPrimitive, ...] = ()
        diagnostics: list[str] = []

        if resolved_interaction.cursor is not None:
            cursor_sync = self.track_engine.resolve(
                resolved_model,
                resolved_interaction.viewport,
                resolved_interaction.cursor.screen_y,
                track_ids=requested,
            )
            diagnostics.extend(cursor_sync.diagnostics)
            cursor_primitives = tuple(
                RenderPrimitive(
                    id=f"cursor.{segment.track_id}",
                    kind="line",
                    z_index=self.CURSOR_Z,
                    track_id=segment.track_id,
                    clip_id=segment.clip_id,
                    visible=segment.visible,
                    printable=False,
                    payload={
                        "x1": segment.x_start,
                        "y1": segment.screen_y,
                        "x2": segment.x_stop,
                        "y2": segment.screen_y,
                        "stroke": cursor_color,
                        "stroke_width": 1.0,
                        "depth": cursor_sync.depth,
                        "depth_unit": cursor_sync.depth_unit,
                        "cursor_overlay": True,
                    },
                )
                for segment in cursor_sync.segments
                if segment.visible
            )

        selection_overlay = self.selection_engine.resolve(
            resolved_model,
            resolved_interaction.selection,
            track_ids=requested,
            synchronize_source_layers=synchronize_source_layers,
            accent=selection_accent,
        )
        diagnostics.extend(selection_overlay.diagnostics)

        primitives = tuple(sorted(
            (*selection_overlay.primitives, *cursor_primitives),
            key=lambda item: (item.z_index, item.track_id, item.id),
        ))
        return LasViewerInteractionOverlay(
            cursor=cursor_sync,
            selection=selection_overlay,
            primitives=primitives,
            diagnostics=tuple(dict.fromkeys(diagnostics)),
        )
