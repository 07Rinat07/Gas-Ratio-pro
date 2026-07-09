from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from reports.executive_summary import build_executive_summary_from_dataframe, main_intervals_table
from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.interval_report import build_interval_print_report


def test_executive_summary_focuses_on_intervals_not_row_count() -> None:
    frame = pd.DataFrame(
        {
            "depth": [2148.2, 2149.0, 2155.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Нефтяная залежь"],
            "wh": [6.0, 7.0, 25.0],
            "bh": [45.0, 44.0, 10.0],
            "c1_c2": [80.0, 82.0, 6.0],
            "oil_indicator": [0.04, 0.05, 0.2],
            "lithology": ["Sandstone", "Sandstone", "Sandstone"],
        }
    )

    summary = build_executive_summary_from_dataframe(frame)

    assert summary.title == "Краткое инженерное заключение"
    assert summary.main_intervals
    assert "строк" not in " ".join(item.title.lower() for item in summary.items)
    assert any(item.title == "Наиболее перспективный интервал" for item in summary.items)


def test_hydrocarbon_report_payload_puts_executive_tables_first() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0],
            "interpretation": ["Газовая залежь", "Газовая залежь"],
            "wh": [6.0, 7.0],
            "bh": [45.0, 44.0],
            "c1_c2": [80.0, 82.0],
        }
    )

    payload = build_hydrocarbon_report_payload(frame)

    assert payload.executive_summary is not None
    assert payload.professional_tables[0].title == "Краткое инженерное заключение"
    assert payload.main_intervals_table is not None
    assert main_intervals_table(payload.executive_summary) is not None


def test_interval_print_report_header_hides_technical_row_counter() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0],
            "interpretation": ["Газовая залежь", "Газовая залежь"],
            "wh": [6.0, 7.0],
            "bh": [45.0, 44.0],
            "c1_c2": [80.0, 82.0],
        }
    )
    figure = go.Figure(data=[go.Scatter(x=[1, 2], y=[1000.0, 1001.0])])

    html = build_interval_print_report(
        [figure],
        title="Gas Ratio Professional Report",
        source_label="sample.las",
        project_label="Default",
        depth_label="1000–1001 м",
        interval_df=frame,
        tablet_columns=("wh", "bh"),
        max_interval_rows=1,
    ).decode("utf-8")

    header = html.split("</section>", 1)[0]
    assert "Инженерное заключение" in header
    assert "Строк в интервале" not in header
    assert "Планшетные параметры" not in header
    assert "Краткое инженерное заключение" in html
