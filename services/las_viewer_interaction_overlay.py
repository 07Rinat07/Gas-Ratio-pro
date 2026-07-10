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
class LasViewerInteractionOverlayStyle:
    cursor_visible: bool = True
    selection_visible: bool = True
    cursor_color: str = "#202020"
    cursor_width: float = 1.0
    cursor_opacity: float = 1.0
    selection_accent: str = "#ff8a00"
    selection_opacity: float = 1.0

    def __post_init__(self) -> None:
        if not self.cursor_color.strip():
            raise ValueError("cursor_color cannot be empty")
        if not self.selection_accent.strip():
            raise ValueError("selection_accent cannot be empty")
        if self.cursor_width <= 0:
            raise ValueError("cursor_width must be positive")
        if not 0.0 <= self.cursor_opacity <= 1.0:
            raise ValueError("cursor_opacity must be between 0 and 1")
        if not 0.0 <= self.selection_opacity <= 1.0:
            raise ValueError("selection_opacity must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.interaction-overlay-style",
            "version": "1.0",
            "cursor_visible": self.cursor_visible,
            "selection_visible": self.selection_visible,
            "cursor_color": self.cursor_color,
            "cursor_width": self.cursor_width,
            "cursor_opacity": self.cursor_opacity,
            "selection_accent": self.selection_accent,
            "selection_opacity": self.selection_opacity,
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LasViewerInteractionOverlayStyle":
        return cls(
            cursor_visible=bool(data.get("cursor_visible", True)),
            selection_visible=bool(data.get("selection_visible", True)),
            cursor_color=str(data.get("cursor_color", "#202020")),
            cursor_width=float(data.get("cursor_width", 1.0)),
            cursor_opacity=float(data.get("cursor_opacity", 1.0)),
            selection_accent=str(data.get("selection_accent", "#ff8a00")),
            selection_opacity=float(data.get("selection_opacity", 1.0)),
        )


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
        style: LasViewerInteractionOverlayStyle | Mapping[str, Any] | None = None,
    ) -> LasViewerInteractionOverlay:
        resolved_model = model if isinstance(model, VisualizationRenderModel) else VisualizationRenderModel.from_dict(model)
        resolved_interaction = (
            interaction if isinstance(interaction, InteractionSessionState)
            else InteractionSessionState.from_dict(interaction)
        )
        resolved_style = (
            style if isinstance(style, LasViewerInteractionOverlayStyle)
            else LasViewerInteractionOverlayStyle.from_dict(style) if style is not None
            else LasViewerInteractionOverlayStyle(
                cursor_color=cursor_color,
                selection_accent=selection_accent,
            )
        )

        requested = tuple(track_ids or ())
        cursor_sync: LasViewerTrackSynchronization | None = None
        cursor_primitives: tuple[RenderPrimitive, ...] = ()
        diagnostics: list[str] = []

        if resolved_style.cursor_visible and resolved_interaction.cursor is not None:
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
                        "stroke": resolved_style.cursor_color,
                        "stroke_width": resolved_style.cursor_width,
                        "opacity": resolved_style.cursor_opacity,
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
            resolved_interaction.selection if resolved_style.selection_visible else {"items": [], "revision": 0},
            track_ids=requested,
            synchronize_source_layers=synchronize_source_layers,
            accent=resolved_style.selection_accent,
        )
        if resolved_style.selection_opacity != 1.0:
            selection_overlay = LasViewerSelectionOverlay(
                selected_ids=selection_overlay.selected_ids,
                synchronized_primitive_ids=selection_overlay.synchronized_primitive_ids,
                primitives=tuple(
                    RenderPrimitive(
                        id=item.id,
                        kind=item.kind,
                        z_index=item.z_index,
                        payload={**item.payload, "opacity": resolved_style.selection_opacity},
                        track_id=item.track_id,
                        clip_id=item.clip_id,
                        visible=item.visible,
                        printable=item.printable,
                    )
                    for item in selection_overlay.primitives
                ),
                requested_track_ids=selection_overlay.requested_track_ids,
                diagnostics=selection_overlay.diagnostics,
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
