from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from reports.interval_report import (
    build_interval_print_report,
    build_hydrocarbon_intervals_table,
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


def test_hydrocarbon_intervals_table_groups_gas_oil_and_transition_intervals():
    df = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0, 1003.0, 1004.0],
            "interpretation": [
                "Газовая залежь",
                "Газовая залежь",
                "Недостаточно данных",
                "Нефтяная залежь",
                "Переходная зона / проверить",
            ],
            "wh": [10.0, 12.0, None, 25.0, 18.0],
            "bh": [20.0, 22.0, None, 15.0, 17.0],
            "oil_indicator": [0.2, 0.3, None, 0.8, 0.6],
        }
    )

    table = build_hydrocarbon_intervals_table(df)

    assert table is not None
    assert table.title == "Сводка выявленных интервалов с признаками УВ"
    assert table.headers[:5] == ("№", "Кровля", "Подошва", "Толщина", "Интерпретация")
    assert table.rows[0][:6] == ("1", "1000", "1001", "1", "Газовая залежь", "2")
    assert table.rows[0][6:9] == ("11", "21", "0.25")
    assert table.rows[1][:6] == ("2", "1003", "1003", "0", "Нефтяная залежь", "1")
    assert table.rows[2][:6] == ("3", "1004", "1004", "0", "Переходная зона / проверить", "1")


def test_dataframe_to_report_table_limits_rows_and_formats_nan():
    df = pd.DataFrame({"A": [1.0, None, 3.0], "B": ["x", "y", "z"]})

    table = dataframe_to_report_table("Rows", df, max_rows=2)

    assert table is not None
    assert table.headers == ("A", "B")
    assert table.rows == (("1", "x"), ("", "y"))


def test_interval_print_report_includes_metadata_tables_and_chart():
    df = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0],
            "GR": [80.0, 90.0],
            "interpretation": ["gas", "oil"],
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
    assert "Сводка предварительной интерпретации" in html
    assert "Сводка выявленных интервалов с признаками УВ" in html
    assert "Статистика выбранного интервала" in html
    assert "Таблица выбранного интервала (первые 1 из 2 строк)" in html
    assert "Plotly.newPlot" in html
