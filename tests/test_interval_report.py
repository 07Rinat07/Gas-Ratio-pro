from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from reports.interval_report import (
    build_hydrocarbon_interval_summary_table,
    build_hydrocarbon_marker_table,
    build_interval_print_report,
    build_interpretation_counts_table,
    build_numeric_statistics_table,
    dataframe_to_report_table,
)


def test_numeric_statistics_table_uses_selected_numeric_columns():
    df = pd.DataFrame({"depth": [1000.0, 1001.0], "GR": [80.0, 90.0], "comment": ["a", "b"]})

    table = build_numeric_statistics_table(df, columns=("GR", "comment"))

    assert table is not None
    assert table.headers == ("Параметр", "Min", "Max", "Mean", "N")
    assert table.rows == (("GR", "80", "90", "85", "2"),)


def test_interpretation_counts_table_counts_preliminary_classes():
    df = pd.DataFrame({"interpretation": ["gas", "oil", "gas", ""]})

    table = build_interpretation_counts_table(df)

    assert table is not None
    assert ("gas", "2") in table.rows
    assert ("oil", "1") in table.rows
    assert ("not classified", "1") in table.rows


def test_dataframe_to_report_table_limits_rows_and_formats_nan():
    df = pd.DataFrame({"A": [1.0, None, 3.0], "B": ["x", "y", "z"]})

    table = dataframe_to_report_table("Rows", df, max_rows=2)

    assert table is not None
    assert table.headers == ("A", "B")
    assert table.rows == (("1", "x"), ("", "y"))


def test_hydrocarbon_interval_summary_table_lists_report_candidates():
    df = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1005.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Нефтяная залежь"],
            "wh": [6.0, 7.0, 25.0],
            "bh": [45.0, 44.0, 10.0],
            "c1_c2": [20.0, 21.0, 6.0],
            "oil_indicator": [0.04, 0.05, 0.2],
        }
    )

    table = build_hydrocarbon_interval_summary_table(df)

    assert table is not None
    assert table.title == "Сводка выявленных УВ-интервалов"
    assert "fluid_type" in table.headers
    assert len(table.rows) >= 1


def test_hydrocarbon_marker_table_lists_graph_annotations():
    df = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0],
            "interpretation": ["Нефтяная залежь", "Нефтяная залежь"],
            "c1_c2": [6.0, 7.0],
            "oil_indicator": [0.2, 0.21],
        }
    )

    table = build_hydrocarbon_marker_table(df)

    assert table is not None
    assert table.title == "Маркеры УВ-интервалов для графиков"
    assert "marker_id" in table.headers
    assert table.rows[0][0] == "HC-001"
    assert "OIL" in table.rows[0]


def test_interval_print_report_includes_metadata_tables_and_chart():
    df = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0],
            "GR": [80.0, 90.0],
            "interpretation": ["gas", "oil"],
            "c1_c2": [20.0, 6.0],
            "oil_indicator": [0.05, 0.2],
        }
    )
    figure = go.Figure(data=[go.Scatter(x=[80.0, 90.0], y=[1000.0, 1001.0])])

    html = build_interval_print_report(
        [figure],
        title="Interval <Report>",
        source_label="sample.las",
        project_label="Default",
        depth_label="1000-1001 м",
        interval_df=df,
        tablet_columns=("GR",),
        max_interval_rows=1,
    ).decode("utf-8")

    assert "Interval &lt;Report&gt;" in html
    assert "Печатный отчет по выбранному интервалу" in html
    assert "sample.las" in html
    assert "Сводка выявленных УВ-интервалов" in html
    assert "Маркеры УВ-интервалов для графиков" in html
    assert "Профиль отчета" in html
    assert "Инженерный" in html
    assert "Сводка предварительной интерпретации" not in html
    assert "Статистика выбранного интервала" not in html
    assert "Техническая таблица данных" not in html
    assert "Plotly.newPlot" in html


def test_interval_print_report_expert_profile_keeps_technical_appendix():
    df = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0],
            "GR": [80.0, 90.0],
            "interpretation": ["gas", "oil"],
            "c1_c2": [20.0, 6.0],
            "oil_indicator": [0.05, 0.2],
        }
    )
    figure = go.Figure(data=[go.Scatter(x=[80.0, 90.0], y=[1000.0, 1001.0])])

    html = build_interval_print_report(
        [figure],
        title="Expert Report",
        source_label="sample.las",
        project_label="Default",
        depth_label="1000-1001 м",
        interval_df=df,
        tablet_columns=("GR",),
        max_interval_rows=1,
        report_profile="expert",
    ).decode("utf-8")

    assert "Экспертный" in html
    assert "Сводка предварительной интерпретации" in html
    assert "Статистика выбранного интервала" in html
    assert "Техническая таблица данных (первые 1 из 2 строк)" in html
