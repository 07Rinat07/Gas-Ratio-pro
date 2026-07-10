from __future__ import annotations

import pytest

from services.visualization_cursor import CursorRequest
from services.visualization_interaction_events import VisualizationInteractionEvent
from services.visualization_interaction_journal import VisualizationInteractionJournal
from services.visualization_interaction_session import VisualizationInteractionSession
from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_render_model import RenderPrimitive, VisualizationRenderModel
from services.visualization_selection import SelectionCommand, SelectionItem
from services.visualization_viewport_controller import ViewportCommand


def _viewport() -> InteractiveViewport:
    return InteractiveViewport(1000.0, 1100.0, 0.0, 500.0, inverted=True, unit="M")


def _model() -> VisualizationRenderModel:
    return VisualizationRenderModel(
        width=200,
        height=500,
        primitives=(RenderPrimitive(
            "curve.gr", "polyline", 10,
            {"points": [{"x": 10.0, "y": 250.0}, {"x": 100.0, "y": 250.0}], "source_layer_id": "GR"},
            track_id="track.logs",
        ),),
    )


def _selection() -> SelectionCommand:
    return SelectionCommand(
        mode="replace",
        items=(SelectionItem("curve.gr", "polyline", "track.logs", "GR", "curve"),),
    )


def test_dispatch_and_record_tracks_revisions():
    session = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()

    state = journal.dispatch_and_record(session, VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0)))

    assert state.viewport.domain_span == 50.0
    assert len(journal.entries) == 1
    assert journal.entries[0].before_revision == 0
    assert journal.entries[0].after_revision == 1
    assert journal.entries[0].changed is True


def test_noop_event_is_recorded_without_change():
    session = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()

    journal.dispatch_and_record(session, VisualizationInteractionEvent.viewport(ViewportCommand.reset()))

    assert journal.entries[0].changed is False


def test_round_trip_preserves_entries():
    session = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    journal.dispatch_and_record(session, VisualizationInteractionEvent.viewport(ViewportCommand.pan_domain(10.0)))

    restored = VisualizationInteractionJournal.from_dict(journal.to_dict())

    assert restored.to_dict() == journal.to_dict()


def test_replay_restores_viewport_and_selection():
    source = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    journal.dispatch_and_record(source, VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0)))
    journal.dispatch_and_record(source, VisualizationInteractionEvent.selection(_selection()))

    target = VisualizationInteractionSession(_viewport())
    result = journal.replay(target)

    assert result.applied_count == 2
    assert result.changed_count == 2
    assert result.state.viewport.domain_span == 50.0
    assert result.state.selection.selected_ids == ("curve.gr",)


def test_cursor_replay_requires_model():
    source = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    journal.dispatch_and_record(
        source,
        VisualizationInteractionEvent.cursor(CursorRequest(50.0, 250.0)),
        model=_model(),
    )

    with pytest.raises(ValueError, match="requires render model"):
        journal.replay(VisualizationInteractionSession(_viewport()))


def test_cursor_replay_with_model():
    source = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    journal.dispatch_and_record(
        source,
        VisualizationInteractionEvent.cursor(CursorRequest(50.0, 250.0)),
        model=_model(),
    )

    result = journal.replay(VisualizationInteractionSession(_viewport()), model=_model())

    assert result.state.cursor is not None
    assert result.state.cursor.depth == 1050.0


def test_cursor_can_be_skipped_without_model():
    source = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    journal.dispatch_and_record(
        source,
        VisualizationInteractionEvent.cursor(CursorRequest(50.0, 250.0)),
        model=_model(),
    )

    result = journal.replay(
        VisualizationInteractionSession(_viewport()),
        skip_cursor_without_model=True,
    )

    assert result.applied_count == 0
    assert result.skipped_count == 1


def test_invalid_sequence_is_rejected():
    value = {
        "entries": [{
            "sequence": 2,
            "event": VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0)).to_dict(),
            "before_revision": 0,
            "after_revision": 1,
        }]
    }

    with pytest.raises(ValueError, match="contiguous"):
        VisualizationInteractionJournal.from_dict(value)


def test_clear_removes_entries():
    session = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    journal.dispatch_and_record(session, VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0)))

    journal.clear()

    assert journal.entries == []
