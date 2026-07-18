from __future__ import annotations

import json

import pandas as pd
import pytest

from palettes.config import load_palette_config
from palettes.depth_tracks import build_depth_gas_tracks, build_depth_interpretation_track
from palettes.ternary import build_ternary_palette
from tests.visual_rebaseline_helpers import assert_visual_rebaseline


def test_load_palette_config_from_json(tmp_path):
    config_path = tmp_path / "palettes.json"
    config_path.write_text(
        json.dumps(
            {
                "version": "test",
                "notice": "test notice",
                "pixler": {
                    "zones": [
                        {
                            "name": "Zone A",
                            "y_min": 1,
                            "y_max": 10,
                            "color": "rgba(1, 2, 3, 0.1)",
                        }
                    ]
                },
                "ternary": {
                    "regions": [
                        {
                            "name": "Region A",
                            "a": [0.6, 0.8, 0.6],
                            "b": [0.2, 0.1, 0.3],
                            "c": [0.2, 0.1, 0.1],
                            "color": "rgba(1, 2, 3, 0.1)",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_palette_config(config_path)

    assert config.version == "test"
    assert config.notice == "test notice"
    assert config.pixler_zones[0].name == "Zone A"
    assert config.ternary_regions[0].name == "Region A"


def test_invalid_pixler_zone_is_rejected(tmp_path):
    config_path = tmp_path / "palettes.json"
    config_path.write_text(
        json.dumps(
            {
                "pixler": {
                    "zones": [
                        {
                            "name": "Broken",
                            "y_min": 10,
                            "y_max": 1,
                            "color": "rgba(1, 2, 3, 0.1)",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="0 < y_min < y_max"):
        load_palette_config(config_path)


def test_ternary_regions_are_rendered():
    config = load_palette_config()
    row = pd.Series({"c2_sumc": 0.5, "c3_sumc": 0.3, "nc4_sumc": 0.2})
    fig = build_ternary_palette(row, regions=config.ternary_regions)

    polygons = [trace for trace in fig.data if str(getattr(trace, "mode", "")) == "lines"]
    labels = [trace for trace in fig.data if str(getattr(trace, "mode", "")) == "text"]
    selected = next(trace for trace in fig.data if getattr(trace, "name", "") == "Выбранная глубина")
    assert_visual_rebaseline(
        "tests/test_palette_config.py::test_ternary_regions_are_rendered",
        {
            "region_count": len(config.ternary_regions),
            "polygon_names": [str(trace.name) for trace in polygons],
            "region_label_trace_count": len(labels),
            "selected_marker_name": str(selected.name),
            "selected_marker_mode": str(selected.mode),
        },
    )

def test_depth_tracks_use_interval_midpoint_when_depth_is_missing():
    df = pd.DataFrame(
        {
            "depth_from": [1000, 1002],
            "depth_to": [1001, 1004],
            "c1": [80, 81],
        }
    )

    fig = build_depth_gas_tracks(df)

    assert list(fig.data[0].y) == [1000.5, 1003.0]

def test_depth_tracks_sort_depth_ascending_for_top_down_plot():
    df = pd.DataFrame({"depth": [1002.0, 1000.0], "c1": [20, 10]})

    fig = build_depth_gas_tracks(df, depth_range=(1000.0, 1002.0), x_range=(0.0, 30.0), height=700)

    assert list(fig.data[0].y) == [1000.0, 1002.0]
    assert list(fig.data[0].x) == [10, 20]
    assert tuple(fig.layout.yaxis.range) == (1002.0, 1000.0)
    assert tuple(fig.layout.xaxis.range) == (0.0, 30.0)
    assert fig.layout.height == 700


def test_depth_interpretation_track_uses_sorted_depths():
    df = pd.DataFrame(
        {
            "depth": [2.0, 1.0],
            "interpretation": ["Нефтяная залежь", "Газовая залежь"],
        }
    )

    fig = build_depth_interpretation_track(df, depth_range=(1.0, 2.0))

    assert list(fig.data[0].y) == [1.0, 2.0]
    assert tuple(fig.layout.yaxis.range) == (2.0, 1.0)
