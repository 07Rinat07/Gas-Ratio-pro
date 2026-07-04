from __future__ import annotations

import pandas as pd

from palettes.well_log_tablet import (
    InterpretationMarker,
    TabletTrackConfig,
    build_marker_interpretation_table,
    build_well_log_tablet,
    default_tablet_columns,
    numeric_tablet_columns,
)


def test_numeric_tablet_columns_include_convertible_values_and_skip_depth():
    df = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0],
            "GR": ["80", "82"],
            "comment": ["sand", "shale"],
            "wh": [10.0, 12.0],
        }
    )

    assert numeric_tablet_columns(df) == ("GR", "wh")
    assert default_tablet_columns(df) == ("GR", "wh")


def test_build_well_log_tablet_keeps_depth_increasing_downward_and_track_scales():
    df = pd.DataFrame(
        {
            "depth": [1002.0, 1000.0, 1001.0],
            "GR": [90.0, 70.0, 80.0],
            "C1": [10.0, 30.0, 20.0],
        }
    )
    tracks = (
        TabletTrackConfig(column="GR", color="#111111", x_range=(0.0, 150.0)),
        TabletTrackConfig(column="C1", color="#d62728"),
    )

    fig = build_well_log_tablet(
        df,
        tracks,
        depth_range=(1000.0, 1002.0),
        markers=(InterpretationMarker(label="a", depth=1001.0),),
        height=800,
    )

    assert list(fig.data[0].y) == [1000.0, 1001.0, 1002.0]
    assert list(fig.data[0].x) == [70.0, 80.0, 90.0]
    assert tuple(fig.layout.yaxis.range) == (1002.0, 1000.0)
    assert tuple(fig.layout.xaxis.range) == (0.0, 150.0)
    assert fig.layout.height == 800
    assert len(fig.layout.shapes) == 1
    assert fig.layout.shapes[0].y0 == 1001.0


def test_marker_interpretation_table_uses_nearest_depth_row():
    df = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0],
            "GR": [70.0, 80.0, 90.0],
            "wh": [10.0, 15.0, 20.0],
            "interpretation": ["gas", "oil", "dry"],
        }
    )

    table = build_marker_interpretation_table(
        df,
        (InterpretationMarker(label="b", depth=1001.2, note="peak"),),
        columns=("GR", "wh"),
    )

    assert table.to_dict("records") == [
        {
            "Метка": "b",
            "Глубина маркера": 1001.2,
            "Ближайшая глубина": 1001.0,
            "GR": 80.0,
            "wh": 15.0,
            "Интерпретация": "oil",
            "Комментарий": "peak",
        }
    ]
