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
    """Build deterministic structural drawing primitives from scene/layout."""

    CANVAS_Z = 0
    TRACK_BACKGROUND_Z = 10
    TRACK_BORDER_Z = 20
    TRACK_TITLE_Z = 40
    DIAGNOSTIC_Z = 1000

    def build(
        self,
        scene: Mapping[str, Any],
        layout: Mapping[str, Any],
    ) -> VisualizationRenderModel:
        width = int(_positive_float(layout.get("width"), 360))
        height = int(_positive_float(layout.get("height"), 180))
        scene_tracks = _mapping_list(scene.get("tracks"))
        layout_tracks = _mapping_list(layout.get("tracks"))
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
                title = str(track_layout.get("title") or scene_track.get("title") or track_id)
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

        if source_layers:
            diagnostics.append(f"render_model_pending_source_layers:{len(source_layers)}")
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
                "foundation_scope": "canvas_track_structure",
            },
        )

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
