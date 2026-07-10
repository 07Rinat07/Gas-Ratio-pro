from __future__ import annotations

from services.visualization_cursor import CursorRequest
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
        {
            "points": [{"x": 10.0, "y": 250.0}, {"x": 100.0, "y": 250.0}],
            "source_layer_id": "GR",
            "data_kind": "curve",
        },
        track_id="track.logs",
    )
    return VisualizationRenderModel(width=200, height=500, primitives=(primitive,))


def _selection() -> SelectionCommand:
    return SelectionCommand(
        mode="replace",
        items=(SelectionItem("curve.gr", "polyline", "track.logs", "GR", "curve"),),
        source="test",
    )


def test_session_starts_with_coordinated_empty_state():
    session = VisualizationInteractionSession(_viewport())

    assert session.state.viewport == _viewport()
    assert session.state.selection.empty is True
    assert session.state.cursor is None
    assert session.state.revision == 0


def test_viewport_command_updates_state_and_revision():
    session = VisualizationInteractionSession(_viewport())

    state = session.execute_viewport(ViewportCommand.zoom(2.0))

    assert state.viewport.domain_span == 50.0
    assert state.revision == 1


def test_selection_command_updates_same_session_state():
    session = VisualizationInteractionSession(_viewport())

    state = session.execute_selection(_selection())

    assert state.selection.selected_ids == ("curve.gr",)
    assert state.revision == 1


def test_cursor_resolution_uses_current_viewport():
    session = VisualizationInteractionSession(_viewport())

    state = session.update_cursor(_model(), CursorRequest(50.0, 250.0, track_id="track.logs"))

    assert state.cursor is not None
    assert state.cursor.depth == 1050.0
    assert state.cursor.hit is True


def test_viewport_change_invalidates_cursor_readout():
    session = VisualizationInteractionSession(_viewport())
    session.update_cursor(_model(), CursorRequest(50.0, 250.0))

    state = session.execute_viewport(ViewportCommand.pan_domain(10.0))

    assert state.cursor is None


def test_undo_and_redo_are_delegated_to_viewport_controller():
    session = VisualizationInteractionSession(_viewport())
    session.execute_viewport(ViewportCommand.zoom(2.0))

    assert session.undo_viewport().viewport == _viewport()
    assert session.redo_viewport().viewport.domain_span == 50.0


def test_undo_and_redo_are_delegated_to_selection_controller():
    session = VisualizationInteractionSession(_viewport())
    session.execute_selection(_selection())

    assert session.undo_selection().selection.empty is True
    assert session.redo_selection().selection.selected_ids == ("curve.gr",)


def test_no_op_does_not_increment_revision():
    session = VisualizationInteractionSession(_viewport())

    state = session.clear_cursor()

    assert state.revision == 0


def test_reset_restores_initial_state_and_clears_cursor():
    session = VisualizationInteractionSession(_viewport())
    session.execute_viewport(ViewportCommand.zoom(2.0))
    session.execute_selection(_selection())
    session.update_cursor(_model(), CursorRequest(50.0, 250.0))

    state = session.reset()

    assert state.viewport == _viewport()
    assert state.selection.empty is True
    assert state.cursor is None


def test_snapshot_is_renderer_neutral_serializable_contract():
    session = VisualizationInteractionSession(_viewport(), history_limit=12)
    session.execute_selection(_selection())

    payload = session.snapshot()

    assert payload["schema"] == "visualization.interactive.session"
    assert payload["state"]["selection"]["selected_ids"] == ["curve.gr"]
    assert payload["viewport_controller"]["history_limit"] == 12
    assert payload["renderer_neutral"] is True
