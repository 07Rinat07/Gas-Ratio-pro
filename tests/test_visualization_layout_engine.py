from __future__ import annotations

from services.visualization_layout_engine import VisualizationLayoutEngine


def _scene():
    return {
        "schema": "visualization.engine.scene",
        "tracks": [
            {"id": "track.gamma", "title": "Gamma", "width": 1.0, "layer_ids": ["curve.GR"]},
            {"id": "track.gas", "title": "Gas", "width": 1.5, "layer_ids": ["curve.C1"]},
        ],
        "depth_sync": {
            "start": 1000.0,
            "stop": 1100.0,
            "unit": "M",
            "inverted": True,
        },
    }


def test_layout_engine_builds_deterministic_track_geometry():
    layout = VisualizationLayoutEngine().build(_scene()).to_dict()

    assert layout["schema"] == "visualization.layout.result"
    assert layout["ok"] is True
    assert layout["width"] == 474
    assert layout["height"] == 708
    assert [track["id"] for track in layout["tracks"]] == ["track.gamma", "track.gas"]
    assert layout["tracks"][0]["plot_bounds"] == {"x": 12.0, "y": 64.0, "width": 180.0, "height": 620.0}
    assert layout["tracks"][1]["plot_bounds"] == {"x": 192.0, "y": 64.0, "width": 270.0, "height": 620.0}


def test_layout_depth_mapping_is_shared_and_inverted_downward():
    layout = VisualizationLayoutEngine().build(_scene())

    assert layout.depth.map_depth(1000.0) == 64.0
    assert layout.depth.map_depth(1050.0) == 374.0
    assert layout.depth.map_depth(1100.0) == 684.0


def test_layout_engine_reports_invalid_empty_scene():
    layout = VisualizationLayoutEngine().build({"tracks": [], "depth_sync": {}}).to_dict()

    assert layout["ok"] is False
    assert "layout_scene_has_no_tracks" in layout["issues"]
    assert "layout_invalid_depth_domain" in layout["issues"]
