from __future__ import annotations

import pytest

from services.las_viewer_layout import LasViewerLayoutController, LasViewerLayoutState


def _payload():
    return {
        "tracks": [
            {"id": "track.gamma", "width": 1.0},
            {"id": "track.gas", "width": 1.5},
        ],
        "curves": [
            {"mnemonic": "GR", "track_id": "track.gamma"},
            {"mnemonic": "TG", "track_id": "track.gas"},
            {"mnemonic": "C1", "track_id": "track.gas"},
        ],
        "visible_tracks": ["track.gamma", "track.gas"],
    }


def test_layout_builds_track_and_curve_order_from_payload():
    state = LasViewerLayoutController.from_payload(_payload()).state
    assert state.track_order == ("track.gamma", "track.gas")
    assert state.visible_curves == ("GR", "TG", "C1")
    assert state.tracks[1].width == 1.5


def test_track_can_be_reordered():
    controller = LasViewerLayoutController.from_payload(_payload())
    state = controller.move_track("track.gas", 0)
    assert state.track_order == ("track.gas", "track.gamma")
    assert state.revision == 1


def test_track_width_is_positive_and_revision_changes_once():
    controller = LasViewerLayoutController.from_payload(_payload())
    assert controller.set_track_width("track.gamma", 2.25).tracks[0].width == 2.25
    assert controller.state.revision == 1
    controller.set_track_width("track.gamma", 2.25)
    assert controller.state.revision == 1
    with pytest.raises(ValueError):
        controller.set_track_width("track.gamma", 0)


def test_track_visibility_updates_derived_visible_tracks_and_curves():
    controller = LasViewerLayoutController.from_payload(_payload())
    state = controller.set_track_visible("track.gas", False)
    assert state.visible_tracks == ("track.gamma",)
    assert state.visible_curves == ("GR",)


def test_curve_visibility_is_independent_within_visible_track():
    controller = LasViewerLayoutController.from_payload(_payload())
    state = controller.set_curve_visible("TG", False)
    assert state.visible_curves == ("GR", "C1")
    state = controller.set_curve_visible("TG", True)
    assert state.visible_curves == ("GR", "TG", "C1")


def test_curve_order_can_be_changed_without_losing_visibility():
    controller = LasViewerLayoutController.from_payload(_payload())
    state = controller.move_curve("C1", 0)
    gas = state.tracks[1]
    assert gas.curve_order == ("C1", "TG")
    assert gas.visible_curves == ("C1", "TG")


def test_layout_contract_round_trip_is_deterministic():
    controller = LasViewerLayoutController.from_payload(_payload())
    controller.move_track("track.gas", 0)
    payload = controller.state.to_dict()
    restored = LasViewerLayoutState.from_dict(payload)
    assert restored.to_dict() == payload
    assert payload["schema"] == "las.viewer.layout"
    assert payload["renderer_neutral"] is True


def test_unknown_track_and_curve_are_rejected():
    controller = LasViewerLayoutController.from_payload(_payload())
    with pytest.raises(ValueError):
        controller.move_track("missing", 0)
    with pytest.raises(ValueError):
        controller.set_curve_visible("missing", False)
