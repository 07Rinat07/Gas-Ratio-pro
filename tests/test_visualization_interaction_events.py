from __future__ import annotations

import pytest

from services.visualization_cursor import CursorRequest
from services.visualization_interaction_events import (
    InteractionEventType,
    VisualizationInteractionEvent,
    VisualizationInteractionEventDispatcher,
)
from services.visualization_interaction_session import VisualizationInteractionSession
from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_render_model import RenderPrimitive, VisualizationRenderModel
from services.visualization_selection import SelectionCommand, SelectionItem
from services.visualization_viewport_controller import ViewportCommand


def _viewport() -> InteractiveViewport:
    return InteractiveViewport(1000.0, 1100.0, 0.0, 500.0, inverted=True, unit="M")


def _model() -> VisualizationRenderModel:
    primitive = RenderPrimitive(
        "curve.gr",
        "polyline",
        10,
        {"points": [{"x": 10.0, "y": 250.0}, {"x": 100.0, "y": 250.0}], "source_layer_id": "GR"},
        track_id="track.logs",
    )
    return VisualizationRenderModel(width=200, height=500, primitives=(primitive,))


def _selection_command() -> SelectionCommand:
    return SelectionCommand(
        mode="replace",
        items=(SelectionItem("curve.gr", "polyline", "track.logs", "GR", "curve"),),
    )


def test_viewport_event_serialization_round_trip():
    event = VisualizationInteractionEvent.viewport(
        ViewportCommand.zoom(2.0), source="viewer", correlation_id="e-1"
    )

    restored = VisualizationInteractionEvent.from_dict(event.to_dict())

    assert restored.kind is InteractionEventType.VIEWPORT_COMMAND
    assert restored.source == "viewer"
    assert restored.correlation_id == "e-1"
    assert restored.valid is True


def test_dispatches_viewport_command():
    session = VisualizationInteractionSession(_viewport())
    dispatcher = VisualizationInteractionEventDispatcher()

    state = dispatcher.dispatch(session, VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0)))

    assert state.viewport.domain_span == 50.0


def test_dispatches_selection_command():
    session = VisualizationInteractionSession(_viewport())
    dispatcher = VisualizationInteractionEventDispatcher()

    state = dispatcher.dispatch(session, VisualizationInteractionEvent.selection(_selection_command()))

    assert state.selection.selected_ids == ("curve.gr",)


def test_dispatches_cursor_update_with_model():
    session = VisualizationInteractionSession(_viewport())
    dispatcher = VisualizationInteractionEventDispatcher()

    state = dispatcher.dispatch(
        session,
        VisualizationInteractionEvent.cursor(CursorRequest(50.0, 250.0, track_id="track.logs")),
        model=_model(),
    )

    assert state.cursor is not None
    assert state.cursor.depth == 1050.0


def test_cursor_update_requires_model():
    session = VisualizationInteractionSession(_viewport())
    dispatcher = VisualizationInteractionEventDispatcher()

    with pytest.raises(ValueError, match="requires render model"):
        dispatcher.dispatch(session, VisualizationInteractionEvent.cursor(CursorRequest(50.0, 250.0)))


def test_dispatches_cursor_clear():
    session = VisualizationInteractionSession(_viewport())
    dispatcher = VisualizationInteractionEventDispatcher()
    dispatcher.dispatch(session, VisualizationInteractionEvent.cursor(CursorRequest(50.0, 250.0)), model=_model())

    state = dispatcher.dispatch(session, VisualizationInteractionEvent.simple(InteractionEventType.CURSOR_CLEAR))

    assert state.cursor is None


def test_dispatches_undo_and_redo():
    session = VisualizationInteractionSession(_viewport())
    dispatcher = VisualizationInteractionEventDispatcher()
    dispatcher.dispatch(session, VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0)))

    undone = dispatcher.dispatch(session, VisualizationInteractionEvent.simple(InteractionEventType.VIEWPORT_UNDO))
    redone = dispatcher.dispatch(session, VisualizationInteractionEvent.simple(InteractionEventType.VIEWPORT_REDO))

    assert undone.viewport == _viewport()
    assert redone.viewport.domain_span == 50.0


def test_dispatches_reset():
    session = VisualizationInteractionSession(_viewport())
    dispatcher = VisualizationInteractionEventDispatcher()
    dispatcher.dispatch(session, VisualizationInteractionEvent.selection(_selection_command()))

    state = dispatcher.dispatch(session, VisualizationInteractionEvent.simple(InteractionEventType.RESET))

    assert state.selection.empty is True


def test_mapping_event_is_supported():
    session = VisualizationInteractionSession(_viewport())
    dispatcher = VisualizationInteractionEventDispatcher()
    event = VisualizationInteractionEvent.viewport(ViewportCommand.pan_domain(10.0)).to_dict()

    state = dispatcher.dispatch(session, event)

    assert state.viewport.domain_start == 1010.0


def test_invalid_payload_is_rejected():
    event = VisualizationInteractionEvent(InteractionEventType.VIEWPORT_COMMAND, {})

    assert event.valid is False
    with pytest.raises(ValueError):
        VisualizationInteractionEventDispatcher().dispatch(VisualizationInteractionSession(_viewport()), event)


def test_simple_rejects_payload_event_types():
    with pytest.raises(ValueError, match="requires a payload"):
        VisualizationInteractionEvent.simple(InteractionEventType.CURSOR_UPDATE)
