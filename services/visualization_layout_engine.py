"""Renderer-neutral geometry for Visualization Engine scenes.

The layout engine converts a logical ``VisualizationScene`` into deterministic
pixel geometry. Renderers consume this model and do not calculate track widths,
depth coordinates, or axis regions themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class LayoutRect:
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True, slots=True)
class TrackLayout:
    id: str
    title: str
    bounds: LayoutRect
    plot_bounds: LayoutRect
    header_bounds: LayoutRect
    axis_bounds: LayoutRect
    layer_ids: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "bounds": self.bounds.to_dict(),
            "plot_bounds": self.plot_bounds.to_dict(),
            "header_bounds": self.header_bounds.to_dict(),
            "axis_bounds": self.axis_bounds.to_dict(),
            "layer_ids": list(self.layer_ids),
        }


@dataclass(frozen=True, slots=True)
class DepthLayout:
    start: float | None
    stop: float | None
    unit: str
    inverted: bool
    plot_top: float
    plot_bottom: float

    @property
    def valid(self) -> bool:
        return self.start is not None and self.stop is not None and self.stop > self.start

    def map_depth(self, depth: float) -> float | None:
        if not self.valid:
            return None
        ratio = (float(depth) - float(self.start)) / (float(self.stop) - float(self.start))
        if not self.inverted:
            ratio = 1.0 - ratio
        return self.plot_top + ratio * (self.plot_bottom - self.plot_top)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "stop": self.stop,
            "unit": self.unit,
            "inverted": self.inverted,
            "plot_top": self.plot_top,
            "plot_bottom": self.plot_bottom,
            "valid": self.valid,
        }


@dataclass(frozen=True, slots=True)
class VisualizationLayout:
    schema: str = "visualization.layout.result"
    version: str = "1.0"
    width: int = 0
    height: int = 0
    canvas_bounds: LayoutRect = field(default_factory=lambda: LayoutRect(0, 0, 0, 0))
    content_bounds: LayoutRect = field(default_factory=lambda: LayoutRect(0, 0, 0, 0))
    tracks: tuple[TrackLayout, ...] = field(default_factory=tuple)
    depth: DepthLayout = field(default_factory=lambda: DepthLayout(None, None, "", True, 0, 0))
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.issues and bool(self.tracks) and self.depth.valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "width": self.width,
            "height": self.height,
            "canvas_bounds": self.canvas_bounds.to_dict(),
            "content_bounds": self.content_bounds.to_dict(),
            "tracks": [track.to_dict() for track in self.tracks],
            "depth": self.depth.to_dict(),
            "issues": list(self.issues),
            "ok": self.ok,
            "renderer_neutral": True,
        }


class VisualizationLayoutEngine:
    """Calculate deterministic scene geometry shared by all renderers."""

    DEFAULT_TRACK_WIDTH = 180
    MIN_TRACK_WIDTH = 120
    HEADER_HEIGHT = 42
    AXIS_HEIGHT = 22
    PLOT_HEIGHT = 620
    FOOTER_HEIGHT = 24
    SIDE_PADDING = 12

    def build(self, scene: Mapping[str, Any]) -> VisualizationLayout:
        tracks = _mapping_list(scene.get("tracks"))
        depth_sync = _mapping(scene.get("depth_sync"))
        issues: list[str] = []
        if not tracks:
            issues.append("layout_scene_has_no_tracks")

        start = _float_or_none(depth_sync.get("start"))
        stop = _float_or_none(depth_sync.get("stop"))
        if start is None or stop is None or stop <= start:
            issues.append("layout_invalid_depth_domain")

        plot_top = self.HEADER_HEIGHT + self.AXIS_HEIGHT
        plot_bottom = plot_top + self.PLOT_HEIGHT
        x = float(self.SIDE_PADDING)
        track_layouts: list[TrackLayout] = []
        for index, track in enumerate(tracks):
            track_id = str(track.get("id") or f"track.{index}")
            weight = max(_positive_float(track.get("width"), 1.0), 0.5)
            width = float(max(self.MIN_TRACK_WIDTH, int(self.DEFAULT_TRACK_WIDTH * weight)))
            bounds = LayoutRect(x=x, y=0.0, width=width, height=float(plot_bottom))
            header = LayoutRect(x=x, y=0.0, width=width, height=float(self.HEADER_HEIGHT))
            axis = LayoutRect(x=x, y=float(self.HEADER_HEIGHT), width=width, height=float(self.AXIS_HEIGHT))
            plot = LayoutRect(x=x, y=float(plot_top), width=width, height=float(self.PLOT_HEIGHT))
            track_layouts.append(
                TrackLayout(
                    id=track_id,
                    title=str(track.get("title") or track_id),
                    bounds=bounds,
                    plot_bounds=plot,
                    header_bounds=header,
                    axis_bounds=axis,
                    layer_ids=tuple(str(item) for item in _sequence(track.get("layer_ids"))),
                )
            )
            x += width

        total_width = int(max(360, x + self.SIDE_PADDING))
        total_height = int(plot_bottom + self.FOOTER_HEIGHT)
        depth = DepthLayout(
            start=start,
            stop=stop,
            unit=str(depth_sync.get("unit") or ""),
            inverted=bool(depth_sync.get("inverted", True)),
            plot_top=float(plot_top),
            plot_bottom=float(plot_bottom),
        )
        return VisualizationLayout(
            width=total_width,
            height=total_height,
            canvas_bounds=LayoutRect(0.0, 0.0, float(total_width), float(total_height)),
            content_bounds=LayoutRect(float(self.SIDE_PADDING), 0.0, max(0.0, x - self.SIDE_PADDING), float(plot_bottom)),
            tracks=tuple(track_layouts),
            depth=depth,
            issues=tuple(issues),
        )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    return [_mapping(item) for item in _sequence(value) if isinstance(item, Mapping)]


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
