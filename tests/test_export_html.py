from __future__ import annotations

import plotly.graph_objects as go

from reports.export_html import HtmlReportMetadata, build_plotly_html_report


def test_build_plotly_html_report_includes_print_header_metadata_and_chart():
    figure = go.Figure(data=[go.Scatter(x=[1, 2], y=[10, 20], name="GR")])

    html = build_plotly_html_report(
        [figure],
        HtmlReportMetadata(
            title="LAS <Correlation>",
            subtitle="Печатный отчет",
            rows=(("Проект", "default"), ("Интервал", "1000-1010 м")),
            notes=("Проверить по ГИС.",),
        ),
    ).decode("utf-8")

    assert "LAS &lt;Correlation&gt;" in html
    assert "Печатный отчет" in html
    assert "Проект" in html
    assert "1000-1010 м" in html
    assert "Проверить по ГИС." in html
    assert "Plotly.newPlot" in html
    assert "@media print" in html
