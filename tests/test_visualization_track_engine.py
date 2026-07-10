from __future__ import annotations

from services.visualization_track_engine import VisualizationTrackEngine


def _scene():
    return {
        "tracks": [
            {
                "id": "track.gamma",
                "title": "Gamma",
                "width": 1.0,
                "printable": True,
                "layer_ids": ["curve.GR"],
                "style": {"pinned": True, "group": "logs"},
            },
            {
                "id": "track.gas",
                "title": "Gas",
                "width": 1.5,
                "printable": False,
                "layer_ids": ["curve.C1"],
                "style": {"group": "gas"},
            },
        ],
        "render_hints": {
            "visible_tracks": ["track.gamma", "track.gas"],
            "active_track_id": "track.gas",
        },
    }


def _layout():
    return {
        "tracks": [
            {
                "id": "track.gamma",
                "bounds": {"x": 12, "y": 0, "width": 180, "height": 684},
                "header_bounds": {"x": 12, "y": 0, "width": 180, "height": 42},
                "axis_bounds": {"x": 12, "y": 42, "width": 180, "height": 22},
                "plot_bounds": {"x": 12, "y": 64, "width": 180, "height": 620},
            },
            {
                "id": "track.gas",
                "bounds": {"x": 192, "y": 0, "width": 270, "height": 684},
                "header_bounds": {"x": 192, "y": 0, "width": 270, "height": 42},
                "axis_bounds": {"x": 192, "y": 42, "width": 270, "height": 22},
                "plot_bounds": {"x": 192, "y": 64, "width": 270, "height": 620},
            },
        ],
        "depth": {
            "start": 1000,
            "stop": 1100,
            "unit": "M",
            "inverted": True,
            "plot_top": 64,
            "plot_bottom": 684,
        },
    }


def test_track_engine_builds_ordered_tracks_regions_and_shared_viewport():
    result = VisualizationTrackEngine().build(_scene(), _layout()).to_dict()

    assert result["schema"] == "visualization.track.collection"
    assert result["ok"] is True
    assert result["active_track_id"] == "track.gas"
    assert result["visible_track_ids"] == ["track.gamma", "track.gas"]
    gamma = result["tracks"][0]
    assert gamma["pinned"] is True
    assert gamma["group"] == "logs"
    assert gamma["viewport"]["depth_start"] == 1000.0
    assert gamma["viewport"]["depth_stop"] == 1100.0
    assert [region["kind"] for region in gamma["regions"]] == ["track", "header", "axis", "plot"]


def test_track_engine_applies_visibility_hint_and_active_fallback():
    scene = _scene()
    scene["render_hints"] = {
        "visible_tracks": ["track.gamma"],
        "active_track_id": "track.gas",
    }
    result = VisualizationTrackEngine().build(scene, _layout()).to_dict()

    assert result["visible_track_ids"] == ["track.gamma"]
    assert result["active_track_id"] == "track.gamma"
    assert result["tracks"][1]["visible"] is False


def test_track_engine_reports_empty_contract_safely():
    result = VisualizationTrackEngine().build({}, {}).to_dict()

    assert result["ok"] is False
    assert "track_engine_error:no_scene_tracks" in result["issues"]
    assert "track_engine_error:no_layout_tracks" in result["issues"]
