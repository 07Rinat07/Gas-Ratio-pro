from __future__ import annotations

from services.las_viewer_multitrack_builder import LasViewerMultiTrackBuilder
from services.las_viewer_navigation import LasViewerNavigationController


def _payload(point_count: int = 101) -> dict:
    points = [[1000.0 + index, float(index % 50)] for index in range(point_count)]
    stop = points[-1][0]
    return {
        "project_id": "project-1",
        "las_id": "large-well.las",
        "depth_curve": "DEPT",
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": stop},
        "tracks": [
            {"id": "track.gamma", "title": "Gamma", "width": 1.0},
            {"id": "track.gas", "title": "Gas", "width": 1.0},
        ],
        "curves": [
            {"mnemonic": "GR", "track_id": "track.gamma", "points": points},
            {"mnemonic": "TG", "track_id": "track.gas", "points": points},
        ],
    }


def _controller(point_count: int = 101) -> LasViewerNavigationController:
    prepared = LasViewerMultiTrackBuilder().build(_payload(point_count)).payload
    return LasViewerNavigationController(prepared)


def test_zoom_pan_fit_and_reset_use_one_shared_depth_viewport() -> None:
    controller = _controller()

    zoomed = controller.zoom(2.0, anchor_depth=1050.0)
    assert zoomed.profile.viewport_start == 1025.0
    assert zoomed.profile.viewport_stop == 1075.0
    assert zoomed.interaction.to_dict()["visible_tracks"] == ["track.gamma", "track.gas"]

    panned = controller.pan_depth(10.0)
    assert panned.profile.viewport_start == 1035.0
    assert panned.profile.viewport_stop == 1085.0

    fitted = controller.fit(1040.0, 1060.0)
    assert fitted.profile.viewport_start == 1040.0
    assert fitted.profile.viewport_stop == 1060.0

    reset = controller.reset()
    assert reset.profile.viewport_start == 1000.0
    assert reset.profile.viewport_stop == 1100.0


def test_pan_is_clamped_to_las_depth_limits() -> None:
    controller = _controller()
    controller.zoom(4.0)
    result = controller.pan_depth(10_000.0)

    assert result.profile.viewport_stop == 1100.0
    assert result.profile.viewport_start == 1075.0


def test_fit_without_arguments_restores_full_source_range() -> None:
    controller = _controller()
    controller.zoom(5.0)

    result = controller.fit()

    assert result.profile.viewport_start == 1000.0
    assert result.profile.viewport_stop == 1100.0


def test_repeated_render_reuses_bounded_viewport_cache() -> None:
    controller = _controller()
    first = controller.render()
    second = controller.render()

    assert first.profile.cache_hit is False
    assert second.profile.cache_hit is True
    assert second.profile.cache_entries >= 1


def test_large_las_navigation_filters_visible_points_and_keeps_compact_state() -> None:
    controller = _controller(point_count=20_001)

    result = controller.fit(5000.0, 5100.0)
    contract = result.to_dict()

    assert result.ok is True
    assert result.profile.source_point_count == 40_002
    assert result.profile.visible_point_count < result.profile.source_point_count
    assert result.profile.stable_large_las is True
    assert contract["raw_dataframe_included"] is False
    assert "dataframe" not in str(contract["interaction"]["viewer_state"]).lower()


def test_navigation_contract_is_renderer_neutral() -> None:
    result = _controller().zoom_at_screen(2.0, 500.0).to_dict()

    assert result["schema"] == "las.viewer.navigation.result"
    assert result["renderer_neutral"] is True
    assert result["profile"]["renderer_neutral"] is True
