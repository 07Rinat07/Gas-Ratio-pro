from __future__ import annotations

import pandas as pd

from palettes.well_log_tablet import (
    InterpretationMarker,
    TabletTrackConfig,
    normalize_track_configs,
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


def test_normalize_track_configs_preserves_order_units_and_custom_colors():
    configs = normalize_track_configs(
        ("C1", "GR"),
        units={"C1": "%", "GR": "API"},
        colors={"GR": "#00ff00"},
        x_ranges={"GR": (0.0, 180.0)},
        fill=True,
    )

    assert [config.column for config in configs] == ["C1", "GR"]
    assert configs[0].unit == "%"
    assert configs[1].unit == "API"
    assert configs[1].color == "#00ff00"
    assert configs[1].x_range == (0.0, 180.0)
    assert configs[0].fill is True


def test_tablet_units_from_dataframe_reads_las_attrs():
    df = pd.DataFrame({"depth": [1.0], "GR": [80.0]})
    df.attrs["las_units"] = {"GR": "API", "EMPTY": ""}

    from palettes.well_log_tablet import tablet_units_from_dataframe

    assert tablet_units_from_dataframe(df) == {"GR": "API"}


def test_build_well_log_tablet_adds_interpretation_zone_shape():
    from palettes.well_log_tablet import InterpretationZone

    df = pd.DataFrame({"depth": [1000.0, 1001.0, 1002.0], "GR": [70.0, 80.0, 90.0]})
    fig = build_well_log_tablet(
        df,
        (TabletTrackConfig(column="GR"),),
        zones=(InterpretationZone(label="oil", top_depth=1000.5, bottom_depth=1001.5, color="#ffd966"),),
    )

    zone_shapes = [shape for shape in fig.layout.shapes if shape.type == "rect"]
    assert len(zone_shapes) == 1
    assert zone_shapes[0].y0 == 1000.5
    assert zone_shapes[0].y1 == 1001.5
    assert zone_shapes[0].fillcolor == "#ffd966"


def test_build_interpretation_zone_table_normalizes_depth_order():
    from palettes.well_log_tablet import InterpretationZone, build_interpretation_zone_table

    table = build_interpretation_zone_table(
        (InterpretationZone(label="gas", top_depth=1005.0, bottom_depth=1000.0, color="#abcdef", note="check"),)
    )

    assert table.to_dict("records") == [
        {
            "Зона": "gas",
            "Верх": 1000.0,
            "Низ": 1005.0,
            "Мощность": 5.0,
            "Цвет": "#abcdef",
            "Комментарий": "check",
        }
    ]


def test_mud_gas_literature_tablet_columns_uses_available_ordered_aliases():
    from palettes.well_log_tablet import mud_gas_literature_tablet_columns

    df = pd.DataFrame(
        {
            "DEPT": [1000.0, 1001.0],
            "NPHI": [0.25, 0.22],
            "C1": [10.0, 11.0],
            "TGAS": [50.0, 70.0],
            "GR": [80.0, 85.0],
            "WH": [8.0, 12.0],
            "C1_C2": [20.0, 15.0],
            "RT": [12.0, 18.0],
        }
    )

    assert mud_gas_literature_tablet_columns(df) == ("GR", "TGAS", "C1", "WH", "C1_C2", "RT", "NPHI")


def test_mud_gas_literature_markers_use_extremes_and_skip_duplicate_depths():
    from palettes.well_log_tablet import mud_gas_literature_markers

    df = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0, 1003.0],
            "TGAS": [10.0, 90.0, 30.0, 20.0],
            "WH": [5.0, 6.0, 25.0, 7.0],
            "C1_C2": [40.0, 30.0, 8.0, 12.0],
            "inverse_oil_indicator": [1.0, 2.0, 3.0, 9.0],
        }
    )

    markers = mud_gas_literature_markers(df)

    assert [(marker.label, marker.depth) for marker in markers] == [
        ("TG", 1001.0),
        ("Wh", 1002.0),
        ("IOI", 1003.0),
    ]
    assert all("провер" in marker.note.lower() or "справоч" in marker.note.lower() for marker in markers)


def test_per_track_fill_modes_add_baseline_traces_and_titles():
    from palettes.well_log_tablet import normalize_tablet_fill_mode

    df = pd.DataFrame({"depth": [1000.0, 1001.0], "GR": [70.0, 90.0], "C1": [5.0, 10.0]})
    configs = normalize_track_configs(
        ("GR", "C1"),
        x_ranges={"GR": (0.0, 150.0), "C1": (0.0, 20.0)},
        fill_modes={"GR": "to_left", "C1": "to_right"},
    )

    fig = build_well_log_tablet(df, configs)

    assert normalize_tablet_fill_mode("left") == "to_left"
    assert configs[0].fill_mode == "to_left"
    assert configs[1].fill_mode == "to_right"
    assert len(fig.data) == 4
    assert list(fig.data[0].x) == [0.0, 0.0]
    assert list(fig.data[2].x) == [20.0, 20.0]
    assert fig.data[1].fill == "tonextx"
    assert fig.data[3].fill == "tonextx"
    assert "fill to left scale" in fig.layout.annotations[0].text
    assert "fill to right scale" in fig.layout.annotations[1].text


def test_legacy_tablet_fill_still_maps_to_zero_fill():
    configs = normalize_track_configs(("GR",), fill=True)

    assert configs[0].fill is True
    assert configs[0].fill_mode == "to_zero"


def test_mud_gas_literature_tablet_columns_accepts_column_name_list() -> None:
    from palettes.well_log_tablet import mud_gas_literature_tablet_columns

    selected = mud_gas_literature_tablet_columns(["DEPT", "GR", "GAS", "C1", "C2"])

    assert "GR" in selected
    assert "GAS" in selected
