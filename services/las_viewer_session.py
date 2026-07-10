"""Renderer-neutral LAS Viewer session state.

The module is the first application-layer contract for the dedicated LAS Viewer.
It composes LAS payload metadata with the existing interaction session while
keeping track/curve visibility and active-object rules outside UI adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from services.visualization_interaction_session import (
    InteractionSessionState,
    VisualizationInteractionSession,
)
from services.visualization_interactive_viewport import InteractiveViewport, ViewportLimits


def _clean_ids(values: Iterable[Any]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)


def _range_value(value: Any, fallback: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return fallback
    return result


@dataclass(frozen=True, slots=True)
class LasViewerState:
    project_id: str
    las_id: str
    interaction: InteractionSessionState
    available_tracks: tuple[str, ...]
    available_curves: tuple[str, ...]
    visible_tracks: tuple[str, ...]
    visible_curves: tuple[str, ...]
    active_track_id: str = ""
    active_curve_id: str = ""
    revision: int = 0

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LasViewerState":
        interaction = value.get("interaction")
        if not isinstance(interaction, Mapping):
            raise ValueError("LAS viewer state requires interaction state")
        return cls(
            project_id=str(value.get("project_id") or "").strip(),
            las_id=str(value.get("las_id") or "").strip(),
            interaction=InteractionSessionState.from_dict(interaction),
            available_tracks=_clean_ids(value.get("available_tracks") or ()),
            available_curves=_clean_ids(value.get("available_curves") or ()),
            visible_tracks=_clean_ids(value.get("visible_tracks") or ()),
            visible_curves=_clean_ids(value.get("visible_curves") or ()),
            active_track_id=str(value.get("active_track_id") or "").strip(),
            active_curve_id=str(value.get("active_curve_id") or "").strip(),
            revision=max(0, int(value.get("revision") or 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.state",
            "version": "1.0",
            "project_id": self.project_id,
            "las_id": self.las_id,
            "interaction": self.interaction.to_dict(),
            "available_tracks": list(self.available_tracks),
            "available_curves": list(self.available_curves),
            "visible_tracks": list(self.visible_tracks),
            "visible_curves": list(self.visible_curves),
            "active_track_id": self.active_track_id,
            "active_curve_id": self.active_curve_id,
            "revision": self.revision,
            "renderer_neutral": True,
        }


class LasViewerSession:
    """Own LAS Viewer state and enforce visibility/activation invariants."""

    def __init__(
        self,
        payload: Mapping[str, Any],
        *,
        screen_start: float = 0.0,
        screen_stop: float = 1000.0,
        history_limit: int = 100,
    ) -> None:
        project_id = str(payload.get("project_id") or "").strip()
        las_id = str(payload.get("las_id") or "").strip()
        if not las_id:
            raise ValueError("LAS viewer payload requires las_id")

        tracks = tuple(item for item in (payload.get("tracks") or ()) if isinstance(item, Mapping))
        curves = tuple(item for item in (payload.get("curves") or ()) if isinstance(item, Mapping))
        available_tracks = _clean_ids(item.get("id") for item in tracks)
        available_curves = _clean_ids(item.get("mnemonic") for item in curves)

        requested_tracks = _clean_ids(payload.get("visible_tracks") or available_tracks)
        visible_tracks = tuple(item for item in requested_tracks if item in available_tracks)
        visible_curves = tuple(
            str(item.get("mnemonic") or "").strip()
            for item in curves
            if str(item.get("mnemonic") or "").strip()
            and str(item.get("track_id") or "").strip() in visible_tracks
        )

        depth_range = payload.get("depth_range") if isinstance(payload.get("depth_range"), Mapping) else {}
        start = _range_value(depth_range.get("start"), 0.0)
        stop = _range_value(depth_range.get("stop"), start + 1.0)
        if stop <= start:
            stop = start + 1.0
        unit = str(payload.get("depth_unit") or "")
        viewport = InteractiveViewport(
            start,
            stop,
            float(screen_start),
            float(screen_stop),
            inverted=True,
            unit=unit,
            limits=ViewportLimits(minimum=start, maximum=stop),
        )
        self._interaction = VisualizationInteractionSession(viewport, history_limit=history_limit)
        self._project_id = project_id
        self._las_id = las_id
        self._available_tracks = available_tracks
        self._available_curves = available_curves
        self._curve_tracks = {
            str(item.get("mnemonic") or "").strip(): str(item.get("track_id") or "").strip()
            for item in curves
            if str(item.get("mnemonic") or "").strip()
        }
        self._visible_tracks = visible_tracks
        self._visible_curves = _clean_ids(visible_curves)
        self._active_track_id = visible_tracks[0] if visible_tracks else ""
        self._active_curve_id = self._first_curve_for_track(self._active_track_id)
        self._revision = 0

    @classmethod
    def from_state(cls, state: LasViewerState | Mapping[str, Any]) -> "LasViewerSession":
        resolved = state if isinstance(state, LasViewerState) else LasViewerState.from_dict(state)
        payload = {
            "project_id": resolved.project_id,
            "las_id": resolved.las_id,
            "depth_unit": resolved.interaction.viewport.unit,
            "depth_range": {
                "start": resolved.interaction.viewport.limits.minimum
                if resolved.interaction.viewport.limits.minimum is not None
                else resolved.interaction.viewport.domain_start,
                "stop": resolved.interaction.viewport.limits.maximum
                if resolved.interaction.viewport.limits.maximum is not None
                else resolved.interaction.viewport.domain_stop,
            },
            "tracks": [{"id": item} for item in resolved.available_tracks],
            "curves": [
                {"mnemonic": item, "track_id": resolved.active_track_id if item == resolved.active_curve_id else ""}
                for item in resolved.available_curves
            ],
            "visible_tracks": list(resolved.visible_tracks),
        }
        session = cls(payload)
        session._interaction = VisualizationInteractionSession.from_state(resolved.interaction)
        session._visible_curves = resolved.visible_curves
        session._active_track_id = resolved.active_track_id if resolved.active_track_id in resolved.visible_tracks else ""
        session._active_curve_id = resolved.active_curve_id if resolved.active_curve_id in resolved.visible_curves else ""
        session._revision = resolved.revision
        return session

    @property
    def interaction_session(self) -> VisualizationInteractionSession:
        return self._interaction

    @property
    def state(self) -> LasViewerState:
        return LasViewerState(
            project_id=self._project_id,
            las_id=self._las_id,
            interaction=self._interaction.state,
            available_tracks=self._available_tracks,
            available_curves=self._available_curves,
            visible_tracks=self._visible_tracks,
            visible_curves=self._visible_curves,
            active_track_id=self._active_track_id,
            active_curve_id=self._active_curve_id,
            revision=self._revision + self._interaction.state.revision,
        )

    def set_track_visible(self, track_id: str, visible: bool) -> LasViewerState:
        track = str(track_id or "").strip()
        if track not in self._available_tracks:
            raise ValueError(f"unknown LAS track: {track}")
        before = self._visible_tracks
        if visible:
            self._visible_tracks = _clean_ids((*self._visible_tracks, track))
        else:
            self._visible_tracks = tuple(item for item in self._visible_tracks if item != track)
        self._visible_curves = tuple(
            curve for curve in self._available_curves if self._curve_tracks.get(curve) in self._visible_tracks
        )
        if self._active_track_id not in self._visible_tracks:
            self._active_track_id = self._visible_tracks[0] if self._visible_tracks else ""
        if self._active_curve_id not in self._visible_curves:
            self._active_curve_id = self._first_curve_for_track(self._active_track_id)
        if self._visible_tracks != before:
            self._revision += 1
        return self.state

    def activate_track(self, track_id: str) -> LasViewerState:
        track = str(track_id or "").strip()
        if track not in self._visible_tracks:
            raise ValueError("active track must be visible")
        if track != self._active_track_id:
            self._active_track_id = track
            self._active_curve_id = self._first_curve_for_track(track)
            self._revision += 1
        return self.state

    def activate_curve(self, curve_id: str) -> LasViewerState:
        curve = str(curve_id or "").strip()
        if curve not in self._visible_curves:
            raise ValueError("active curve must be visible")
        track = self._curve_tracks.get(curve, "")
        changed = curve != self._active_curve_id or track != self._active_track_id
        self._active_curve_id = curve
        self._active_track_id = track
        if changed:
            self._revision += 1
        return self.state

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.session",
            "version": "1.0",
            "state": self.state.to_dict(),
            "interaction": self._interaction.snapshot(),
            "renderer_neutral": True,
        }

    def _first_curve_for_track(self, track_id: str) -> str:
        return next(
            (curve for curve in self._visible_curves if self._curve_tracks.get(curve) == track_id),
            "",
        )
