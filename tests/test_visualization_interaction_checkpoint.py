from __future__ import annotations

import pytest

from services.visualization_interaction_checkpoint import (
    InteractionCheckpoint,
    VisualizationInteractionCheckpointStore,
)
from services.visualization_interaction_events import VisualizationInteractionEvent
from services.visualization_interaction_journal import VisualizationInteractionJournal
from services.visualization_interaction_session import VisualizationInteractionSession
from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_selection import SelectionCommand, SelectionItem
from services.visualization_viewport_controller import ViewportCommand


def _viewport() -> InteractiveViewport:
    return InteractiveViewport(1000.0, 1100.0, 0.0, 500.0, inverted=True, unit="M")


def _selection() -> SelectionCommand:
    return SelectionCommand(
        mode="replace",
        items=(SelectionItem("curve.gr", "polyline", "track.logs", "GR", "curve"),),
    )


def test_checkpoint_round_trip_preserves_state():
    session = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    journal.dispatch_and_record(session, VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0)))
    journal.dispatch_and_record(session, VisualizationInteractionEvent.selection(_selection()))

    checkpoint = InteractionCheckpoint(session.state, len(journal.entries), checkpoint_id="cp-1")
    restored = InteractionCheckpoint.from_dict(checkpoint.to_dict())

    assert restored.to_dict() == checkpoint.to_dict()


def test_store_restores_session_without_replay():
    session = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    journal.dispatch_and_record(session, VisualizationInteractionEvent.viewport(ViewportCommand.pan_domain(10.0)))
    store = VisualizationInteractionCheckpointStore()
    checkpoint = store.create(session, journal)

    result = store.restore(checkpoint)

    assert result.session.state.to_dict() == session.state.to_dict()
    assert result.checkpoint.journal_position == 1
    assert result.replayed_count == 0


def test_store_capacity_evicts_oldest_checkpoint():
    session = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    store = VisualizationInteractionCheckpointStore(capacity=2)

    store.create(session, journal, checkpoint_id="a")
    store.create(session, journal, checkpoint_id="b")
    store.create(session, journal, checkpoint_id="c")

    assert [item.checkpoint_id for item in store.checkpoints] == ["b", "c"]


def test_store_round_trip():
    session = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    store = VisualizationInteractionCheckpointStore(capacity=3)
    store.create(session, journal, checkpoint_id="latest")

    restored = VisualizationInteractionCheckpointStore.from_dict(store.to_dict())

    assert restored.to_dict() == store.to_dict()


def test_restore_uses_latest_checkpoint():
    session = VisualizationInteractionSession(_viewport())
    journal = VisualizationInteractionJournal()
    store = VisualizationInteractionCheckpointStore()
    store.create(session, journal, checkpoint_id="initial")
    journal.dispatch_and_record(session, VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0)))
    store.create(session, journal, checkpoint_id="zoomed")

    result = store.restore()

    assert result.checkpoint.checkpoint_id == "zoomed"
    assert result.session.state.viewport.domain_span == 50.0


def test_clear_removes_checkpoints():
    store = VisualizationInteractionCheckpointStore()
    store.create(VisualizationInteractionSession(_viewport()), VisualizationInteractionJournal())

    store.clear()

    assert store.latest is None


def test_invalid_capacity_is_rejected():
    with pytest.raises(ValueError, match="positive"):
        VisualizationInteractionCheckpointStore(capacity=0)


def test_restore_without_checkpoint_is_rejected():
    with pytest.raises(ValueError, match="no interaction checkpoint"):
        VisualizationInteractionCheckpointStore().restore()
