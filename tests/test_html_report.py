from __future__ import annotations

from reports.export_html import HtmlReportMetadata, HtmlReportTable, build_plotly_html_report


def test_html_report_includes_escaped_engineering_tables():
    table = HtmlReportTable(
        title="Маркеры <планшета>",
        headers=("Метка", "Комментарий"),
        rows=(("a", "oil < gas"),),
    )

    html = build_plotly_html_report([], HtmlReportMetadata(title="Report", tables=(table,))).decode("utf-8")

    assert "Маркеры &lt;планшета&gt;" in html
    assert "oil &lt; gas" in html
    assert "<table class='report-table'>" in html
