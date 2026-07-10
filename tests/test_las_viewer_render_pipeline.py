from __future__ import annotations

from services.las_viewer_render_pipeline import LasViewerRenderPipeline
from services.las_viewer_session import LasViewerSession
from services.visualization_viewport_controller import ViewportCommand


def _payload():
    return {
        "project_id": "project-1",
        "las_id": "well-a.las",
        "source_type": "las",
        "depth_curve": "DEPT",
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1200.0},
        "tracks": [
            {"id": "track.gamma", "title": "Gamma", "width": 1.0},
            {"id": "track.gas", "title": "Gas", "width": 1.0},
        ],
        "curves": [
            {"mnemonic": "GR", "track_id": "track.gamma", "unit": "API", "points": [[1000, 10], [1100, 20], [1200, 30]]},
            {"mnemonic": "TG", "track_id": "track.gas", "unit": "%", "points": [[1000, 1], [1100, 2], [1200, 3]]},
            {"mnemonic": "C1", "track_id": "track.gas", "unit": "%", "points": [[1000, 4], [1100, 5], [1200, 6]]},
        ],
        "visible_tracks": ["track.gamma", "track.gas"],
        "viewport_prefetch": False,
    }


def test_layout_order_width_and_curve_visibility_are_applied_before_rendering():
    payload = _payload()
    session = LasViewerSession(payload)
    session.layout_controller.move_track("track.gas", 0)
    session.layout_controller.set_track_width("track.gas", 2.5)
    session.layout_controller.set_curve_visible("C1", False)

    result = LasViewerRenderPipeline().run(payload, session)

    assert [item["id"] for item in result.payload["tracks"]] == ["track.gas", "track.gamma"]
    assert result.payload["tracks"][0]["width"] == 2.5
    assert [item["mnemonic"] for item in result.payload["curves"]] == ["TG", "GR"]
    assert result.profile.rendered_track_count == 2
    assert result.profile.rendered_curve_count == 2


def test_hidden_track_and_curves_are_excluded_from_render_payload():
    payload = _payload()
    session = LasViewerSession(payload)
    session.set_track_visible("track.gamma", False)
    session.layout_controller.set_track_visible("track.gamma", False)

    result = LasViewerRenderPipeline().run(payload, session)

    assert [item["id"] for item in result.payload["tracks"]] == ["track.gas"]
    assert [item["mnemonic"] for item in result.payload["curves"]] == ["TG", "C1"]


def test_current_viewport_is_used_by_render_pipeline():
    payload = _payload()
    session = LasViewerSession(payload)
    session.interaction_session.execute_viewport(ViewportCommand.zoom(2.0))

    result = LasViewerRenderPipeline().run(payload, session)

    assert result.viewport_result.profile.applied_start == 1050.0
    assert result.viewport_result.profile.applied_stop == 1150.0
    assert result.viewport_result.payload["depth_range"] == {"start": 1050.0, "stop": 1150.0}


def test_render_metadata_and_validation_include_viewer_state():
    payload = _payload()
    session = LasViewerSession(payload)
    session.activate_curve("TG")

    result = LasViewerRenderPipeline().run(payload, session)

    assert result.payload["las_viewer"]["active_track_id"] == "track.gas"
    assert result.payload["las_viewer"]["active_curve_id"] == "TG"
    assert result.viewport_result.pipeline.validation["las_viewer_active_curve_id"] == "TG"
    assert result.to_dict()["schema"] == "las.viewer.render.result"
    assert result.to_dict()["renderer_neutral"] is True


def test_serialized_viewer_state_is_supported():
    payload = _payload()
    state = LasViewerSession(payload).state.to_dict()

    result = LasViewerRenderPipeline().run(payload, state)

    assert result.profile.rendered_track_count == 2
    assert result.viewport_result.pipeline.render_model.to_dict()["schema"] == "visualization.render.model"
