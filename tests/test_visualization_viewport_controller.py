from __future__ import annotations

import pytest

from services.visualization_interactive_viewport import InteractiveViewport, ViewportLimits
from services.visualization_viewport_controller import (
    ViewportCommand,
    ViewportCommandType,
    ViewportController,
)


def _viewport() -> InteractiveViewport:
    return InteractiveViewport(
        domain_start=1000.0,
        domain_stop=1100.0,
        screen_start=50.0,
        screen_stop=650.0,
        inverted=True,
        unit="M",
        limits=ViewportLimits(minimum=900.0, maximum=1200.0, minimum_span=1.0),
    )


def test_command_round_trip_preserves_metadata_and_parameters():
    command = ViewportCommand.zoom_at_screen(
        2.0,
        200.0,
        source="las-viewer",
        correlation_id="evt-42",
    )

    restored = ViewportCommand.from_dict(command.to_dict())

    assert restored == command
    assert restored.valid is True
    assert restored.to_dict()["renderer_neutral"] is True


def test_all_command_factories_apply_expected_operations():
    initial = _viewport()

    assert ViewportCommand.pan_domain(10).apply(initial, initial_viewport=initial).domain_start == 1010
    assert ViewportCommand.pan_pixels(60).apply(initial, initial_viewport=initial).domain_start == 990
    assert ViewportCommand.zoom(2).apply(initial, initial_viewport=initial).domain_span == 50
    assert ViewportCommand.fit(1020, 1040).apply(initial, initial_viewport=initial).domain_span == 20
    assert ViewportCommand.set_range(1030, 1060).apply(initial, initial_viewport=initial).domain_span == 30


def test_zoom_at_screen_keeps_cursor_depth_stationary():
    initial = _viewport()
    cursor = 225.0
    expected_depth = initial.screen_to_domain(cursor)

    result = ViewportCommand.zoom_at_screen(2.0, cursor).apply(initial, initial_viewport=initial)

    assert result.screen_to_domain(cursor) == pytest.approx(expected_depth)


def test_reset_returns_initial_viewport():
    initial = _viewport()
    changed = initial.zoom(2.0)

    assert ViewportCommand.reset().apply(changed, initial_viewport=initial) == initial


def test_invalid_command_parameters_are_rejected():
    malformed = ViewportCommand(ViewportCommandType.ZOOM, {"factor": 0})

    assert malformed.valid is False
    with pytest.raises(ValueError, match="positive"):
        malformed.apply(_viewport(), initial_viewport=_viewport())

    with pytest.raises(ValueError, match="unknown"):
        ViewportCommand.from_dict({"kind": "explode"})


def test_controller_executes_commands_and_records_history():
    controller = ViewportController(_viewport())

    current = controller.execute(ViewportCommand.zoom(2.0))

    assert current.domain_span == pytest.approx(50.0)
    assert controller.current == current
    assert controller.can_undo is True
    assert controller.can_redo is False
    assert controller.undo_depth == 1


def test_controller_undo_and_redo_restore_exact_states():
    controller = ViewportController(_viewport())
    zoomed = controller.execute(ViewportCommand.zoom(2.0))
    panned = controller.execute(ViewportCommand.pan_domain(10.0))

    assert controller.undo() == zoomed
    assert controller.undo() == _viewport()
    assert controller.redo() == zoomed
    assert controller.redo() == panned


def test_new_command_after_undo_discards_redo_branch():
    controller = ViewportController(_viewport())
    controller.execute(ViewportCommand.zoom(2.0))
    controller.execute(ViewportCommand.pan_domain(10.0))
    controller.undo()

    controller.execute(ViewportCommand.pan_domain(-5.0))

    assert controller.can_redo is False
    assert controller.redo_depth == 0


def test_no_op_command_is_not_recorded():
    initial = _viewport()
    controller = ViewportController(initial)

    result = controller.execute(ViewportCommand.reset())

    assert result == initial
    assert controller.undo_depth == 0


def test_history_limit_keeps_only_latest_transitions():
    controller = ViewportController(_viewport(), history_limit=2)
    controller.execute(ViewportCommand.pan_domain(5))
    controller.execute(ViewportCommand.pan_domain(5))
    controller.execute(ViewportCommand.pan_domain(5))

    assert controller.undo_depth == 2
    assert controller.undo().domain_start == pytest.approx(1010)
    assert controller.undo().domain_start == pytest.approx(1005)
    assert controller.undo().domain_start == pytest.approx(1005)


def test_zero_history_limit_executes_without_undo_storage():
    controller = ViewportController(_viewport(), history_limit=0)

    controller.execute(ViewportCommand.zoom(2))

    assert controller.current.domain_span == pytest.approx(50)
    assert controller.can_undo is False


def test_controller_snapshot_is_serializable_contract():
    controller = ViewportController(_viewport(), history_limit=8)
    controller.execute(ViewportCommand.fit(1020, 1060))

    snapshot = controller.snapshot()

    assert snapshot["schema"] == "visualization.interactive.viewport-controller"
    assert snapshot["history_limit"] == 8
    assert snapshot["undo_depth"] == 1
    assert snapshot["current"]["domain_start"] == pytest.approx(1020)
    assert snapshot["renderer_neutral"] is True


def test_invalid_controller_configuration_is_rejected():
    with pytest.raises(ValueError, match="history_limit"):
        ViewportController(_viewport(), history_limit=-1)

    invalid = InteractiveViewport(1, 1, 0, 100)
    with pytest.raises(ValueError, match="initial viewport"):
        ViewportController(invalid)
