from __future__ import annotations

from services.visualization_axis_grid import VisualizationAxisGridEngine


def _scene():
    return {
        "tracks": [{"id": "track.gamma", "title": "Gamma", "layer_ids": ["curve.GR"]}],
        "layers": [
            {
                "id": "curve.GR",
                "kind": "curve",
                "track_id": "track.gamma",
                "payload": {
                    "unit": "API",
                    "axis": {"min": 0.0, "max": 150.0, "scale": "linear"},
                },
            }
        ],
    }


def _layout():
    return {
        "tracks": [
            {
                "id": "track.gamma",
                "plot_bounds": {"x": 12.0, "y": 64.0, "width": 180.0, "height": 620.0},
                "axis_bounds": {"x": 12.0, "y": 42.0, "width": 180.0, "height": 22.0},
            }
        ],
        "depth": {
            "start": 1000.0,
            "stop": 1100.0,
            "unit": "M",
            "plot_top": 64.0,
            "plot_bottom": 684.0,
        },
    }


def test_axis_grid_engine_builds_depth_curve_axes_and_grid_lines():
    result = VisualizationAxisGridEngine().build(_scene(), _layout()).to_dict()

    assert result["schema"] == "visualization.axis.grid.model"
    assert result["ok"] is True
    assert [axis["kind"] for axis in result["axes"]] == ["curve", "depth"]
    curve_axis = next(axis for axis in result["axes"] if axis["kind"] == "curve")
    depth_axis = next(axis for axis in result["axes"] if axis["kind"] == "depth")
    assert curve_axis["unit"] == "API"
    assert curve_axis["ticks"][0]["position"] == 12.0
    assert curve_axis["ticks"][-1]["position"] == 192.0
    assert depth_axis["ticks"][0]["value"] == 1000.0
    assert depth_axis["ticks"][0]["position"] == 64.0
    assert any(line["orientation"] == "horizontal" for line in result["grid_lines"])
    assert any(line["orientation"] == "vertical" for line in result["grid_lines"])


def test_axis_grid_engine_supports_log_curve_axis():
    scene = _scene()
    scene["layers"][0]["payload"]["axis"] = {"min": 0.2, "max": 2000.0, "scale": "log"}
    result = VisualizationAxisGridEngine().build(scene, _layout()).to_dict()

    curve_axis = next(axis for axis in result["axes"] if axis["kind"] == "curve")
    assert curve_axis["scale"] == "log"
    assert [tick["value"] for tick in curve_axis["ticks"] if tick["major"]] == [1, 10, 100, 1000]


def test_axis_grid_engine_reports_invalid_depth_domain():
    layout = _layout()
    layout["depth"] = {"start": None, "stop": None}
    result = VisualizationAxisGridEngine().build(_scene(), layout).to_dict()

    assert result["ok"] is False
    assert "axis_grid_error:invalid_depth_layout" in result["issues"]
