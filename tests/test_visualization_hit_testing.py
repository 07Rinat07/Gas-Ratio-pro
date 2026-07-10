from __future__ import annotations

import pytest

from services.visualization_hit_testing import HitTestQuery, VisualizationHitTestingEngine
from services.visualization_render_model import RenderClipRegion, RenderPrimitive, VisualizationRenderModel


def _model() -> VisualizationRenderModel:
    return VisualizationRenderModel(
        width=400,
        height=600,
        clip_regions=(RenderClipRegion("clip.track.plot", 10, 50, 180, 500),),
        primitives=(
            RenderPrimitive("background", "rectangle", 0, {"x": 0, "y": 0, "width": 400, "height": 600}),
            RenderPrimitive(
                "overlay.gas", "rectangle", 12,
                {"x": 10, "y": 100, "width": 180, "height": 40, "data_kind": "interval_overlay", "source_layer_id": "gas"},
                track_id="track", clip_id="clip.track.plot",
            ),
            RenderPrimitive(
                "curve.GR", "polyline", 30,
                {"points": [{"x": 40, "y": 80}, {"x": 80, "y": 120}, {"x": 120, "y": 200}], "data_kind": "curve", "source_layer_id": "GR", "title": "GR"},
                track_id="track", clip_id="clip.track.plot",
            ),
            RenderPrimitive("hidden", "text", 100, {"x": 80, "y": 120, "text": "hidden"}, visible=False),
        ),
    )


def test_query_contract_and_validation():
    query = HitTestQuery(10, 20, tolerance=5, track_id="track", kinds=("polyline",))
    assert query.valid is True
    assert query.to_dict()["schema"] == "visualization.interactive.hit-test-query"
    assert HitTestQuery(0, 0, tolerance=-1).valid is False


def test_nearest_polyline_segment_is_returned_with_normalized_metadata():
    response = VisualizationHitTestingEngine().hit_test(
        _model(), HitTestQuery(82, 122, tolerance=5, kinds=("polyline",))
    )
    assert response.hit is True
    hit = response.nearest
    assert hit is not None
    assert hit.primitive_id == "curve.GR"
    assert hit.source_layer_id == "GR"
    assert hit.data_kind == "curve"
    assert hit.segment_index == 1
    assert hit.point_index == 1
    assert hit.distance < 3
    assert hit.payload == {"data_kind": "curve", "source_layer_id": "GR", "title": "GR"}


def test_polyline_projection_reports_segment_ratio():
    response = VisualizationHitTestingEngine().hit_test(
        _model(), HitTestQuery(60, 100, tolerance=0.01, kinds=("polyline",))
    )
    assert response.nearest is not None
    assert response.nearest.segment_index == 0
    assert response.nearest.segment_ratio == pytest.approx(0.5)
    assert response.nearest.distance == pytest.approx(0.0)


def test_rectangle_inside_hit_has_zero_distance_and_interval_identity():
    response = VisualizationHitTestingEngine().hit_test(
        _model(), HitTestQuery(20, 110, tolerance=2, kinds=("rectangle",), track_id="track")
    )
    assert response.nearest is not None
    assert response.nearest.primitive_id == "overlay.gas"
    assert response.nearest.inside is True
    assert response.nearest.distance == 0


def test_results_are_sorted_by_distance_then_topmost_z_index():
    model = VisualizationRenderModel(
        width=100, height=100,
        primitives=(
            RenderPrimitive("low", "text", 1, {"x": 50, "y": 50}),
            RenderPrimitive("high", "text", 10, {"x": 50, "y": 50}),
        ),
    )
    response = VisualizationHitTestingEngine().hit_test(model, HitTestQuery(50, 50, tolerance=1))
    assert [item.primitive_id for item in response.results] == ["high", "low"]


def test_track_and_kind_filters_reduce_results():
    response = VisualizationHitTestingEngine().hit_test(
        _model(), HitTestQuery(80, 120, tolerance=10, track_id="other", kinds=("polyline",))
    )
    assert response.hit is False


def test_hidden_primitives_are_excluded_by_default_and_can_be_included():
    engine = VisualizationHitTestingEngine()
    default = engine.hit_test(_model(), HitTestQuery(80, 120, tolerance=1, kinds=("text",)))
    included = engine.hit_test(_model(), HitTestQuery(80, 120, tolerance=1, kinds=("text",), include_hidden=True))
    assert default.hit is False
    assert included.nearest is not None
    assert included.nearest.primitive_id == "hidden"


def test_clip_region_prevents_hits_outside_track_plot():
    response = VisualizationHitTestingEngine().hit_test(
        _model(), HitTestQuery(80, 20, tolerance=100, kinds=("polyline",))
    )
    assert response.hit is False
    assert response.candidate_primitive_count == 0


def test_missing_clip_is_reported_and_primitive_skipped():
    model = VisualizationRenderModel(
        width=100, height=100,
        primitives=(RenderPrimitive("curve", "polyline", 1, {"points": [[0, 0], [10, 10]]}, clip_id="missing"),),
    )
    response = VisualizationHitTestingEngine().hit_test(model, HitTestQuery(5, 5, tolerance=2))
    assert response.hit is False
    assert response.diagnostics == ("hit_test_missing_clip:curve:missing",)


def test_serialized_render_model_is_accepted():
    response = VisualizationHitTestingEngine().hit_test(
        _model().to_dict(), HitTestQuery(60, 100, tolerance=1, kinds=("polyline",))
    )
    assert response.hit is True


def test_max_results_is_respected():
    response = VisualizationHitTestingEngine().hit_test(
        _model(), HitTestQuery(80, 120, tolerance=100, max_results=1)
    )
    assert len(response.results) == 1


def test_invalid_query_is_rejected():
    with pytest.raises(ValueError, match="invalid"):
        VisualizationHitTestingEngine().hit_test(_model(), HitTestQuery(0, 0, tolerance=-1))


def test_response_serialization_is_renderer_neutral_and_deterministic():
    engine = VisualizationHitTestingEngine()
    query = HitTestQuery(60, 100, tolerance=2)
    first = engine.hit_test(_model(), query).to_dict()
    second = engine.hit_test(_model(), query).to_dict()
    assert first == second
    assert first["renderer_neutral"] is True
    assert first["schema"] == "visualization.interactive.hit-test-response"
