from __future__ import annotations

import pytest

from services.visualization_cursor import CursorRequest, VisualizationCursorEngine
from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_render_model import RenderClipRegion, RenderPrimitive, VisualizationRenderModel
from services.visualization_spatial_index import VisualizationSpatialIndex


def _model() -> VisualizationRenderModel:
    return VisualizationRenderModel(
        width=300,
        height=600,
        clip_regions=(RenderClipRegion("clip.track", 10, 50, 180, 500),),
        primitives=(
            RenderPrimitive(
                "curve.GR",
                "polyline",
                30,
                {
                    "points": [[50, 100], [80, 200], [120, 300]],
                    "data_kind": "curve",
                    "source_layer_id": "GR",
                    "title": "GR",
                },
                track_id="track",
                clip_id="clip.track",
            ),
        ),
    )


def _viewport() -> InteractiveViewport:
    return InteractiveViewport(1000, 1100, 50, 550, inverted=True, unit="M")


def test_cursor_request_contract_and_validation():
    request = CursorRequest(10, 20, tolerance=5, track_id="track")
    assert request.valid is True
    assert request.to_dict()["schema"] == "visualization.interactive.cursor-request"
    assert CursorRequest(0, 0, tolerance=-1).valid is False


def test_cursor_resolves_depth_and_nearest_curve():
    readout = VisualizationCursorEngine().resolve(
        _model(), _viewport(), CursorRequest(80, 200, tolerance=1, track_id="track")
    )
    assert readout.depth == pytest.approx(1030.0)
    assert readout.depth_unit == "M"
    assert readout.hit is True
    assert readout.nearest is not None
    assert readout.nearest.primitive_id == "curve.GR"


def test_cursor_supports_serialized_contracts():
    readout = VisualizationCursorEngine().resolve(
        _model().to_dict(), _viewport().to_dict(), CursorRequest(80, 200, tolerance=1)
    )
    assert readout.hit is True


def test_cursor_reuses_compatible_spatial_index():
    model = _model()
    index = VisualizationSpatialIndex.build(model, cell_size=32)
    readout = VisualizationCursorEngine().resolve(
        model, _viewport(), CursorRequest(80, 200, tolerance=1), spatial_index=index
    )
    assert readout.hit is True
    assert "hit_test_spatial_index_used" in readout.diagnostics


def test_cursor_outside_viewport_can_clamp_depth():
    readout = VisualizationCursorEngine().resolve(
        _model(), _viewport(), CursorRequest(20, 0, tolerance=1, clamp_depth=True)
    )
    assert readout.depth == pytest.approx(1000.0)
    assert "cursor_outside_viewport" in readout.diagnostics


def test_cursor_outside_viewport_can_extrapolate_depth():
    readout = VisualizationCursorEngine().resolve(
        _model(), _viewport(), CursorRequest(20, 0, tolerance=1, clamp_depth=False)
    )
    assert readout.depth == pytest.approx(990.0)


def test_track_filter_is_forwarded_to_hit_testing():
    readout = VisualizationCursorEngine().resolve(
        _model(), _viewport(), CursorRequest(80, 200, tolerance=5, track_id="other")
    )
    assert readout.hit is False


def test_invalid_request_is_rejected():
    with pytest.raises(ValueError, match="cursor request"):
        VisualizationCursorEngine().resolve(
            _model(), _viewport(), CursorRequest(0, 0, tolerance=-1)
        )


def test_invalid_viewport_is_rejected():
    with pytest.raises(ValueError, match="viewport"):
        VisualizationCursorEngine().resolve(
            _model(), InteractiveViewport(10, 10, 0, 100), CursorRequest(10, 10)
        )


def test_readout_serialization_is_deterministic():
    engine = VisualizationCursorEngine()
    request = CursorRequest(80, 200, tolerance=1)
    first = engine.resolve(_model(), _viewport(), request).to_dict()
    second = engine.resolve(_model(), _viewport(), request).to_dict()
    assert first == second
    assert first["schema"] == "visualization.interactive.cursor-readout"
    assert first["renderer_neutral"] is True
