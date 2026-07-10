from __future__ import annotations

import pytest

from services.visualization_selection import (
    SelectionCommand,
    SelectionController,
    SelectionItem,
    SelectionState,
    SelectionTransition,
)


def _item(name: str) -> SelectionItem:
    return SelectionItem(
        primitive_id=f"curve.{name}",
        primitive_kind="polyline",
        track_id="track.logs",
        source_layer_id=name,
        data_kind="curve",
    )


def _command(mode: str, *names: str) -> SelectionCommand:
    return SelectionCommand(mode=mode, items=tuple(_item(name) for name in names), source="test")


def test_controller_executes_selection_commands_and_records_history():
    controller = SelectionController()

    current = controller.execute(_command("replace", "GR"))

    assert current.selected_ids == ("curve.GR",)
    assert controller.current == current
    assert controller.can_undo is True
    assert controller.can_redo is False
    assert controller.undo_depth == 1


def test_controller_undo_and_redo_restore_exact_states():
    controller = SelectionController()
    first = controller.execute(_command("replace", "GR"))
    second = controller.execute(_command("add", "RHOB"))

    assert controller.undo() == first
    assert controller.undo() == SelectionState()
    assert controller.redo() == first
    assert controller.redo() == second


def test_new_command_after_undo_discards_redo_branch():
    controller = SelectionController()
    controller.execute(_command("replace", "GR"))
    controller.execute(_command("add", "RHOB"))
    controller.undo()

    controller.execute(_command("add", "NPHI"))

    assert controller.can_redo is False
    assert controller.redo_depth == 0


def test_no_op_command_is_not_recorded():
    initial = SelectionState(items=(_item("GR"),), revision=7)
    controller = SelectionController(initial)

    result = controller.execute(_command("add", "GR"))

    assert result is initial
    assert controller.undo_depth == 0


def test_history_limit_keeps_only_latest_transitions():
    controller = SelectionController(history_limit=2)
    controller.execute(_command("replace", "GR"))
    controller.execute(_command("add", "RHOB"))
    controller.execute(_command("add", "NPHI"))

    assert controller.undo_depth == 2
    assert controller.undo().selected_ids == ("curve.GR", "curve.RHOB")
    assert controller.undo().selected_ids == ("curve.GR",)
    assert controller.undo().selected_ids == ("curve.GR",)


def test_zero_history_limit_executes_without_undo_storage():
    controller = SelectionController(history_limit=0)

    controller.execute(_command("replace", "GR"))

    assert controller.current.selected_ids == ("curve.GR",)
    assert controller.can_undo is False


def test_controller_accepts_serialized_state_and_command():
    initial = SelectionState(items=(_item("GR"),), revision=3)
    controller = SelectionController(initial.to_dict())

    result = controller.execute(_command("add", "RHOB").to_dict())

    assert result.selected_ids == ("curve.GR", "curve.RHOB")


def test_reset_restores_initial_selection_as_recorded_transition():
    initial = SelectionState(items=(_item("GR"),), revision=4)
    controller = SelectionController(initial)
    controller.execute(_command("replace", "RHOB"))

    reset = controller.reset(source="toolbar")

    assert reset.selected_ids == ("curve.GR",)
    assert reset.revision == 6
    assert controller.undo().selected_ids == ("curve.RHOB",)


def test_clear_history_keeps_current_state():
    controller = SelectionController()
    controller.execute(_command("replace", "GR"))

    controller.clear_history()

    assert controller.current.selected_ids == ("curve.GR",)
    assert controller.can_undo is False
    assert controller.can_redo is False


def test_snapshot_is_renderer_neutral_serializable_contract():
    controller = SelectionController(history_limit=8)
    controller.execute(_command("replace", "GR"))

    snapshot = controller.snapshot()

    assert snapshot["schema"] == "visualization.interactive.selection-controller"
    assert snapshot["history_limit"] == 8
    assert snapshot["undo_depth"] == 1
    assert snapshot["current"]["selected_ids"] == ["curve.GR"]
    assert snapshot["renderer_neutral"] is True


def test_transition_serializes_before_after_and_command():
    before = SelectionState()
    command = _command("replace", "GR")
    after = SelectionState(items=(_item("GR"),), revision=1)

    payload = SelectionTransition(command, before, after).to_dict()

    assert payload["changed"] is True
    assert payload["command"]["mode"] == "replace"
    assert payload["after"]["selected_ids"] == ["curve.GR"]


def test_invalid_controller_configuration_is_rejected():
    with pytest.raises(ValueError, match="history_limit"):
        SelectionController(history_limit=-1)

    invalid = SelectionState(items=(SelectionItem(primitive_id=""),))
    with pytest.raises(ValueError, match="invalid items"):
        SelectionController(invalid)
