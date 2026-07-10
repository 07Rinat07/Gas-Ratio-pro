"""Renderer-neutral labels and legend contracts for Visualization Engine.

The engine prepares text placement and legend metadata before a concrete
renderer is invoked.  Renderers therefore draw ready coordinates and styles
without inspecting LAS payloads or performing collision calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class VisualizationLabel:
    id: str
    kind: str
    text: str
    x: float
    y: float
    track_id: str = ""
    font_size: float = 9.0
    font_weight: int = 400
    fill: str = "#37474f"
    text_anchor: str = "start"
    rotation: float = 0.0
    visible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "track_id": self.track_id,
            "font_size": self.font_size,
            "font_weight": self.font_weight,
            "fill": self.fill,
            "text_anchor": self.text_anchor,
            "rotation": self.rotation,
            "visible": self.visible,
        }


@dataclass(frozen=True, slots=True)
class VisualizationLegendItem:
    id: str
    kind: str
    label: str
    track_id: str = ""
    color: str = "#607d8b"
    line_width: float = 1.5
    unit: str = ""
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "track_id": self.track_id,
            "color": self.color,
            "line_width": self.line_width,
            "unit": self.unit,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class VisualizationLabelLegendModel:
    schema: str = "visualization.label.legend.model"
    version: str = "1.0"
    labels: tuple[VisualizationLabel, ...] = field(default_factory=tuple)
    legend_items: tuple[VisualizationLegendItem, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not any(item.startswith("label_legend_error:") for item in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "labels": [item.to_dict() for item in self.labels],
            "legend_items": [item.to_dict() for item in self.legend_items],
            "issues": list(self.issues),
            "metadata": dict(self.metadata),
            "ok": self.ok,
            "renderer_neutral": True,
        }


class VisualizationLabelLegendEngine:
    """Build collision-safe labels and legend items from scene/layout data."""

    MIN_LABEL_GAP = 12.0
    MAX_CURVE_LABELS_PER_TRACK = 4

    def build(
        self,
        scene: Mapping[str, Any],
        layout: Mapping[str, Any],
        track_model: Mapping[str, Any] | None = None,
    ) -> VisualizationLabelLegendModel:
        tracks = _mapping_list(scene.get("tracks"))
        layers = _mapping_list(scene.get("layers"))
        layout_tracks = _mapping_list(layout.get("tracks"))
        managed = _mapping_list((track_model or {}).get("tracks"))
        managed_by_id = {str(item.get("id") or ""): item for item in managed}
        scene_by_id = {str(item.get("id") or ""): item for item in tracks}
        labels: list[VisualizationLabel] = []
        legend_items: list[VisualizationLegendItem] = []
        issues: list[str] = []
        collision_count = 0
        truncated_count = 0

        layers_by_track: dict[str, list[dict[str, Any]]] = {}
        for layer in layers:
            if not bool(layer.get("visible", True)):
                continue
            layers_by_track.setdefault(str(layer.get("track_id") or ""), []).append(layer)

        for index, layout_track in enumerate(layout_tracks):
            track_id = str(layout_track.get("id") or f"track.{index}")
            if managed and not bool(managed_by_id.get(track_id, {}).get("visible", False)):
                continue
            scene_track = scene_by_id.get(track_id, {})
            title = str(
                managed_by_id.get(track_id, {}).get("title")
                or layout_track.get("title")
                or scene_track.get("title")
                or track_id
            )
            header = _mapping(layout_track.get("header_bounds"))
            axis = _mapping(layout_track.get("axis_bounds"))
            labels.append(
                VisualizationLabel(
                    id=f"label.{track_id}.title",
                    kind="track_title",
                    text=_truncate(title, 34),
                    x=_float(header.get("x")) + 8.0,
                    y=_float(header.get("y")) + 18.0,
                    track_id=track_id,
                    font_size=11.0,
                    font_weight=600,
                    fill="#263238",
                )
            )

            curve_layers = [item for item in layers_by_track.get(track_id, []) if str(item.get("kind") or "") == "curve"]
            curve_layers.sort(key=lambda item: str(item.get("id") or ""))
            usable = curve_layers[: self.MAX_CURVE_LABELS_PER_TRACK]
            if len(curve_layers) > len(usable):
                truncated_count += len(curve_layers) - len(usable)
                issues.append(f"label_legend_curve_labels_truncated:{track_id}:{len(curve_layers) - len(usable)}")
            if usable:
                left = _float(axis.get("x")) + 8.0
                width = max(_float(axis.get("width")), 1.0)
                slot = width / len(usable)
                previous_x: float | None = None
                for curve_index, layer in enumerate(usable):
                    payload = _mapping(layer.get("payload"))
                    mnemonic = str(payload.get("mnemonic") or layer.get("id") or "Curve")
                    unit = str(payload.get("unit") or "")
                    text = mnemonic if not unit else f"{mnemonic} [{unit}]"
                    x = left + slot * curve_index + slot / 2.0
                    if previous_x is not None and x - previous_x < self.MIN_LABEL_GAP:
                        collision_count += 1
                        x = previous_x + self.MIN_LABEL_GAP
                    previous_x = x
                    style = _mapping(payload.get("style"))
                    color = str(style.get("stroke") or "#455a64")
                    labels.append(
                        VisualizationLabel(
                            id=f"label.{layer.get('id')}",
                            kind="curve_label",
                            text=_truncate(text, 22),
                            x=x,
                            y=_float(axis.get("y")) + 14.0,
                            track_id=track_id,
                            font_size=8.0,
                            font_weight=500,
                            fill=color,
                            text_anchor="middle",
                        )
                    )
                    legend_items.append(
                        VisualizationLegendItem(
                            id=f"legend.{layer.get('id')}",
                            kind="curve",
                            label=mnemonic,
                            track_id=track_id,
                            color=color,
                            line_width=_positive_float(style.get("line_width"), 1.3),
                            unit=unit,
                        )
                    )

        seen_overlay_labels: set[tuple[str, str]] = set()
        for layer in layers:
            if str(layer.get("kind") or "") != "interval_overlay" or not bool(layer.get("visible", True)):
                continue
            payload = _mapping(layer.get("payload"))
            label = str(payload.get("label") or "Interval")
            track_id = str(layer.get("track_id") or "")
            key = (label, track_id)
            if key in seen_overlay_labels:
                continue
            seen_overlay_labels.add(key)
            style = _mapping(payload.get("style"))
            confidence = _finite_float(payload.get("confidence"))
            legend_items.append(
                VisualizationLegendItem(
                    id=f"legend.{layer.get('id')}",
                    kind="interval",
                    label=label,
                    track_id=track_id,
                    color=str(style.get("fill") or "#b0bec5"),
                    line_width=0.0,
                    confidence=confidence,
                )
            )

        labels.sort(key=lambda item: (item.track_id, item.kind, item.id))
        legend_items.sort(key=lambda item: (item.kind, item.track_id, item.label, item.id))
        return VisualizationLabelLegendModel(
            labels=tuple(labels),
            legend_items=tuple(legend_items),
            issues=tuple(dict.fromkeys(issues)),
            metadata={
                "track_label_count": len([item for item in labels if item.kind == "track_title"]),
                "curve_label_count": len([item for item in labels if item.kind == "curve_label"]),
                "legend_item_count": len(legend_items),
                "collision_adjustment_count": collision_count,
                "truncated_curve_label_count": truncated_count,
                "raw_dataframe_included": False,
                "ui_objects_included": False,
            },
        )


def _truncate(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


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


def _finite_float(value: Any) -> float | None:
    import math
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
