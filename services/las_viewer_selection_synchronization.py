"""Renderer-neutral LAS Viewer selection synchronization.

The service expands a logical selection across visible LAS tracks and produces
ready-to-render overlay primitives. UI adapters only render the returned model;
matching rules and highlight styling remain outside the UI layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from services.visualization_render_model import RenderPrimitive, VisualizationRenderModel
from services.visualization_selection import SelectionItem, SelectionState


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
class LasViewerSelectionOverlay:
    selected_ids: tuple[str, ...]
    synchronized_primitive_ids: tuple[str, ...]
    primitives: tuple[RenderPrimitive, ...]
    requested_track_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def empty(self) -> bool:
        return not self.primitives

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.selection-overlay",
            "version": "1.0",
            "selected_ids": list(self.selected_ids),
            "synchronized_primitive_ids": list(self.synchronized_primitive_ids),
            "primitives": [item.to_dict() for item in self.primitives],
            "requested_track_ids": list(self.requested_track_ids),
            "diagnostics": list(self.diagnostics),
            "empty": self.empty,
            "renderer_neutral": True,
        }


class LasViewerSelectionSynchronizationEngine:
    """Resolve logical selection into synchronized LAS track overlays."""

    OVERLAY_Z_OFFSET = 200

    def resolve(
        self,
        model: VisualizationRenderModel | Mapping[str, Any],
        selection: SelectionState | Mapping[str, Any],
        *,
        track_ids: Iterable[str] | None = None,
        synchronize_source_layers: bool = True,
        accent: str = "#ff8a00",
    ) -> LasViewerSelectionOverlay:
        resolved_model = model if isinstance(model, VisualizationRenderModel) else VisualizationRenderModel.from_dict(model)
        resolved_selection = selection if isinstance(selection, SelectionState) else SelectionState.from_dict(selection)
        requested = _clean_ids(track_ids or ())
        requested_set = set(requested)
        diagnostics: list[str] = []

        if not accent.strip():
            raise ValueError("accent cannot be empty")
        if any(not item.valid for item in resolved_selection.items):
            raise ValueError("selection contains invalid items")

        visible = tuple(
            primitive
            for primitive in resolved_model.primitives
            if primitive.visible and (not requested_set or primitive.track_id in requested_set)
        )
        by_id = {primitive.id: primitive for primitive in visible}
        matched: dict[str, RenderPrimitive] = {}

        for item in resolved_selection.items:
            exact = by_id.get(item.primitive_id)
            if exact is not None:
                matched[exact.id] = exact

            if synchronize_source_layers and item.source_layer_id:
                for primitive in visible:
                    if self._source_layer_id(primitive) == item.source_layer_id:
                        matched[primitive.id] = primitive

            if exact is None and not any(
                self._matches_item(primitive, item, synchronize_source_layers)
                for primitive in visible
            ):
                diagnostics.append(f"selection_overlay_missing_primitive:{item.primitive_id}")

        overlays = tuple(
            self._overlay_for(matched[key], accent=accent)
            for key in sorted(matched, key=lambda value: (matched[value].track_id, matched[value].z_index, value))
        )

        if requested_set:
            model_tracks = {item.track_id for item in resolved_model.primitives if item.track_id}
            for track_id in sorted(requested_set.difference(model_tracks)):
                diagnostics.append(f"selection_overlay_missing_track:{track_id}")

        return LasViewerSelectionOverlay(
            selected_ids=resolved_selection.selected_ids,
            synchronized_primitive_ids=tuple(item.id for item in overlays),
            primitives=overlays,
            requested_track_ids=requested,
            diagnostics=tuple(dict.fromkeys(diagnostics)),
        )

    @classmethod
    def _matches_item(
        cls,
        primitive: RenderPrimitive,
        item: SelectionItem,
        synchronize_source_layers: bool,
    ) -> bool:
        if primitive.id == item.primitive_id:
            return True
        return bool(
            synchronize_source_layers
            and item.source_layer_id
            and cls._source_layer_id(primitive) == item.source_layer_id
        )

    @staticmethod
    def _source_layer_id(primitive: RenderPrimitive) -> str:
        return str(primitive.payload.get("source_layer_id") or "").strip()

    @classmethod
    def _overlay_for(cls, primitive: RenderPrimitive, *, accent: str) -> RenderPrimitive:
        payload = dict(primitive.payload)
        payload.update(
            {
                "selection_overlay": True,
                "selected_primitive_id": primitive.id,
                "source_layer_id": cls._source_layer_id(primitive),
                "selection_accent": accent,
            }
        )
        if primitive.kind in {"polyline", "line"}:
            payload["stroke"] = accent
            payload["stroke_width"] = max(3.0, float(payload.get("stroke_width") or 1.0) + 2.0)
            payload["opacity"] = 1.0
        elif primitive.kind == "rectangle":
            payload["fill"] = "none"
            payload["stroke"] = accent
            payload["stroke_width"] = max(2.0, float(payload.get("stroke_width") or 1.0) + 1.0)
        elif primitive.kind == "text":
            payload["fill"] = accent
            payload["font_weight"] = "bold"
        else:
            payload["stroke"] = accent
            payload["selection_highlight"] = True

        return RenderPrimitive(
            id=f"selection.{primitive.id}",
            kind=primitive.kind,
            z_index=primitive.z_index + cls.OVERLAY_Z_OFFSET,
            payload=payload,
            track_id=primitive.track_id,
            clip_id=primitive.clip_id,
            visible=True,
            printable=False,
        )
