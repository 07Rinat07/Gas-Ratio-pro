"""Unified renderer-neutral LAS Viewer track configuration.

Coordinates order, width, scale and visibility through the existing viewer
session and layout controller so UI adapters never duplicate invariants.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from services.las_viewer_session import LasViewerSession, LasViewerState


@dataclass(frozen=True, slots=True)
class LasViewerTrackConfigurationResult:
    state: LasViewerState
    changed_track_id: str
    operation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.track-configuration.result",
            "version": "1.0",
            "operation": self.operation,
            "changed_track_id": self.changed_track_id,
            "state": self.state.to_dict(),
            "renderer_neutral": True,
        }


class LasViewerTrackConfigurationController:
    """Apply track configuration atomically to one LAS Viewer session."""

    def __init__(self, viewer: LasViewerSession) -> None:
        self.viewer = viewer

    @classmethod
    def from_state(cls, state: LasViewerState | Mapping[str, Any]) -> "LasViewerTrackConfigurationController":
        return cls(LasViewerSession.from_state(state))

    def move(self, track_id: str, target_index: int) -> LasViewerTrackConfigurationResult:
        self.viewer.layout_controller.move_track(track_id, target_index)
        return self._result(track_id, "move")

    def set_width(self, track_id: str, width: float) -> LasViewerTrackConfigurationResult:
        self.viewer.layout_controller.set_track_width(track_id, width)
        return self._result(track_id, "set_width")

    def set_scale(
        self,
        track_id: str,
        *,
        scale_type: str = "linear",
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> LasViewerTrackConfigurationResult:
        self.viewer.layout_controller.set_track_scale(
            track_id,
            scale_type=scale_type,
            minimum=minimum,
            maximum=maximum,
        )
        return self._result(track_id, "set_scale")

    def set_visible(self, track_id: str, visible: bool) -> LasViewerTrackConfigurationResult:
        # Keep session visibility, active object invariants and layout visibility synchronized.
        self.viewer.set_track_visible(track_id, visible)
        self.viewer.layout_controller.set_track_visible(track_id, visible)
        return self._result(track_id, "set_visible")

    def _result(self, track_id: str, operation: str) -> LasViewerTrackConfigurationResult:
        return LasViewerTrackConfigurationResult(self.viewer.state, str(track_id), operation)
