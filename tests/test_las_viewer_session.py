from __future__ import annotations

import pytest

from services.las_viewer_session import LasViewerSession, LasViewerState
from services.visualization_viewport_controller import ViewportCommand


def _payload():
    return {
        "project_id": "project-1",
        "las_id": "well-a.las",
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1200.0},
        "tracks": [
            {"id": "track.gamma"},
            {"id": "track.gas"},
        ],
        "curves": [
            {"mnemonic": "GR", "track_id": "track.gamma"},
            {"mnemonic": "TG", "track_id": "track.gas"},
            {"mnemonic": "C1", "track_id": "track.gas"},
        ],
        "visible_tracks": ["track.gamma", "track.gas"],
    }


def test_session_builds_initial_las_viewer_state():
    state = LasViewerSession(_payload()).state

    assert state.project_id == "project-1"
    assert state.las_id == "well-a.las"
    assert state.visible_tracks == ("track.gamma", "track.gas")
    assert state.visible_curves == ("GR", "TG", "C1")
    assert state.active_track_id == "track.gamma"
    assert state.active_curve_id == "GR"


def test_session_builds_depth_limited_viewport():
    viewport = LasViewerSession(_payload(), screen_stop=800).state.interaction.viewport

    assert viewport.domain_start == 1000.0
    assert viewport.domain_stop == 1200.0
    assert viewport.screen_stop == 800.0
    assert viewport.limits.minimum == 1000.0
    assert viewport.limits.maximum == 1200.0


def test_hiding_track_hides_its_curves_and_selects_next_track():
    session = LasViewerSession(_payload())

    state = session.set_track_visible("track.gamma", False)

    assert state.visible_tracks == ("track.gas",)
    assert state.visible_curves == ("TG", "C1")
    assert state.active_track_id == "track.gas"
    assert state.active_curve_id == "TG"


def test_showing_track_restores_its_curves():
    session = LasViewerSession(_payload())
    session.set_track_visible("track.gas", False)

    state = session.set_track_visible("track.gas", True)

    assert state.visible_tracks == ("track.gamma", "track.gas")
    assert state.visible_curves == ("GR", "TG", "C1")


def test_activate_curve_updates_active_track():
    session = LasViewerSession(_payload())

    state = session.activate_curve("C1")

    assert state.active_curve_id == "C1"
    assert state.active_track_id == "track.gas"


def test_unknown_or_hidden_objects_are_rejected():
    session = LasViewerSession(_payload())
    session.set_track_visible("track.gas", False)

    with pytest.raises(ValueError):
        session.activate_track("track.gas")
    with pytest.raises(ValueError):
        session.activate_curve("TG")
    with pytest.raises(ValueError):
        session.set_track_visible("track.unknown", True)


def test_interaction_revision_is_reflected_in_viewer_state():
    session = LasViewerSession(_payload())

    session.interaction_session.execute_viewport(ViewportCommand.zoom(2.0))

    assert session.state.interaction.viewport.domain_span == 100.0
    assert session.state.revision == 1


def test_state_round_trip_preserves_serializable_contract():
    session = LasViewerSession(_payload())
    session.activate_curve("TG")
    payload = session.state.to_dict()

    restored = LasViewerState.from_dict(payload)

    assert restored.to_dict() == payload
    assert payload["schema"] == "las.viewer.state"
    assert payload["renderer_neutral"] is True


def test_snapshot_contains_viewer_and_interaction_contracts():
    payload = LasViewerSession(_payload()).snapshot()

    assert payload["schema"] == "las.viewer.session"
    assert payload["state"]["las_id"] == "well-a.las"
    assert payload["interaction"]["schema"] == "visualization.interactive.session"


def test_viewer_state_contains_renderer_neutral_layout():
    session = LasViewerSession(_payload())
    layout = session.layout_controller

    layout.move_track("track.gas", 0)
    layout.set_track_width("track.gas", 2.0)
    state = session.state

    assert state.layout is not None
    assert state.layout.track_order == ("track.gas", "track.gamma")
    assert state.layout.tracks[0].width == 2.0
    assert state.revision == 2


def test_viewer_state_round_trip_preserves_layout():
    session = LasViewerSession(_payload())
    session.layout_controller.set_curve_visible("C1", False)

    restored = LasViewerSession.from_state(session.state.to_dict())

    assert restored.state.layout == session.state.layout
    assert restored.state.to_dict()["version"] == "1.1"
