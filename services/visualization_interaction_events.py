"""Serializable event layer for renderer-neutral visualization interactions.

UI adapters emit stable events instead of mutating interaction state directly.
The dispatcher routes events to :class:`VisualizationInteractionSession`, keeping
viewport, cursor and selection rules outside presentation code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from services.visualization_cursor import CursorRequest
from services.visualization_interaction_session import (
    InteractionSessionState,
    VisualizationInteractionSession,
)
from services.visualization_render_model import VisualizationRenderModel
from services.visualization_selection import SelectionCommand
from services.visualization_spatial_index import VisualizationSpatialIndex
from services.visualization_viewport_controller import ViewportCommand


class InteractionEventType(str, Enum):
    VIEWPORT_COMMAND = "viewport_command"
    VIEWPORT_UNDO = "viewport_undo"
    VIEWPORT_REDO = "viewport_redo"
    SELECTION_COMMAND = "selection_command"
    SELECTION_UNDO = "selection_undo"
    SELECTION_REDO = "selection_redo"
    CURSOR_UPDATE = "cursor_update"
    CURSOR_CLEAR = "cursor_clear"
    RESET = "reset"


@dataclass(frozen=True, slots=True)
class VisualizationInteractionEvent:
    kind: InteractionEventType
    payload: Mapping[str, Any] = field(default_factory=dict)
    source: str = ""
    correlation_id: str = ""

    @classmethod
    def viewport(cls, command: ViewportCommand, **metadata: str) -> "VisualizationInteractionEvent":
        return cls(InteractionEventType.VIEWPORT_COMMAND, {"command": command.to_dict()}, **metadata)

    @classmethod
    def selection(cls, command: SelectionCommand, **metadata: str) -> "VisualizationInteractionEvent":
        return cls(InteractionEventType.SELECTION_COMMAND, {"command": command.to_dict()}, **metadata)

    @classmethod
    def cursor(cls, request: CursorRequest, **metadata: str) -> "VisualizationInteractionEvent":
        return cls(InteractionEventType.CURSOR_UPDATE, {"request": request.to_dict()}, **metadata)

    @classmethod
    def simple(cls, kind: InteractionEventType, **metadata: str) -> "VisualizationInteractionEvent":
        if kind in {
            InteractionEventType.VIEWPORT_COMMAND,
            InteractionEventType.SELECTION_COMMAND,
            InteractionEventType.CURSOR_UPDATE,
        }:
            raise ValueError("event kind requires a payload")
        return cls(kind, {}, **metadata)

    @property
    def valid(self) -> bool:
        try:
            self._validated_payload()
        except (TypeError, ValueError):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.event",
            "version": "1.0",
            "kind": self.kind.value,
            "payload": dict(self.payload),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "valid": self.valid,
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VisualizationInteractionEvent":
        try:
            kind = InteractionEventType(str(value.get("kind") or ""))
        except ValueError as exc:
            raise ValueError("unknown interaction event kind") from exc
        raw_payload = value.get("payload")
        payload = dict(raw_payload) if isinstance(raw_payload, Mapping) else {}
        return cls(
            kind=kind,
            payload=payload,
            source=str(value.get("source") or ""),
            correlation_id=str(value.get("correlation_id") or ""),
        )

    def _validated_payload(self) -> dict[str, Any]:
        raw = dict(self.payload)
        if self.kind is InteractionEventType.VIEWPORT_COMMAND:
            command = raw.get("command")
            if not isinstance(command, Mapping):
                raise ValueError("viewport event requires command")
            resolved = ViewportCommand.from_dict(command)
            if not resolved.valid:
                raise ValueError("viewport command is invalid")
            return {"command": resolved}
        if self.kind is InteractionEventType.SELECTION_COMMAND:
            command = raw.get("command")
            if not isinstance(command, Mapping):
                raise ValueError("selection event requires command")
            resolved = SelectionCommand.from_dict(command)
            if not resolved.valid:
                raise ValueError("selection command is invalid")
            return {"command": resolved}
        if self.kind is InteractionEventType.CURSOR_UPDATE:
            request = raw.get("request")
            if not isinstance(request, Mapping):
                raise ValueError("cursor event requires request")
            resolved = CursorRequest(
                x=float(request.get("x")),
                y=float(request.get("y")),
                tolerance=float(request.get("tolerance", 6.0)),
                track_id=str(request.get("track_id") or ""),
                max_results=int(request.get("max_results", 8)),
                clamp_depth=bool(request.get("clamp_depth", True)),
            )
            if not resolved.valid:
                raise ValueError("cursor request is invalid")
            return {"request": resolved}
        return {}


class VisualizationInteractionEventDispatcher:
    """Route interaction events to one coordinated interaction session."""

    def dispatch(
        self,
        session: VisualizationInteractionSession,
        event: VisualizationInteractionEvent | Mapping[str, Any],
        *,
        model: VisualizationRenderModel | Mapping[str, Any] | None = None,
        spatial_index: VisualizationSpatialIndex | None = None,
    ) -> InteractionSessionState:
        resolved = event if isinstance(event, VisualizationInteractionEvent) else VisualizationInteractionEvent.from_dict(event)
        payload = resolved._validated_payload()

        if resolved.kind is InteractionEventType.VIEWPORT_COMMAND:
            return session.execute_viewport(payload["command"])
        if resolved.kind is InteractionEventType.VIEWPORT_UNDO:
            return session.undo_viewport()
        if resolved.kind is InteractionEventType.VIEWPORT_REDO:
            return session.redo_viewport()
        if resolved.kind is InteractionEventType.SELECTION_COMMAND:
            return session.execute_selection(payload["command"])
        if resolved.kind is InteractionEventType.SELECTION_UNDO:
            return session.undo_selection()
        if resolved.kind is InteractionEventType.SELECTION_REDO:
            return session.redo_selection()
        if resolved.kind is InteractionEventType.CURSOR_UPDATE:
            if model is None:
                raise ValueError("cursor update event requires render model")
            return session.update_cursor(model, payload["request"], spatial_index=spatial_index)
        if resolved.kind is InteractionEventType.CURSOR_CLEAR:
            return session.clear_cursor()
        if resolved.kind is InteractionEventType.RESET:
            return session.reset()
        raise ValueError(f"unsupported interaction event: {resolved.kind}")
