"""Renderer-neutral drawing primitives for Visualization Engine.

The render model sits between logical scene/layout data and concrete rendering
backends.  It contains only serializable drawing primitives, clip regions and
QA diagnostics.  SVG/PDF/Canvas renderers can consume this contract without
reading LAS payloads or calculating track geometry.

This first foundation increment intentionally converts only canvas/track
structure and labels. Curve, axis, grid and interval geometry are added by
subsequent focused increments. Source layers are reported through diagnostics
instead of being silently discarded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from services.visualization_axis_grid import VisualizationAxisGridEngine


@dataclass(frozen=True, slots=True)
class RenderClipRegion:
    """Named rectangular clipping region shared by render primitives."""

    id: str
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True, slots=True)
class RenderPrimitive:
    """Single backend-independent drawing command."""

    id: str
    kind: str
    z_index: int
    payload: dict[str, Any] = field(default_factory=dict)
    track_id: str = ""
    clip_id: str = ""
    visible: bool = True
    printable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "z_index": self.z_index,
            "track_id": self.track_id,
            "clip_id": self.clip_id,
            "visible": self.visible,
            "printable": self.printable,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class VisualizationRenderModel:
    """Stable renderer input produced from a scene and its layout."""

    schema: str = "visualization.render.model"
    version: str = "1.0"
    width: int = 0
    height: int = 0
    clip_regions: tuple[RenderClipRegion, ...] = field(default_factory=tuple)
    primitives: tuple[RenderPrimitive, ...] = field(default_factory=tuple)
    diagnostics: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.width > 0 and self.height > 0 and not any(
            item.startswith("render_model_error:") for item in self.diagnostics
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "width": self.width,
            "height": self.height,
            "clip_regions": [region.to_dict() for region in self.clip_regions],
            "primitives": [primitive.to_dict() for primitive in self.primitives],
            "diagnostics": list(self.diagnostics),
            "metadata": dict(self.metadata),
            "ok": self.ok,
            "renderer_neutral": True,
        }


class VisualizationRenderModelBuilder:
    """Build deterministic renderer primitives from scene/layout contracts."""

    def __init__(self, axis_grid_engine: VisualizationAxisGridEngine | None = None) -> None:
        self.axis_grid_engine = axis_grid_engine or VisualizationAxisGridEngine()

    CANVAS_Z = 0
    TRACK_BACKGROUND_Z = 10
    MINOR_GRID_Z = 14
    MAJOR_GRID_Z = 16
    TRACK_BORDER_Z = 20
    AXIS_TEXT_Z = 35
    TRACK_TITLE_Z = 40
    DIAGNOSTIC_Z = 1000

    def build(
        self,
        scene: Mapping[str, Any],
        layout: Mapping[str, Any],
        axis_grid: Mapping[str, Any] | None = None,
        track_model: Mapping[str, Any] | None = None,
    ) -> VisualizationRenderModel:
        width = int(_positive_float(layout.get("width"), 360))
        height = int(_positive_float(layout.get("height"), 180))
        scene_tracks = _mapping_list(scene.get("tracks"))
        layout_tracks = _mapping_list(layout.get("tracks"))
        track_model_payload = dict(track_model or {})
        managed_tracks = _mapping_list(track_model_payload.get("tracks"))
        managed_by_id = {str(item.get("id") or ""): item for item in managed_tracks}
        source_layers = _mapping_list(scene.get("layers"))
        diagnostics: list[str] = []
        clips: list[RenderClipRegion] = []
        primitives: list[RenderPrimitive] = [
            RenderPrimitive(
                id="canvas.background",
                kind="rectangle",
                z_index=self.CANVAS_Z,
                payload={
                    "x": 0.0,
                    "y": 0.0,
                    "width": float(width),
                    "height": float(height),
                    "fill": "#ffffff",
                    "stroke": "none",
                },
            )
        ]

        scene_by_id = {
            str(track.get("id") or ""): track
            for track in scene_tracks
            if str(track.get("id") or "")
        }

        if not layout_tracks:
            diagnostics.append("render_model_error:no_layout_tracks")
            primitives.extend(self._empty_scene_primitives(width=width, height=height))
        else:
            for index, track_layout in enumerate(layout_tracks):
                track_id = str(track_layout.get("id") or f"track.{index}")
                scene_track = _mapping(scene_by_id.get(track_id))
                managed_track = _mapping(managed_by_id.get(track_id))
                if managed_tracks and not bool(managed_track.get("visible", False)):
                    continue
                bounds = _mapping(track_layout.get("bounds"))
                plot_bounds = _mapping(track_layout.get("plot_bounds"))
                header_bounds = _mapping(track_layout.get("header_bounds"))
                clip_id = f"clip.{track_id}.plot"
                clips.append(
                    RenderClipRegion(
                        id=clip_id,
                        x=_float(plot_bounds.get("x")),
                        y=_float(plot_bounds.get("y")),
                        width=_non_negative_float(plot_bounds.get("width")),
                        height=_non_negative_float(plot_bounds.get("height")),
                    )
                )
                style = _mapping(scene_track.get("style"))
                title = str(managed_track.get("title") or track_layout.get("title") or scene_track.get("title") or track_id)
                x = _float(bounds.get("x"))
                y = _float(bounds.get("y"))
                track_width = _non_negative_float(bounds.get("width"))
                track_height = _non_negative_float(bounds.get("height"))
                primitives.extend(
                    [
                        RenderPrimitive(
                            id=f"track.{track_id}.background",
                            kind="rectangle",
                            z_index=self.TRACK_BACKGROUND_Z,
                            track_id=track_id,
                            payload={
                                "x": x,
                                "y": y,
                                "width": track_width,
                                "height": track_height,
                                "fill": str(style.get("fill") or "#ffffff"),
                                "stroke": "none",
                            },
                        ),
                        RenderPrimitive(
                            id=f"track.{track_id}.border",
                            kind="rectangle",
                            z_index=self.TRACK_BORDER_Z,
                            track_id=track_id,
                            payload={
                                "x": x,
                                "y": y,
                                "width": track_width,
                                "height": track_height,
                                "fill": "none",
                                "stroke": "#b0bec5",
                                "stroke_width": 1.0,
                            },
                        ),
                        RenderPrimitive(
                            id=f"track.{track_id}.title",
                            kind="text",
                            z_index=self.TRACK_TITLE_Z,
                            track_id=track_id,
                            payload={
                                "x": _float(header_bounds.get("x")) + 8.0,
                                "y": _float(header_bounds.get("y")) + 26.0,
                                "text": title,
                                "font_size": 12.0,
                                "font_weight": 600,
                                "fill": "#263238",
                            },
                        ),
                    ]
                )

        axis_grid_model = (
            self.axis_grid_engine.build(scene, layout)
            if axis_grid is None
            else None
        )
        axis_grid_payload = axis_grid_model.to_dict() if axis_grid_model is not None else dict(axis_grid or {})
        diagnostics.extend(str(item) for item in _sequence(axis_grid_payload.get("issues")) if str(item))
        primitives.extend(self._axis_grid_primitives(axis_grid_payload, layout_tracks))

        pending_layers = [layer for layer in source_layers if str(layer.get("kind") or "") in {"curve", "interval_overlay"}]
        if pending_layers:
            diagnostics.append(f"render_model_pending_source_layers:{len(pending_layers)}")
        if track_model_payload:
            diagnostics.extend(str(item) for item in _sequence(track_model_payload.get("issues")) if str(item))
        if scene_tracks and len(layout_tracks) != len(scene_tracks):
            diagnostics.append(
                f"render_model_track_count_mismatch:{len(scene_tracks)}:{len(layout_tracks)}"
            )

        ordered_clips = tuple(sorted(clips, key=lambda item: item.id))
        ordered_primitives = tuple(
            sorted(primitives, key=lambda item: (item.z_index, item.track_id, item.id))
        )
        return VisualizationRenderModel(
            width=width,
            height=height,
            clip_regions=ordered_clips,
            primitives=ordered_primitives,
            diagnostics=tuple(diagnostics),
            metadata={
                "source_scene_schema": str(scene.get("schema") or ""),
                "source_layout_schema": str(layout.get("schema") or ""),
                "track_count": len(layout_tracks),
                "source_layer_count": len(source_layers),
                "primitive_count": len(ordered_primitives),
                "clip_region_count": len(ordered_clips),
                "raw_dataframe_included": False,
                "ui_objects_included": False,
                "foundation_scope": "canvas_track_axis_grid_track_engine",
                "axis_count": len(_mapping_list(axis_grid_payload.get("axes"))),
                "grid_line_count": len(_mapping_list(axis_grid_payload.get("grid_lines"))),
                "axis_grid_ok": bool(axis_grid_payload.get("ok", False)),
                "track_model_ok": bool(track_model_payload.get("ok", False)) if track_model_payload else False,
                "visible_track_count": len(_sequence(track_model_payload.get("visible_track_ids"))) if track_model_payload else len(layout_tracks),
                "active_track_id": str(track_model_payload.get("active_track_id") or ""),
            },
        )

    def _axis_grid_primitives(
        self,
        axis_grid: Mapping[str, Any],
        layout_tracks: list[dict[str, Any]],
    ) -> list[RenderPrimitive]:
        primitives: list[RenderPrimitive] = []
        layout_by_id = {str(item.get("id") or ""): item for item in layout_tracks}
        for line in _mapping_list(axis_grid.get("grid_lines")):
            track_id = str(line.get("track_id") or "")
            orientation = str(line.get("orientation") or "")
            major = bool(line.get("major"))
            position = _float(line.get("position"))
            start = _float(line.get("start"))
            stop = _float(line.get("stop"))
            if orientation == "horizontal":
                x1, y1, x2, y2 = start, position, stop, position
            else:
                x1, y1, x2, y2 = position, start, position, stop
            primitives.append(
                RenderPrimitive(
                    id=str(line.get("id") or "grid"),
                    kind="line",
                    z_index=self.MAJOR_GRID_Z if major else self.MINOR_GRID_Z,
                    track_id=track_id,
                    clip_id=f"clip.{track_id}.plot" if track_id else "",
                    payload={
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        "stroke": "#cfd8dc" if major else "#eceff1",
                        "stroke_width": 0.8 if major else 0.45,
                        "major": major,
                    },
                )
            )
        for axis in _mapping_list(axis_grid.get("axes")):
            track_id = str(axis.get("track_id") or "")
            kind = str(axis.get("kind") or "")
            ticks = _mapping_list(axis.get("ticks"))
            for index, tick in enumerate(ticks):
                if not bool(tick.get("major")) or not str(tick.get("label") or ""):
                    continue
                position = _float(tick.get("position"))
                if kind == "depth":
                    for track_layout in layout_tracks[:1]:
                        plot = _mapping(track_layout.get("plot_bounds"))
                        primitives.append(RenderPrimitive(
                            id=f"axis.depth.label.{index}", kind="text", z_index=self.AXIS_TEXT_Z,
                            track_id=str(track_layout.get("id") or ""),
                            payload={"x": _float(plot.get("x")) + 4.0, "y": position + 10.0,
                                     "text": str(tick.get("label") or ""), "font_size": 8.0, "fill": "#607d8b"},
                        ))
                elif track_id in layout_by_id:
                    axis_bounds = _mapping(layout_by_id[track_id].get("axis_bounds"))
                    primitives.append(RenderPrimitive(
                        id=f"{axis.get('id', 'axis')}.label.{index}", kind="text", z_index=self.AXIS_TEXT_Z,
                        track_id=track_id,
                        payload={"x": position, "y": _float(axis_bounds.get("y")) + 16.0,
                                 "text": str(tick.get("label") or ""), "font_size": 8.0,
                                 "text_anchor": "middle", "fill": "#455a64"},
                    ))
        return primitives

    def _empty_scene_primitives(self, *, width: int, height: int) -> list[RenderPrimitive]:
        card_width = float(max(260, min(width - 24, 420)))
        card_height = float(min(max(height - 24, 110), 140))
        return [
            RenderPrimitive(
                id="diagnostic.empty.background",
                kind="rectangle",
                z_index=self.DIAGNOSTIC_Z,
                payload={
                    "x": 12.0,
                    "y": 12.0,
                    "width": card_width,
                    "height": card_height,
                    "fill": "#f5f7fa",
                    "stroke": "#c7d0d9",
                    "corner_radius": 6.0,
                },
            ),
            RenderPrimitive(
                id="diagnostic.empty.title",
                kind="text",
                z_index=self.DIAGNOSTIC_Z + 1,
                payload={
                    "x": 28.0,
                    "y": 52.0,
                    "text": "Visualization scene is empty",
                    "font_size": 15.0,
                    "font_weight": 600,
                    "fill": "#263238",
                },
            ),
            RenderPrimitive(
                id="diagnostic.empty.message",
                kind="text",
                z_index=self.DIAGNOSTIC_Z + 2,
                payload={
                    "x": 28.0,
                    "y": 80.0,
                    "text": "No layout tracks are available for rendering.",
                    "font_size": 11.0,
                    "font_weight": 400,
                    "fill": "#607d8b",
                },
            ),
        ]


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


def _positive_float(value: Any, default: float) -> float:
    parsed = _float(value, default)
    return parsed if parsed > 0 else default


def _non_negative_float(value: Any) -> float:
    return max(0.0, _float(value))
