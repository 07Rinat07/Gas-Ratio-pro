from __future__ import annotations

import json

from projects import (
    InterpretationGraphSettings,
    graph_settings_from_dict,
    graph_settings_to_dict,
    load_project_interpretation_graph_settings,
    project_interpretation_graph_settings_exists,
    save_project_interpretation_graph_settings,
)


def test_project_interpretation_graph_settings_roundtrip(tmp_path):
    settings = InterpretationGraphSettings(
        selected_tracks=("C1-C5", "Wh/Bh/Ch"),
        height=720,
        depth_range=(1000.0, 1002.0),
        gas_x_range=(0.0, 120.0),
        ratio_x_range=None,
        pixler_x_range=(1.0, 10.0),
        tablet_tracks=("GR", "C1"),
        tablet_x_ranges={"GR": (0.0, 150.0)},
        tablet_colors={"GR": "#111111"},
        tablet_markers=({"label": "a", "depth": 1001.0, "note": "peak"},),
        tablet_zones=({"label": "oil", "top_depth": 1000.0, "bottom_depth": 1002.0, "color": "#ffd966", "note": "manual"},),
        tablet_fill=True,
    )

    path = save_project_interpretation_graph_settings(settings, root=tmp_path, project_id="demo")
    loaded = load_project_interpretation_graph_settings(tmp_path, "demo")

    assert path == tmp_path / "demo" / "interpretation_graph_settings.json"
    assert project_interpretation_graph_settings_exists(tmp_path, "demo") is True
    assert loaded == settings
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["settings"]["selected_tracks"] == ["C1-C5", "Wh/Bh/Ch"]
    assert payload["settings"]["tablet_tracks"] == ["GR", "C1"]
    assert payload["settings"]["tablet_x_ranges"] == {"GR": [0.0, 150.0]}
    assert payload["settings"]["tablet_colors"] == {"GR": "#111111"}
    assert payload["settings"]["tablet_markers"] == [{"label": "a", "depth": 1001.0, "note": "peak"}]
    assert payload["settings"]["tablet_zones"] == [
        {"label": "oil", "top_depth": 1000.0, "bottom_depth": 1002.0, "color": "#ffd966", "note": "manual"}
    ]
    assert payload["settings"]["tablet_fill"] is True


def test_project_interpretation_graph_settings_from_dict_normalizes_values():
    settings = graph_settings_from_dict(
        {
            "selected_tracks": ["Pixler ratios", ""],
            "height": 9999,
            "depth_range": [1200, 1000],
            "gas_x_range": [10, 10],
            "ratio_x_range": ["bad", 5],
            "pixler_x_range": [1, 3],
            "tablet_tracks": ["GR", ""],
            "tablet_x_ranges": {"GR": [150, 0], "bad": [10, 10]},
            "tablet_colors": {"GR": "#123456", "bad": "red"},
            "tablet_markers": [
                {"label": "", "depth": "1001.5", "note": "check"},
                {"label": "bad", "depth": "nope"},
            ],
            "tablet_zones": [
                {"label": "gas", "top_depth": 1005, "bottom_depth": 1000, "color": "#abcdef", "note": "check"},
                {"label": "bad", "top_depth": 1, "bottom_depth": 1},
            ],
            "tablet_fill": True,
        }
    )

    assert settings.selected_tracks == ("Pixler ratios",)
    assert settings.height == 1100
    assert settings.depth_range == (1000.0, 1200.0)
    assert settings.gas_x_range is None
    assert settings.ratio_x_range is None
    assert settings.pixler_x_range == (1.0, 3.0)
    assert settings.tablet_tracks == ("GR",)
    assert settings.tablet_x_ranges == {"GR": (0.0, 150.0)}
    assert settings.tablet_colors == {"GR": "#123456"}
    assert settings.tablet_markers == ({"label": "a", "depth": 1001.5, "note": "check"},)
    assert settings.tablet_zones == (
        {"label": "gas", "top_depth": 1000.0, "bottom_depth": 1005.0, "color": "#abcdef", "note": "check"},
    )
    assert settings.tablet_fill is True
    assert graph_settings_to_dict(settings)["height"] == 1100


def test_project_interpretation_graph_settings_missing_file_returns_none(tmp_path):
    assert load_project_interpretation_graph_settings(tmp_path, "demo") is None
    assert project_interpretation_graph_settings_exists(tmp_path, "demo") is False
