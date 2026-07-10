from __future__ import annotations

import pytest

from services.visualization_hit_testing import HitTestResult
from services.visualization_selection import (
    SelectionCommand,
    SelectionItem,
    SelectionState,
    VisualizationSelectionEngine,
)


def _hit(primitive_id: str, *, track_id: str = "track") -> HitTestResult:
    return HitTestResult(
        primitive_id=primitive_id,
        primitive_kind="polyline",
        track_id=track_id,
        source_layer_id=primitive_id.removeprefix("curve."),
        data_kind="curve",
        distance=1.0,
        hit_x=10.0,
        hit_y=20.0,
        query_x=11.0,
        query_y=20.0,
        z_index=30,
        segment_index=2,
        point_index=3,
        segment_ratio=0.4,
        payload={"title": primitive_id},
    )


def test_selection_item_is_created_from_hit():
    item = SelectionItem.from_hit(_hit("curve.GR"))
    assert item.primitive_id == "curve.GR"
    assert item.segment_index == 2
    assert item.payload["title"] == "curve.GR"


def test_replace_selection():
    engine = VisualizationSelectionEngine()
    initial = SelectionState(items=(SelectionItem.from_hit(_hit("curve.GR")),))
    result = engine.apply(initial, SelectionCommand.from_hits([_hit("curve.RHOB")]))
    assert result.selected_ids == ("curve.RHOB",)
    assert result.revision == 1


def test_add_selection_is_deduplicated_and_sorted():
    engine = VisualizationSelectionEngine()
    initial = SelectionState(items=(SelectionItem.from_hit(_hit("curve.RHOB")),))
    result = engine.apply(initial, SelectionCommand.from_hits([_hit("curve.GR"), _hit("curve.RHOB")], mode="add"))
    assert result.selected_ids == ("curve.GR", "curve.RHOB")


def test_toggle_selection_adds_and_removes():
    engine = VisualizationSelectionEngine()
    initial = SelectionState(items=(SelectionItem.from_hit(_hit("curve.GR")),))
    command = SelectionCommand.from_hits([_hit("curve.GR"), _hit("curve.RHOB")], mode="toggle")
    result = engine.apply(initial, command)
    assert result.selected_ids == ("curve.RHOB",)


def test_remove_and_clear_selection():
    engine = VisualizationSelectionEngine()
    initial = SelectionState(items=(SelectionItem.from_hit(_hit("curve.GR")), SelectionItem.from_hit(_hit("curve.RHOB"))))
    removed = engine.apply(initial, SelectionCommand.from_hits([_hit("curve.GR")], mode="remove"))
    assert removed.selected_ids == ("curve.RHOB",)
    cleared = engine.apply(removed, SelectionCommand.clear())
    assert cleared.empty is True


def test_no_op_returns_same_state_and_revision():
    engine = VisualizationSelectionEngine()
    initial = SelectionState(items=(SelectionItem.from_hit(_hit("curve.GR")),), revision=4)
    result = engine.apply(initial, SelectionCommand.from_hits([_hit("curve.GR")], mode="add"))
    assert result is initial
    assert result.revision == 4


def test_command_and_state_support_serialized_contracts():
    command = SelectionCommand.from_hits([_hit("curve.GR")], mode="add", source="las-viewer")
    restored_command = SelectionCommand.from_dict(command.to_dict())
    result = VisualizationSelectionEngine().apply(SelectionState().to_dict(), restored_command.to_dict())
    restored_state = SelectionState.from_dict(result.to_dict())
    assert restored_command.source == "las-viewer"
    assert restored_state.selected_ids == ("curve.GR",)
    assert restored_state.to_dict()["renderer_neutral"] is True


def test_invalid_mode_is_rejected():
    with pytest.raises(ValueError, match="selection command"):
        VisualizationSelectionEngine().apply(SelectionState(), SelectionCommand(mode="unknown"))


def test_empty_replace_clears_selection():
    initial = SelectionState(items=(SelectionItem.from_hit(_hit("curve.GR")),))
    result = VisualizationSelectionEngine().apply(initial, SelectionCommand(mode="replace"))
    assert result.empty is True


def test_duplicate_hits_use_last_semantic_payload():
    first = _hit("curve.GR", track_id="one")
    second = _hit("curve.GR", track_id="two")
    result = VisualizationSelectionEngine().apply(
        SelectionState(), SelectionCommand.from_hits([first, second], mode="add")
    )
    assert result.items[0].track_id == "two"
