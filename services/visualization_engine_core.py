"""Renderer-neutral Visualization Engine core contracts.

This module is the first independent layer of Visualization Engine 2.0.  It
normalizes already prepared visualization payloads into a generic scene contract:
tracks, layers and synchronized depth domain.  It deliberately contains no
Streamlit, matplotlib or report rendering imports, so UI and export layers can
consume the same scene without rebuilding domain calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class VisualizationLayer:
    """Generic printable layer inside a visualization track."""

    id: str
    kind: str
    track_id: str
    z_index: int = 0
    visible: bool = True
    printable: bool = True
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "track_id": self.track_id,
            "z_index": self.z_index,
            "visible": self.visible,
            "printable": self.printable,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class VisualizationTrack:
    """Renderer-neutral track descriptor with attached layer ids."""

    id: str
    title: str
    layer_ids: tuple[str, ...] = field(default_factory=tuple)
    width: float = 1.0
    printable: bool = True
    axis: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "layer_ids": list(self.layer_ids),
            "width": self.width,
            "printable": self.printable,
            "axis": dict(self.axis),
            "style": dict(self.style),
        }


@dataclass(frozen=True, slots=True)
class DepthSynchronizationContract:
    """Shared depth-domain contract used to keep all tracks aligned."""

    mode: str = "shared_depth_axis"
    depth_curve: str = ""
    unit: str = ""
    start: float | None = None
    stop: float | None = None
    step: float | None = None
    track_ids: tuple[str, ...] = field(default_factory=tuple)
    inverted: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "depth_curve": self.depth_curve,
            "unit": self.unit,
            "start": self.start,
            "stop": self.stop,
            "step": self.step,
            "track_ids": list(self.track_ids),
            "inverted": self.inverted,
        }


@dataclass(frozen=True, slots=True)
class VisualizationScene:
    """Complete Visualization Engine scene prepared for UI/export renderers."""

    schema: str = "visualization.engine.scene"
    version: str = "1.0"
    source: str = "las_visualization_payload"
    tracks: tuple[VisualizationTrack, ...] = field(default_factory=tuple)
    layers: tuple[VisualizationLayer, ...] = field(default_factory=tuple)
    depth_sync: DepthSynchronizationContract = field(default_factory=DepthSynchronizationContract)
    render_hints: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "source": self.source,
            "tracks": [track.to_dict() for track in self.tracks],
            "layers": [layer.to_dict() for layer in self.layers],
            "depth_sync": self.depth_sync.to_dict(),
            "render_hints": dict(self.render_hints),
            "quality": dict(self.quality),
        }


class VisualizationLayerManager:
    """Build deterministic layers from a renderer-neutral LAS payload."""

    CURVE_LAYER_Z = 20
    OVERLAY_LAYER_Z = 10

    def build_layers(self, payload: Mapping[str, Any]) -> tuple[VisualizationLayer, ...]:
        layers: list[VisualizationLayer] = []
        for curve in payload.get("curves", []) or []:
            mnemonic = str(curve.get("mnemonic") or "").strip()
            track_id = str(curve.get("track_id") or "track.other")
            if not mnemonic:
                continue
            layers.append(
                VisualizationLayer(
                    id=f"curve.{mnemonic}",
                    kind="curve",
                    track_id=track_id,
                    z_index=self.CURVE_LAYER_Z,
                    payload={
                        "mnemonic": mnemonic,
                        "unit": curve.get("unit", ""),
                        "axis": dict(curve.get("axis", {}) or {}),
                        "style": dict(curve.get("style", {}) or {}),
                        "point_count": int(curve.get("point_count") or 0),
                        "sampled_count": int(curve.get("sampled_count") or 0),
                        "points": list(curve.get("points", []) or []),
                    },
                )
            )
        for overlay in payload.get("overlays", []) or []:
            overlay_id = str(overlay.get("id") or "").strip()
            scope = tuple(str(item) for item in (overlay.get("track_scope", []) or []))
            if not overlay_id:
                continue
            target_tracks = scope or tuple(payload.get("visible_tracks", []) or []) or ("track.other",)
            for track_id in target_tracks:
                layers.append(
                    VisualizationLayer(
                        id=f"overlay.{overlay_id}.{track_id}",
                        kind="interval_overlay",
                        track_id=track_id,
                        z_index=self.OVERLAY_LAYER_Z,
                        payload={
                            "id": overlay_id,
                            "top": overlay.get("top"),
                            "base": overlay.get("base"),
                            "label": overlay.get("label", ""),
                            "fluid_type": overlay.get("fluid_type", "unknown"),
                            "confidence": overlay.get("confidence", ""),
                            "style": dict(overlay.get("style", {}) or {}),
                        },
                    )
                )
        return tuple(sorted(layers, key=lambda item: (item.track_id, item.z_index, item.id)))


class VisualizationEngineCore:
    """Create the first stable Visualization Engine scene contract."""

    def __init__(self, layer_manager: VisualizationLayerManager | None = None) -> None:
        self.layer_manager = layer_manager or VisualizationLayerManager()

    def build_scene(self, payload: Mapping[str, Any]) -> VisualizationScene:
        layers = self.layer_manager.build_layers(payload)
        layer_ids_by_track: dict[str, list[str]] = {}
        for layer in layers:
            layer_ids_by_track.setdefault(layer.track_id, []).append(layer.id)

        tracks: list[VisualizationTrack] = []
        for track in payload.get("tracks", []) or []:
            track_id = str(track.get("id") or "").strip()
            if not track_id:
                continue
            tracks.append(
                VisualizationTrack(
                    id=track_id,
                    title=str(track.get("title") or track_id),
                    layer_ids=tuple(layer_ids_by_track.get(track_id, [])),
                    width=float(track.get("width") or 1.0),
                    printable=bool(track.get("printable", True)),
                    axis=dict(track.get("axis", {}) or {}),
                    style=dict(track.get("style", {}) or {}),
                )
            )

        depth_range = dict(payload.get("depth_range", {}) or {})
        track_ids = tuple(track.id for track in tracks)
        depth_sync = DepthSynchronizationContract(
            depth_curve=str(payload.get("depth_curve") or ""),
            unit=str(payload.get("depth_unit") or ""),
            start=_float_or_none(depth_range.get("start")),
            stop=_float_or_none(depth_range.get("stop")),
            step=_float_or_none(depth_range.get("step")),
            track_ids=track_ids,
        )
        quality_flags = list(payload.get("quality_flags", []) or [])
        if not tracks:
            quality_flags.append("visualization_scene_has_no_tracks")
        if not layers:
            quality_flags.append("visualization_scene_has_no_layers")
        return VisualizationScene(
            tracks=tuple(tracks),
            layers=layers,
            depth_sync=depth_sync,
            render_hints={
                "renderer_neutral": True,
                "ui_must_not_recalculate": True,
                "preferred_preview_format": (payload.get("preview", {}) or {}).get("format", "svg"),
                "visible_tracks": list(payload.get("visible_tracks", []) or track_ids),
                "legend": list(payload.get("legend", []) or []),
                "plot_summary": dict(payload.get("plot_summary", {}) or {}),
            },
            quality={
                "flags": quality_flags,
                "track_count": len(tracks),
                "layer_count": len(layers),
                "curve_layer_count": len([layer for layer in layers if layer.kind == "curve"]),
                "overlay_layer_count": len([layer for layer in layers if layer.kind == "interval_overlay"]),
                "raw_dataframe_included": False,
            },
        )


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
