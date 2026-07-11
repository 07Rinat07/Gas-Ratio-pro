from __future__ import annotations

import pytest

from services.las_viewer_render_pipeline import LasViewerRenderPipeline
from services.las_viewer_session import LasViewerSession
from services.las_viewer_track_configuration import LasViewerTrackConfigurationController


def _payload():
    return {
        "project_id": "project-1",
        "las_id": "well-a.las",
        "depth_curve": "DEPT",
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1200.0},
        "tracks": [
            {"id": "track.gamma", "title": "Gamma", "width": 1.0},
            {"id": "track.gas", "title": "Gas", "width": 1.0},
        ],
        "curves": [
            {"mnemonic": "GR", "track_id": "track.gamma", "points": [[1000, 10], [1200, 30]]},
            {"mnemonic": "TG", "track_id": "track.gas", "points": [[1000, 1], [1200, 3]]},
        ],
        "visible_tracks": ["track.gamma", "track.gas"],
        "viewport_prefetch": False,
    }


def test_configuration_coordinates_order_width_scale_and_visibility():
    session = LasViewerSession(_payload())
    controller = LasViewerTrackConfigurationController(session)

    controller.move("track.gas", 0)
    controller.set_width("track.gas", 2.5)
    controller.set_scale("track.gas", scale_type="log", minimum=0.1, maximum=100.0)
    result = controller.set_visible("track.gamma", False)

    assert result.state.layout.track_order == ("track.gas", "track.gamma")
    gas = result.state.layout.tracks[0]
    assert gas.width == 2.5
    assert gas.scale == {"scale_type": "log", "minimum": 0.1, "maximum": 100.0}
    assert result.state.visible_tracks == ("track.gas",)
    assert result.state.layout.visible_tracks == ("track.gas",)


def test_configuration_round_trip_preserves_scale_without_raw_dataframe():
    controller = LasViewerTrackConfigurationController(LasViewerSession(_payload()))
    state = controller.set_scale("track.gamma", minimum=0, maximum=150).state
    restored = LasViewerTrackConfigurationController.from_state(state.to_dict())

    snapshot = restored.viewer.snapshot()
    gamma = restored.viewer.state.layout.tracks[0]
    assert gamma.scale["maximum"] == 150.0
    assert "dataframe" not in str(snapshot).lower()


def test_scale_is_applied_to_track_and_curve_render_contract():
    payload = _payload()
    session = LasViewerSession(payload)
    LasViewerTrackConfigurationController(session).set_scale(
        "track.gas", scale_type="log", minimum=0.1, maximum=10.0
    )

    result = LasViewerRenderPipeline().run(payload, session)
    track = next(item for item in result.payload["tracks"] if item["id"] == "track.gas")
    curve = next(item for item in result.payload["curves"] if item["mnemonic"] == "TG")
    assert track["axis"] == {"scale_type": "log", "minimum": 0.1, "maximum": 10.0}
    assert curve["axis"] == {"scale_type": "log", "minimum": 0.1, "maximum": 10.0}


def test_invalid_scale_is_rejected():
    controller = LasViewerTrackConfigurationController(LasViewerSession(_payload()))
    with pytest.raises(ValueError):
        controller.set_scale("track.gas", scale_type="log", minimum=0, maximum=10)
    with pytest.raises(ValueError):
        controller.set_scale("track.gas", scale_type="sqrt")
    with pytest.raises(ValueError):
        controller.set_scale("track.gas", minimum=10, maximum=1)
