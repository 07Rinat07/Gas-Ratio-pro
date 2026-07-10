from __future__ import annotations

from services.visualization_render_model import VisualizationRenderModelBuilder


def _scene():
    return {
        "schema": "visualization.engine.scene",
        "tracks": [
            {"id": "track.gamma", "title": "Gamma", "style": {"fill": "#fafafa"}},
            {"id": "track.gas", "title": "Gas"},
        ],
        "layers": [
            {"id": "curve.GR", "kind": "curve", "track_id": "track.gamma", "payload": {"mnemonic": "GR", "unit": "API", "axis": {"min": 0, "max": 150, "scale": "linear"}, "points": [{"depth": 1000, "value": 20}, {"depth": 1050, "value": 80}, {"depth": 1100, "value": 120}]}},
            {"id": "curve.C1", "kind": "curve", "track_id": "track.gas", "payload": {"mnemonic": "C1", "unit": "PPM", "axis": {"min": 1, "max": 1000, "scale": "log"}, "points": [{"depth": 1000, "value": 2}, {"depth": 1050, "value": 20}, {"depth": 1100, "value": 200}]}},
            {"id": "interval.gas", "kind": "interval_overlay", "track_id": "track.gas", "z_index": 10, "payload": {"top": 1020, "base": 1040, "label": "Gas", "style": {"fill": "#ffd54f", "stroke": "#ff8f00"}}},
        ],
    }


def _layout():
    return {
        "schema": "visualization.layout.result",
        "width": 474,
        "height": 708,
        "tracks": [
            {
                "id": "track.gamma",
                "title": "Gamma",
                "bounds": {"x": 12.0, "y": 0.0, "width": 180.0, "height": 684.0},
                "plot_bounds": {"x": 12.0, "y": 64.0, "width": 180.0, "height": 620.0},
                "header_bounds": {"x": 12.0, "y": 0.0, "width": 180.0, "height": 42.0},
                "axis_bounds": {"x": 12.0, "y": 42.0, "width": 180.0, "height": 22.0},
            },
            {
                "id": "track.gas",
                "title": "Gas",
                "bounds": {"x": 192.0, "y": 0.0, "width": 270.0, "height": 684.0},
                "plot_bounds": {"x": 192.0, "y": 64.0, "width": 270.0, "height": 620.0},
                "header_bounds": {"x": 192.0, "y": 0.0, "width": 270.0, "height": 42.0},
                "axis_bounds": {"x": 192.0, "y": 42.0, "width": 270.0, "height": 22.0},
            },
        ],
        "depth": {"start": 1000.0, "stop": 1100.0, "unit": "M", "plot_top": 64.0, "plot_bottom": 684.0},
    }


def test_render_model_builds_deterministic_structural_primitives():
    result = VisualizationRenderModelBuilder().build(_scene(), _layout()).to_dict()

    assert result["schema"] == "visualization.render.model"
    assert result["ok"] is True
    assert result["width"] == 474
    assert result["height"] == 708
    assert [item["id"] for item in result["clip_regions"]] == [
        "clip.track.gamma.plot",
        "clip.track.gas.plot",
    ]
    primitive_ids = [item["id"] for item in result["primitives"]]
    assert primitive_ids[0] == "canvas.background"
    assert "track.track.gamma.background" in primitive_ids
    assert "track.track.gas.border" in primitive_ids
    assert "axis.depth.label.0" in primitive_ids
    assert any(item["kind"] == "line" for item in result["primitives"])
    assert result["metadata"]["raw_dataframe_included"] is False
    assert result["metadata"]["foundation_scope"] == "canvas_track_axis_grid_curve_quality_overlay"
    assert result["metadata"]["curve_primitive_count"] == 2
    assert result["metadata"]["overlay_primitive_count"] == 1
    assert result["metadata"]["axis_count"] >= 1
    assert result["metadata"]["grid_line_count"] >= 1
    assert result["diagnostics"] == []
    assert any(item["kind"] == "polyline" and item["clip_id"] == "clip.track.gamma.plot" for item in result["primitives"])
    assert any(item["id"] == "overlay.interval.gas" for item in result["primitives"])


def test_render_model_serialization_is_deterministic():
    builder = VisualizationRenderModelBuilder()

    assert builder.build(_scene(), _layout()).to_dict() == builder.build(_scene(), _layout()).to_dict()


def test_render_model_returns_safe_diagnostic_primitives_for_empty_layout():
    result = VisualizationRenderModelBuilder().build(
        {"schema": "visualization.engine.scene", "tracks": [], "layers": []},
        {"schema": "visualization.layout.result", "width": 360, "height": 180, "tracks": []},
    ).to_dict()

    assert result["ok"] is False
    assert "render_model_error:no_layout_tracks" in result["diagnostics"]
    assert [item["kind"] for item in result["primitives"]] == [
        "rectangle",
        "rectangle",
        "text",
        "text",
    ]
