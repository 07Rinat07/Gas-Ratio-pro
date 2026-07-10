"""Renderer-neutral selection state for interactive visualization.

The module converts hit-test results into stable selection items and applies
explicit selection commands. UI adapters only create commands and render the
resulting state; selection rules remain in the service layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from services.visualization_hit_testing import HitTestResult


_SELECTION_MODES = frozenset({"replace", "add", "toggle", "remove", "clear"})


@dataclass(frozen=True, slots=True)
class SelectionItem:
    primitive_id: str
    primitive_kind: str = ""
    track_id: str = ""
    source_layer_id: str = ""
    data_kind: str = ""
    segment_index: int | None = None
    point_index: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_hit(cls, hit: HitTestResult) -> "SelectionItem":
        return cls(
            primitive_id=hit.primitive_id,
            primitive_kind=hit.primitive_kind,
            track_id=hit.track_id,
            source_layer_id=hit.source_layer_id,
            data_kind=hit.data_kind,
            segment_index=hit.segment_index,
            point_index=hit.point_index,
            payload=dict(hit.payload),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SelectionItem":
        return cls(
            primitive_id=str(value.get("primitive_id") or ""),
            primitive_kind=str(value.get("primitive_kind") or ""),
            track_id=str(value.get("track_id") or ""),
            source_layer_id=str(value.get("source_layer_id") or ""),
            data_kind=str(value.get("data_kind") or ""),
            segment_index=_optional_int(value.get("segment_index")),
            point_index=_optional_int(value.get("point_index")),
            payload=dict(value.get("payload") or {}),
        )

    @property
    def valid(self) -> bool:
        return bool(self.primitive_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_id": self.primitive_id,
            "primitive_kind": self.primitive_kind,
            "track_id": self.track_id,
            "source_layer_id": self.source_layer_id,
            "data_kind": self.data_kind,
            "segment_index": self.segment_index,
            "point_index": self.point_index,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class SelectionCommand:
    mode: str
    items: tuple[SelectionItem, ...] = field(default_factory=tuple)
    source: str = ""

    @classmethod
    def from_hits(
        cls,
        hits: Sequence[HitTestResult],
        *,
        mode: str = "replace",
        source: str = "",
    ) -> "SelectionCommand":
        return cls(mode=mode, items=tuple(SelectionItem.from_hit(hit) for hit in hits), source=source)

    @classmethod
    def clear(cls, *, source: str = "") -> "SelectionCommand":
        return cls(mode="clear", source=source)

    @property
    def valid(self) -> bool:
        return self.mode in _SELECTION_MODES and all(item.valid for item in self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.selection-command",
            "version": "1.0",
            "mode": self.mode,
            "items": [item.to_dict() for item in self.items],
            "source": self.source,
            "valid": self.valid,
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SelectionCommand":
        raw_items = value.get("items") or ()
        return cls(
            mode=str(value.get("mode") or ""),
            items=tuple(
                SelectionItem.from_dict(item)
                for item in raw_items
                if isinstance(item, Mapping)
            ),
            source=str(value.get("source") or ""),
        )


@dataclass(frozen=True, slots=True)
class SelectionState:
    items: tuple[SelectionItem, ...] = field(default_factory=tuple)
    revision: int = 0

    @property
    def empty(self) -> bool:
        return not self.items

    @property
    def selected_ids(self) -> tuple[str, ...]:
        return tuple(item.primitive_id for item in self.items)

    def contains(self, primitive_id: str) -> bool:
        return any(item.primitive_id == primitive_id for item in self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.selection-state",
            "version": "1.0",
            "items": [item.to_dict() for item in self.items],
            "selected_ids": list(self.selected_ids),
            "revision": self.revision,
            "empty": self.empty,
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SelectionState":
        raw_items = value.get("items") or ()
        return cls(
            items=tuple(
                SelectionItem.from_dict(item)
                for item in raw_items
                if isinstance(item, Mapping)
            ),
            revision=max(0, int(value.get("revision") or 0)),
        )


class VisualizationSelectionEngine:
    """Apply deterministic selection commands to immutable selection state."""

    def apply(
        self,
        state: SelectionState | Mapping[str, Any],
        command: SelectionCommand | Mapping[str, Any],
    ) -> SelectionState:
        resolved_state = state if isinstance(state, SelectionState) else SelectionState.from_dict(state)
        resolved_command = command if isinstance(command, SelectionCommand) else SelectionCommand.from_dict(command)
        if not resolved_command.valid:
            raise ValueError("selection command is invalid")

        current = {item.primitive_id: item for item in resolved_state.items}
        incoming = {item.primitive_id: item for item in resolved_command.items}
        mode = resolved_command.mode

        if mode == "clear":
            updated: dict[str, SelectionItem] = {}
        elif mode == "replace":
            updated = dict(incoming)
        elif mode == "add":
            updated = dict(current)
            updated.update(incoming)
        elif mode == "remove":
            updated = {key: item for key, item in current.items() if key not in incoming}
        else:  # toggle
            updated = dict(current)
            for key, item in incoming.items():
                if key in updated:
                    del updated[key]
                else:
                    updated[key] = item

        items = tuple(updated[key] for key in sorted(updated))
        if items == resolved_state.items:
            return resolved_state
        return SelectionState(items=items, revision=resolved_state.revision + 1)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
