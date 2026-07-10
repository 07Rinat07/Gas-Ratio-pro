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
            {"id": "curve.GR", "kind": "curve", "track_id": "track.gamma"},
            {"id": "curve.C1", "kind": "curve", "track_id": "track.gas"},
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
            },
            {
                "id": "track.gas",
                "title": "Gas",
                "bounds": {"x": 192.0, "y": 0.0, "width": 270.0, "height": 684.0},
                "plot_bounds": {"x": 192.0, "y": 64.0, "width": 270.0, "height": 620.0},
                "header_bounds": {"x": 192.0, "y": 0.0, "width": 270.0, "height": 42.0},
            },
        ],
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
    assert [item["id"] for item in result["primitives"]] == [
        "canvas.background",
        "track.track.gamma.background",
        "track.track.gas.background",
        "track.track.gamma.border",
        "track.track.gas.border",
        "track.track.gamma.title",
        "track.track.gas.title",
    ]
    assert result["metadata"]["raw_dataframe_included"] is False
    assert result["metadata"]["foundation_scope"] == "canvas_track_structure"
    assert result["diagnostics"] == ["render_model_pending_source_layers:2"]


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
