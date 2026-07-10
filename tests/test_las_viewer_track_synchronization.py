from __future__ import annotations

import pytest

from services.las_viewer_track_synchronization import LasViewerTrackSynchronizationEngine
from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_render_model import RenderClipRegion, VisualizationRenderModel


def _model():
    return VisualizationRenderModel(
        width=600,
        height=800,
        clip_regions=(
            RenderClipRegion("clip.track.gamma.plot", 10, 100, 180, 600),
            RenderClipRegion("clip.track.gas.plot", 200, 100, 390, 600),
        ),
    )


def _viewport():
    return InteractiveViewport(1000, 1200, 100, 700, inverted=True, unit="M")


def test_resolves_shared_depth_and_segments_for_all_tracks():
    result = LasViewerTrackSynchronizationEngine().resolve(_model(), _viewport(), 400)
    assert result.depth == pytest.approx(1100)
    assert result.synchronized_track_ids == ("track.gamma", "track.gas")
    assert result.segments[0].x_start == 10
    assert result.segments[1].x_stop == 590


def test_requested_track_order_is_preserved():
    result = LasViewerTrackSynchronizationEngine().resolve(
        _model(), _viewport(), 400, track_ids=("track.gas", "track.gamma")
    )
    assert result.synchronized_track_ids == ("track.gas", "track.gamma")


def test_missing_track_region_is_reported():
    result = LasViewerTrackSynchronizationEngine().resolve(
        _model(), _viewport(), 400, track_ids=("track.missing",)
    )
    assert not result.segments
    assert "track_sync_missing_region:track.missing" in result.diagnostics


def test_outside_cursor_is_clamped_to_viewport_depth():
    result = LasViewerTrackSynchronizationEngine().resolve(_model(), _viewport(), 50)
    assert result.depth == 1000
    assert "track_sync_cursor_outside_viewport" in result.diagnostics
    assert not result.synchronized_track_ids


def test_serialized_model_and_viewport_are_supported():
    result = LasViewerTrackSynchronizationEngine().resolve(
        _model().to_dict(), _viewport().to_dict(), 700
    )
    assert result.depth == 1200
    assert result.to_dict()["renderer_neutral"] is True


def test_mismatched_track_plot_geometry_is_reported():
    model = VisualizationRenderModel(
        width=600,
        height=800,
        clip_regions=(
            RenderClipRegion("clip.track.a.plot", 0, 100, 100, 600),
            RenderClipRegion("clip.track.b.plot", 100, 120, 100, 580),
        ),
    )
    result = LasViewerTrackSynchronizationEngine().resolve(model, _viewport(), 400)
    assert "track_sync_plot_geometry_mismatch:track.b" in result.diagnostics


def test_non_finite_screen_coordinate_is_rejected():
    with pytest.raises(ValueError):
        LasViewerTrackSynchronizationEngine().resolve(_model(), _viewport(), float("nan"))
