"""Coordinated renderer-neutral state for visualization interactions.

The session composes viewport, cursor and selection services without moving
interaction rules into UI adapters. It is intentionally small and serializable
so Workspace Session and Event Bus integrations can use one stable contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from services.visualization_cursor import CursorReadout, CursorRequest, VisualizationCursorEngine
from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_render_model import VisualizationRenderModel
from services.visualization_selection import SelectionCommand, SelectionController, SelectionState
from services.visualization_spatial_index import VisualizationSpatialIndex
from services.visualization_viewport_controller import ViewportCommand, ViewportController


@dataclass(frozen=True, slots=True)
class InteractionSessionState:
    viewport: InteractiveViewport
    selection: SelectionState
    cursor: CursorReadout | None = None
    revision: int = 0

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InteractionSessionState":
        raw_viewport = value.get("viewport")
        raw_selection = value.get("selection")
        if not isinstance(raw_viewport, Mapping) or not isinstance(raw_selection, Mapping):
            raise ValueError("interaction session state requires viewport and selection")
        raw_cursor = value.get("cursor")
        return cls(
            viewport=InteractiveViewport.from_dict(raw_viewport),
            selection=SelectionState.from_dict(raw_selection),
            cursor=(CursorReadout.from_dict(raw_cursor) if isinstance(raw_cursor, Mapping) else None),
            revision=max(0, int(value.get("revision") or 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.session-state",
            "version": "1.0",
            "viewport": self.viewport.to_dict(),
            "selection": self.selection.to_dict(),
            "cursor": self.cursor.to_dict() if self.cursor is not None else None,
            "revision": self.revision,
            "renderer_neutral": True,
        }


class VisualizationInteractionSession:
    """Synchronize viewport, cursor and selection interaction state."""

    def __init__(
        self,
        initial_viewport: InteractiveViewport,
        *,
        initial_selection: SelectionState | Mapping[str, Any] | None = None,
        history_limit: int = 100,
        cursor_engine: VisualizationCursorEngine | None = None,
    ) -> None:
        self._viewport = ViewportController(initial_viewport, history_limit=history_limit)
        self._selection = SelectionController(initial_selection, history_limit=history_limit)
        self._cursor_engine = cursor_engine or VisualizationCursorEngine()
        self._cursor: CursorReadout | None = None
        self._revision = 0

    @classmethod
    def from_state(
        cls,
        state: InteractionSessionState | Mapping[str, Any],
        *,
        history_limit: int = 100,
        cursor_engine: VisualizationCursorEngine | None = None,
    ) -> "VisualizationInteractionSession":
        resolved = state if isinstance(state, InteractionSessionState) else InteractionSessionState.from_dict(state)
        session = cls(
            resolved.viewport,
            initial_selection=resolved.selection,
            history_limit=history_limit,
            cursor_engine=cursor_engine,
        )
        session._cursor = resolved.cursor
        session._revision = resolved.revision
        return session

    @property
    def state(self) -> InteractionSessionState:
        return InteractionSessionState(
            viewport=self._viewport.current,
            selection=self._selection.current,
            cursor=self._cursor,
            revision=self._revision,
        )

    @property
    def viewport_controller(self) -> ViewportController:
        return self._viewport

    @property
    def selection_controller(self) -> SelectionController:
        return self._selection

    def execute_viewport(self, command: ViewportCommand) -> InteractionSessionState:
        before = self._viewport.current
        after = self._viewport.execute(command)
        if after != before:
            self._cursor = None
            self._revision += 1
        return self.state

    def execute_selection(
        self,
        command: SelectionCommand | Mapping[str, Any],
    ) -> InteractionSessionState:
        before = self._selection.current
        after = self._selection.execute(command)
        if after != before:
            self._revision += 1
        return self.state

    def update_cursor(
        self,
        model: VisualizationRenderModel | Mapping[str, Any],
        request: CursorRequest,
        *,
        spatial_index: VisualizationSpatialIndex | None = None,
    ) -> InteractionSessionState:
        readout = self._cursor_engine.resolve(
            model,
            self._viewport.current,
            request,
            spatial_index=spatial_index,
        )
        if readout != self._cursor:
            self._cursor = readout
            self._revision += 1
        return self.state

    def clear_cursor(self) -> InteractionSessionState:
        if self._cursor is not None:
            self._cursor = None
            self._revision += 1
        return self.state

    def undo_viewport(self) -> InteractionSessionState:
        before = self._viewport.current
        after = self._viewport.undo()
        if after != before:
            self._cursor = None
            self._revision += 1
        return self.state

    def redo_viewport(self) -> InteractionSessionState:
        before = self._viewport.current
        after = self._viewport.redo()
        if after != before:
            self._cursor = None
            self._revision += 1
        return self.state

    def undo_selection(self) -> InteractionSessionState:
        before = self._selection.current
        after = self._selection.undo()
        if after != before:
            self._revision += 1
        return self.state

    def redo_selection(self) -> InteractionSessionState:
        before = self._selection.current
        after = self._selection.redo()
        if after != before:
            self._revision += 1
        return self.state

    def reset(self) -> InteractionSessionState:
        changed = False
        if self._viewport.current != self._viewport.initial:
            self._viewport.execute(ViewportCommand.reset(source="interaction-session"))
            changed = True
        if self._selection.current != self._selection.initial:
            self._selection.reset(source="interaction-session")
            changed = True
        if self._cursor is not None:
            self._cursor = None
            changed = True
        if changed:
            self._revision += 1
        return self.state

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.session",
            "version": "1.0",
            "state": self.state.to_dict(),
            "viewport_controller": self._viewport.snapshot(),
            "selection_controller": self._selection.snapshot(),
            "renderer_neutral": True,
        }
