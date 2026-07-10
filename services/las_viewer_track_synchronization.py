"""Renderer-neutral synchronization of LAS Viewer tracks.

The service projects one shared depth cursor across all visible track plot
regions.  UI adapters receive ready-to-render horizontal cursor segments and
never calculate depth or track geometry themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Iterable, Mapping

from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_render_model import RenderClipRegion, VisualizationRenderModel


def _clean_ids(values: Iterable[Any]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class LasViewerTrackCursorSegment:
    track_id: str
    clip_id: str
    x_start: float
    x_stop: float
    screen_y: float
    visible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "clip_id": self.clip_id,
            "x_start": self.x_start,
            "x_stop": self.x_stop,
            "screen_y": self.screen_y,
            "visible": self.visible,
        }


@dataclass(frozen=True, slots=True)
class LasViewerTrackSynchronization:
    depth: float
    depth_unit: str
    screen_y: float
    segments: tuple[LasViewerTrackCursorSegment, ...]
    requested_track_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def synchronized_track_ids(self) -> tuple[str, ...]:
        return tuple(item.track_id for item in self.segments if item.visible)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.track-synchronization",
            "version": "1.0",
            "depth": self.depth,
            "depth_unit": self.depth_unit,
            "screen_y": self.screen_y,
            "segments": [item.to_dict() for item in self.segments],
            "requested_track_ids": list(self.requested_track_ids),
            "synchronized_track_ids": list(self.synchronized_track_ids),
            "diagnostics": list(self.diagnostics),
            "renderer_neutral": True,
        }


class LasViewerTrackSynchronizationEngine:
    """Create shared depth-cursor segments for LAS track plot regions."""

    def resolve(
        self,
        model: VisualizationRenderModel | Mapping[str, Any],
        viewport: InteractiveViewport | Mapping[str, Any],
        screen_y: float,
        *,
        track_ids: Iterable[str] | None = None,
        clamp: bool = True,
    ) -> LasViewerTrackSynchronization:
        if not isfinite(float(screen_y)):
            raise ValueError("screen_y must be finite")
        resolved_model = model if isinstance(model, VisualizationRenderModel) else VisualizationRenderModel.from_dict(model)
        resolved_viewport = viewport if isinstance(viewport, InteractiveViewport) else InteractiveViewport.from_dict(viewport)
        if not resolved_viewport.valid:
            raise ValueError("viewport is invalid")

        requested = _clean_ids(track_ids or ())
        requested_set = set(requested)
        regions = self._track_regions(resolved_model.clip_regions)
        if requested:
            ordered_ids = requested
        else:
            ordered_ids = tuple(regions)

        y = float(screen_y)
        diagnostics: list[str] = []
        if not resolved_viewport.contains_screen(y):
            diagnostics.append("track_sync_cursor_outside_viewport")
        depth = resolved_viewport.screen_to_domain(y, clamp=clamp)

        segments: list[LasViewerTrackCursorSegment] = []
        reference_geometry: tuple[float, float] | None = None
        for track_id in ordered_ids:
            region = regions.get(track_id)
            if region is None:
                diagnostics.append(f"track_sync_missing_region:{track_id}")
                continue
            if reference_geometry is None:
                reference_geometry = (region.y, region.height)
            elif reference_geometry != (region.y, region.height):
                diagnostics.append(f"track_sync_plot_geometry_mismatch:{track_id}")
            visible = region.y <= y <= region.y + region.height
            segments.append(
                LasViewerTrackCursorSegment(
                    track_id=track_id,
                    clip_id=region.id,
                    x_start=region.x,
                    x_stop=region.x + region.width,
                    screen_y=y,
                    visible=visible,
                )
            )

        if requested_set:
            unknown = requested_set.difference(regions)
            for track_id in sorted(unknown):
                marker = f"track_sync_missing_region:{track_id}"
                if marker not in diagnostics:
                    diagnostics.append(marker)

        return LasViewerTrackSynchronization(
            depth=depth,
            depth_unit=resolved_viewport.unit,
            screen_y=y,
            segments=tuple(segments),
            requested_track_ids=requested,
            diagnostics=tuple(dict.fromkeys(diagnostics)),
        )

    @staticmethod
    def _track_regions(regions: tuple[RenderClipRegion, ...]) -> dict[str, RenderClipRegion]:
        result: dict[str, RenderClipRegion] = {}
        for region in regions:
            prefix = "clip."
            suffix = ".plot"
            if not region.id.startswith(prefix) or not region.id.endswith(suffix):
                continue
            track_id = region.id[len(prefix):-len(suffix)]
            if track_id and track_id not in result:
                result[track_id] = region
        return result
