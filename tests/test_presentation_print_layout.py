from __future__ import annotations

import pandas as pd

from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_html import PresentationHtmlOptions, build_presentation_html_report


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "depth": [2148.2, 2149.0, 2155.0, 2156.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Нефтяная залежь", "Нефтяная залежь"],
            "c1": [0.1, 0.2, 0.15, 0.12],
            "wh": [6.0, 7.0, 25.0, 26.0],
            "bh": [45.0, 44.0, 10.0, 11.0],
            "c1_c2": [80.0, 82.0, 6.0, 6.5],
            "oil_indicator": [0.04, 0.05, 0.2, 0.22],
            "lithology": ["Sandstone", "Sandstone", "Sandstone", "Sandstone"],
        }
    )


def test_presentation_html_contains_print_ready_page_css() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame(), include_plot=True)
    assert payload.presentation_model is not None

    rendered = build_presentation_html_report(
        payload.presentation_model,
        options=PresentationHtmlOptions(paper_size="A4", orientation="portrait", print_margin_mm=12),
    )
    html = rendered.content.decode("utf-8")

    assert "@page{size:A4 portrait;margin:12mm;}" in html
    assert "page-break-inside:avoid" in html
    assert "report-plot avoid-break" in html
    assert "modebar{display:none!important;}" in html


def test_presentation_html_sanitizes_print_options() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame())
    assert payload.presentation_model is not None

    rendered = build_presentation_html_report(
        payload.presentation_model,
        options=PresentationHtmlOptions(paper_size="bad", orientation="bad", print_margin_mm=100),
    )
    html = rendered.content.decode("utf-8")

    assert "@page{size:A4 portrait;margin:25mm;}" in html
