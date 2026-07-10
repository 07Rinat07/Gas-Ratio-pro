from __future__ import annotations

import pytest

from services.visualization_hit_testing import HitTestQuery, VisualizationHitTestingEngine
from services.visualization_render_model import RenderPrimitive, VisualizationRenderModel
from services.visualization_spatial_index import PrimitiveBounds, VisualizationSpatialIndex, primitive_bounds


def _large_model(count: int = 500) -> VisualizationRenderModel:
    primitives = tuple(
        RenderPrimitive(
            id=f"point.{index}",
            kind="text",
            z_index=index,
            payload={"x": float(index * 20), "y": 50.0, "text": str(index)},
        )
        for index in range(count)
    )
    return VisualizationRenderModel(width=count * 20 + 100, height=100, primitives=primitives)


def test_primitive_bounds_support_core_interactive_kinds():
    polyline = RenderPrimitive("curve", "polyline", 1, {"points": [[10, 20], [30, 5], [40, 50]]})
    rectangle = RenderPrimitive("box", "rectangle", 1, {"x": 2, "y": 3, "width": 8, "height": 9})
    line = RenderPrimitive("line", "line", 1, {"x1": 5, "y1": 8, "x2": 1, "y2": 2})
    text = RenderPrimitive("text", "text", 1, {"x": 7, "y": 11})

    assert primitive_bounds(polyline) == PrimitiveBounds(10, 5, 40, 50)
    assert primitive_bounds(rectangle) == PrimitiveBounds(2, 3, 10, 12)
    assert primitive_bounds(line) == PrimitiveBounds(1, 2, 5, 8)
    assert primitive_bounds(text) == PrimitiveBounds(7, 11, 7, 11)


def test_index_returns_only_bounds_intersecting_query_area():
    model = _large_model(20)
    index = VisualizationSpatialIndex.build(model, cell_size=32)
    candidates = index.query_point(200, 50, tolerance=3)
    assert candidates == (10,)


def test_tolerance_expands_spatial_candidate_query():
    model = _large_model(20)
    index = VisualizationSpatialIndex.build(model, cell_size=32)
    assert index.query_point(208, 50, tolerance=7) == ()
    assert index.query_point(208, 50, tolerance=8) == (10,)


def test_index_reduces_hit_testing_inspection_count():
    model = _large_model()
    index = VisualizationSpatialIndex.build(model, cell_size=64)
    query = HitTestQuery(4000, 50, tolerance=2, kinds=("text",))
    engine = VisualizationHitTestingEngine()

    linear = engine.hit_test(model, query)
    indexed = engine.hit_test(model, query, spatial_index=index)

    assert indexed.nearest is not None
    assert indexed.nearest.primitive_id == "point.200"
    assert indexed.results == linear.results
    assert indexed.inspected_primitive_count < linear.inspected_primitive_count / 20
    assert indexed.diagnostics == ("hit_test_spatial_index_used",)


def test_index_preserves_deterministic_z_ordering():
    model = VisualizationRenderModel(
        width=100,
        height=100,
        primitives=(
            RenderPrimitive("low", "text", 1, {"x": 50, "y": 50}),
            RenderPrimitive("high", "text", 10, {"x": 50, "y": 50}),
        ),
    )
    index = VisualizationSpatialIndex.build(model)
    response = VisualizationHitTestingEngine().hit_test(
        model, HitTestQuery(50, 50, tolerance=1), spatial_index=index
    )
    assert [item.primitive_id for item in response.results] == ["high", "low"]


def test_incompatible_index_is_rejected():
    first = _large_model(10)
    second = _large_model(11)
    index = VisualizationSpatialIndex.build(first)
    with pytest.raises(ValueError, match="not compatible"):
        VisualizationHitTestingEngine().hit_test(second, HitTestQuery(0, 50), spatial_index=index)


def test_index_can_be_rebuilt_for_new_model():
    index = VisualizationSpatialIndex.build(_large_model(10))
    replacement = _large_model(12)
    index.rebuild(replacement)
    assert index.compatible_with(replacement) is True
    assert index.stats.primitive_count == 12
    assert index.stats.indexed_primitive_count == 12


def test_index_contract_exposes_diagnostics_without_geometry_payload():
    index = VisualizationSpatialIndex.build(_large_model(10), cell_size=40)
    payload = index.to_dict()
    assert payload["schema"] == "visualization.interactive.spatial-index"
    assert payload["strategy"] == "uniform-grid"
    assert payload["stats"]["cell_size"] == 40
    assert payload["renderer_neutral"] is True
    assert "buckets" not in payload


def test_invalid_cell_size_and_query_are_rejected():
    with pytest.raises(ValueError, match="cell_size"):
        VisualizationSpatialIndex(cell_size=0)
    index = VisualizationSpatialIndex.build(_large_model(1))
    with pytest.raises(ValueError, match="tolerance"):
        index.query_point(0, 0, tolerance=-1)
