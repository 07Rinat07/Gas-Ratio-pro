"""Renderer-neutral LAS Viewer track layout state.

The module owns track order, normalized width weights and per-track curve
visibility. UI adapters only issue layout operations and render the resulting
serializable state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


def _clean_ids(values: Iterable[Any]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)



def _scale(value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = dict(value or {})
    scale_type = str(source.get("scale_type") or source.get("scale") or "linear").strip().lower()
    if scale_type not in {"linear", "log"}:
        raise ValueError("track scale_type must be linear or log")
    minimum = source.get("minimum", source.get("min_value"))
    maximum = source.get("maximum", source.get("max_value"))
    if minimum is not None:
        minimum = float(minimum)
    if maximum is not None:
        maximum = float(maximum)
    if minimum is not None and maximum is not None and maximum <= minimum:
        raise ValueError("track scale maximum must be greater than minimum")
    if scale_type == "log" and minimum is not None and minimum <= 0:
        raise ValueError("log scale minimum must be positive")
    return {"scale_type": scale_type, "minimum": minimum, "maximum": maximum}

def _positive_width(value: Any, fallback: float = 1.0) -> float:
    try:
        width = float(value)
    except (TypeError, ValueError):
        return fallback
    if width <= 0.0:
        raise ValueError("track width must be positive")
    return width


@dataclass(frozen=True, slots=True)
class LasViewerTrackLayout:
    track_id: str
    width: float = 1.0
    visible: bool = True
    curve_order: tuple[str, ...] = ()
    visible_curves: tuple[str, ...] = ()
    scale: dict[str, Any] = field(default_factory=_scale)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LasViewerTrackLayout":
        track_id = str(value.get("track_id") or value.get("id") or "").strip()
        if not track_id:
            raise ValueError("track layout requires track_id")
        curve_order = _clean_ids(value.get("curve_order") or ())
        requested_visible = _clean_ids(value.get("visible_curves") or curve_order)
        return cls(
            track_id=track_id,
            width=_positive_width(value.get("width"), 1.0),
            visible=bool(value.get("visible", True)),
            curve_order=curve_order,
            visible_curves=tuple(item for item in requested_visible if item in curve_order),
            scale=_scale(value.get("scale") if isinstance(value.get("scale"), Mapping) else value.get("axis") if isinstance(value.get("axis"), Mapping) else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "width": self.width,
            "visible": self.visible,
            "curve_order": list(self.curve_order),
            "visible_curves": list(self.visible_curves),
            "scale": dict(self.scale),
        }


@dataclass(frozen=True, slots=True)
class LasViewerLayoutState:
    tracks: tuple[LasViewerTrackLayout, ...]
    revision: int = 0

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LasViewerLayoutState":
        tracks = tuple(
            LasViewerTrackLayout.from_dict(item)
            for item in (value.get("tracks") or ())
            if isinstance(item, Mapping)
        )
        return cls(tracks=tracks, revision=max(0, int(value.get("revision") or 0)))

    @property
    def track_order(self) -> tuple[str, ...]:
        return tuple(item.track_id for item in self.tracks)

    @property
    def visible_tracks(self) -> tuple[str, ...]:
        return tuple(item.track_id for item in self.tracks if item.visible)

    @property
    def visible_curves(self) -> tuple[str, ...]:
        return tuple(
            curve
            for item in self.tracks
            if item.visible
            for curve in item.visible_curves
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.layout",
            "version": "1.0",
            "tracks": [item.to_dict() for item in self.tracks],
            "track_order": list(self.track_order),
            "visible_tracks": list(self.visible_tracks),
            "visible_curves": list(self.visible_curves),
            "revision": self.revision,
            "renderer_neutral": True,
        }


class LasViewerLayoutController:
    """Mutate LAS Viewer layout while preserving deterministic invariants."""

    def __init__(self, state: LasViewerLayoutState) -> None:
        ids = state.track_order
        if len(ids) != len(set(ids)):
            raise ValueError("track layout ids must be unique")
        self._tracks = list(state.tracks)
        self._revision = state.revision

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "LasViewerLayoutController":
        tracks = tuple(item for item in (payload.get("tracks") or ()) if isinstance(item, Mapping))
        curves = tuple(item for item in (payload.get("curves") or ()) if isinstance(item, Mapping))
        curves_by_track: dict[str, list[str]] = {}
        for curve in curves:
            mnemonic = str(curve.get("mnemonic") or "").strip()
            track_id = str(curve.get("track_id") or "").strip()
            if mnemonic and track_id:
                curves_by_track.setdefault(track_id, []).append(mnemonic)
        requested_visible = set(_clean_ids(payload.get("visible_tracks") or ()))
        use_requested = "visible_tracks" in payload
        items = []
        for track in tracks:
            track_id = str(track.get("id") or "").strip()
            if not track_id:
                continue
            order = _clean_ids(curves_by_track.get(track_id, ()))
            items.append(
                LasViewerTrackLayout(
                    track_id=track_id,
                    width=_positive_width(track.get("width"), 1.0),
                    visible=(track_id in requested_visible) if use_requested else bool(track.get("visible", True)),
                    curve_order=order,
                    visible_curves=order,
                    scale=_scale(track.get("scale") if isinstance(track.get("scale"), Mapping) else track.get("axis") if isinstance(track.get("axis"), Mapping) else None),
                )
            )
        return cls(LasViewerLayoutState(tuple(items)))

    @property
    def state(self) -> LasViewerLayoutState:
        return LasViewerLayoutState(tuple(self._tracks), self._revision)

    def set_track_visible(self, track_id: str, visible: bool) -> LasViewerLayoutState:
        index = self._track_index(track_id)
        item = self._tracks[index]
        updated = LasViewerTrackLayout(item.track_id, item.width, bool(visible), item.curve_order, item.visible_curves, item.scale)
        self._replace(index, updated)
        return self.state

    def set_track_width(self, track_id: str, width: float) -> LasViewerLayoutState:
        index = self._track_index(track_id)
        item = self._tracks[index]
        updated = LasViewerTrackLayout(item.track_id, _positive_width(width), item.visible, item.curve_order, item.visible_curves, item.scale)
        self._replace(index, updated)
        return self.state

    def set_track_scale(
        self,
        track_id: str,
        *,
        scale_type: str = "linear",
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> LasViewerLayoutState:
        index = self._track_index(track_id)
        item = self._tracks[index]
        updated = LasViewerTrackLayout(
            item.track_id, item.width, item.visible, item.curve_order, item.visible_curves,
            _scale({"scale_type": scale_type, "minimum": minimum, "maximum": maximum}),
        )
        self._replace(index, updated)
        return self.state

    def move_track(self, track_id: str, target_index: int) -> LasViewerLayoutState:
        source = self._track_index(track_id)
        if not self._tracks:
            return self.state
        target = max(0, min(int(target_index), len(self._tracks) - 1))
        if source != target:
            item = self._tracks.pop(source)
            self._tracks.insert(target, item)
            self._revision += 1
        return self.state

    def set_curve_visible(self, curve_id: str, visible: bool) -> LasViewerLayoutState:
        curve = str(curve_id or "").strip()
        for index, item in enumerate(self._tracks):
            if curve not in item.curve_order:
                continue
            values = list(item.visible_curves)
            if visible and curve not in values:
                values.append(curve)
            elif not visible and curve in values:
                values.remove(curve)
            ordered = tuple(candidate for candidate in item.curve_order if candidate in values)
            updated = LasViewerTrackLayout(item.track_id, item.width, item.visible, item.curve_order, ordered, item.scale)
            self._replace(index, updated)
            return self.state
        raise ValueError(f"unknown LAS curve: {curve}")

    def move_curve(self, curve_id: str, target_index: int) -> LasViewerLayoutState:
        curve = str(curve_id or "").strip()
        for index, item in enumerate(self._tracks):
            if curve not in item.curve_order:
                continue
            order = list(item.curve_order)
            source = order.index(curve)
            target = max(0, min(int(target_index), len(order) - 1))
            if source == target:
                return self.state
            order.pop(source)
            order.insert(target, curve)
            visible = tuple(candidate for candidate in order if candidate in item.visible_curves)
            self._tracks[index] = LasViewerTrackLayout(item.track_id, item.width, item.visible, tuple(order), visible, item.scale)
            self._revision += 1
            return self.state
        raise ValueError(f"unknown LAS curve: {curve}")

    def _track_index(self, track_id: str) -> int:
        track = str(track_id or "").strip()
        for index, item in enumerate(self._tracks):
            if item.track_id == track:
                return index
        raise ValueError(f"unknown LAS track: {track}")

    def _replace(self, index: int, updated: LasViewerTrackLayout) -> None:
        if updated != self._tracks[index]:
            self._tracks[index] = updated
            self._revision += 1
