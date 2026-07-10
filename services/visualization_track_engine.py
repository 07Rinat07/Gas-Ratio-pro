"""Renderer-neutral track management for Visualization Engine.

The track engine converts logical scene tracks and layout geometry into a stable
workbench/renderer contract.  It owns ordering, visibility, printable state,
shared depth viewport metadata and track regions.  Concrete renderers therefore
do not decide which tracks are visible or how a track is subdivided.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class TrackRegion:
    kind: str
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True, slots=True)
class TrackViewport:
    depth_start: float | None
    depth_stop: float | None
    depth_unit: str
    inverted: bool
    plot_top: float
    plot_bottom: float

    @property
    def valid(self) -> bool:
        return (
            self.depth_start is not None
            and self.depth_stop is not None
            and self.depth_stop > self.depth_start
            and self.plot_bottom > self.plot_top
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth_start": self.depth_start,
            "depth_stop": self.depth_stop,
            "depth_unit": self.depth_unit,
            "inverted": self.inverted,
            "plot_top": self.plot_top,
            "plot_bottom": self.plot_bottom,
            "valid": self.valid,
        }


@dataclass(frozen=True, slots=True)
class VisualizationTrackModel:
    id: str
    title: str
    order: int
    visible: bool
    printable: bool
    pinned: bool
    group: str
    width_weight: float
    minimum_width: float
    layer_ids: tuple[str, ...] = field(default_factory=tuple)
    regions: tuple[TrackRegion, ...] = field(default_factory=tuple)
    viewport: TrackViewport = field(
        default_factory=lambda: TrackViewport(None, None, "", True, 0.0, 0.0)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "order": self.order,
            "visible": self.visible,
            "printable": self.printable,
            "pinned": self.pinned,
            "group": self.group,
            "width_weight": self.width_weight,
            "minimum_width": self.minimum_width,
            "layer_ids": list(self.layer_ids),
            "regions": [region.to_dict() for region in self.regions],
            "viewport": self.viewport.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class VisualizationTrackCollection:
    schema: str = "visualization.track.collection"
    version: str = "1.0"
    tracks: tuple[VisualizationTrackModel, ...] = field(default_factory=tuple)
    active_track_id: str = ""
    shared_depth_viewport: bool = True
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def visible_tracks(self) -> tuple[VisualizationTrackModel, ...]:
        return tuple(track for track in self.tracks if track.visible)

    @property
    def ok(self) -> bool:
        return bool(self.visible_tracks) and not any(
            issue.startswith("track_engine_error:") for issue in self.issues
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "tracks": [track.to_dict() for track in self.tracks],
            "visible_track_ids": [track.id for track in self.visible_tracks],
            "active_track_id": self.active_track_id,
            "shared_depth_viewport": self.shared_depth_viewport,
            "issues": list(self.issues),
            "ok": self.ok,
            "renderer_neutral": True,
        }


class VisualizationTrackEngine:
    """Build track state and regions without renderer or UI dependencies."""

    DEFAULT_MINIMUM_WIDTH = 120.0

    def build(
        self,
        scene: Mapping[str, Any],
        layout: Mapping[str, Any],
    ) -> VisualizationTrackCollection:
        scene_tracks = _mapping_list(scene.get("tracks"))
        layout_tracks = _mapping_list(layout.get("tracks"))
        render_hints = _mapping(scene.get("render_hints"))
        visible_hint = {
            str(item) for item in _sequence(render_hints.get("visible_tracks")) if str(item)
        }
        layout_by_id = {
            str(item.get("id") or ""): item
            for item in layout_tracks
            if str(item.get("id") or "")
        }
        depth = _mapping(layout.get("depth"))
        issues: list[str] = []
        if not scene_tracks:
            issues.append("track_engine_error:no_scene_tracks")
        if not layout_tracks:
            issues.append("track_engine_error:no_layout_tracks")

        models: list[VisualizationTrackModel] = []
        for order, track in enumerate(scene_tracks):
            track_id = str(track.get("id") or "").strip()
            if not track_id:
                issues.append(f"track_engine_warning:missing_track_id:{order}")
                continue
            track_layout = _mapping(layout_by_id.get(track_id))
            if not track_layout:
                issues.append(f"track_engine_warning:missing_layout:{track_id}")
            style = _mapping(track.get("style"))
            regions = self._regions(track_layout)
            plot = next((region for region in regions if region.kind == "plot"), None)
            viewport = TrackViewport(
                depth_start=_float_or_none(depth.get("start")),
                depth_stop=_float_or_none(depth.get("stop")),
                depth_unit=str(depth.get("unit") or ""),
                inverted=bool(depth.get("inverted", True)),
                plot_top=plot.y if plot else _float(depth.get("plot_top")),
                plot_bottom=(plot.y + plot.height) if plot else _float(depth.get("plot_bottom")),
            )
            visible = (not visible_hint or track_id in visible_hint) and bool(
                style.get("visible", True)
            )
            models.append(
                VisualizationTrackModel(
                    id=track_id,
                    title=str(track.get("title") or track_id),
                    order=order,
                    visible=visible,
                    printable=bool(track.get("printable", True)),
                    pinned=bool(style.get("pinned", False)),
                    group=str(style.get("group") or "default"),
                    width_weight=_positive_float(track.get("width"), 1.0),
                    minimum_width=_positive_float(
                        style.get("minimum_width"), self.DEFAULT_MINIMUM_WIDTH
                    ),
                    layer_ids=tuple(str(item) for item in _sequence(track.get("layer_ids"))),
                    regions=regions,
                    viewport=viewport,
                )
            )

        visible_models = [track for track in models if track.visible]
        active_track_id = str(render_hints.get("active_track_id") or "")
        if not active_track_id or active_track_id not in {item.id for item in visible_models}:
            active_track_id = visible_models[0].id if visible_models else ""
        if models and not visible_models:
            issues.append("track_engine_error:no_visible_tracks")
        if any(not track.viewport.valid for track in visible_models):
            issues.append("track_engine_error:invalid_shared_depth_viewport")

        return VisualizationTrackCollection(
            tracks=tuple(sorted(models, key=lambda item: (item.order, item.id))),
            active_track_id=active_track_id,
            shared_depth_viewport=True,
            issues=tuple(issues),
        )

    def _regions(self, layout: Mapping[str, Any]) -> tuple[TrackRegion, ...]:
        region_names = (
            ("bounds", "track"),
            ("header_bounds", "header"),
            ("axis_bounds", "axis"),
            ("plot_bounds", "plot"),
        )
        regions: list[TrackRegion] = []
        for key, kind in region_names:
            rect = _mapping(layout.get(key))
            if not rect:
                continue
            regions.append(
                TrackRegion(
                    kind=kind,
                    x=_float(rect.get("x")),
                    y=_float(rect.get("y")),
                    width=max(0.0, _float(rect.get("width"))),
                    height=max(0.0, _float(rect.get("height"))),
                )
            )
        return tuple(regions)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    return [_mapping(item) for item in _sequence(value) if isinstance(item, Mapping)]


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_float(value: Any, default: float) -> float:
    parsed = _float(value, default)
    return parsed if parsed > 0 else default
