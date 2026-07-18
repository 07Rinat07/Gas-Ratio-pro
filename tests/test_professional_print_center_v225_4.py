from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import pytest

from reports.document_model import build_engineering_document
from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_docx import PresentationDocxOptions, render_engineering_document_docx
from reports.presentation_html import PresentationHtmlOptions, build_presentation_html_report
from reports.print_center import build_professional_print_center_view
from reports.visualization_preview import normalize_visualization_preview
from services.report_page_aware_preview import ReportPageAwarePreviewService


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0, 1003.0],
            "GR": [10.0, 20.0, 30.0, 25.0],
            "C1": [1.0, 2.0, 3.0, 2.5],
            "RT": [100.0, 200.0, 300.0, 250.0],
            "NPHI": [0.20, 0.25, 0.30, 0.28],
            "X": [4.0, 5.0, 6.0, 5.5],
            "interpretation": ["Газовая залежь"] * 4,
            "wh": [8.0, 9.0, 10.0, 11.0],
            "bh": [40.0, 39.0, 38.0, 37.0],
            "c1_c2": [60.0, 62.0, 64.0, 66.0],
            "oil_indicator": [0.05, 0.06, 0.07, 0.08],
            "lithology": ["Sandstone"] * 4,
        }
    )


def _prepared(*, locale: str = "ru"):
    return ReportPageAwarePreviewService().prepare(
        _frame(),
        project_id="demo",
        source_id="well-a",
        title="Well A",
        locale=locale,
        page_size="A4",
        orientation="portrait",
        show_page_chrome=True,
        curve_limit=8,
        raster_dpi=96,
    )


def test_visible_print_center_view_exposes_every_physical_page() -> None:
    result = _prepared()
    view = build_professional_print_center_view(
        result.prepared,
        project_id="demo",
        locale="ru",
        title="Well A",
        output_format="docx",
    )

    assert result.export_ready is True
    assert view.export_ready is True
    assert view.page_count == result.prepared.package.page_count == 2
    assert view.exact_profile_label == "A4 · Книжная · 96 DPI · 2 страницы"
    assert [page.label for page in view.pages] == ["Страница 1/2", "Страница 2/2"]
    assert all(page.svg.startswith("<svg") for page in view.pages)
    assert view.to_dict()["direct_multi_page_preview"] is True
    assert view.to_dict()["single_page_fallback"] is False


def test_page_aware_preview_never_falls_back_to_first_svg() -> None:
    normalized = normalize_visualization_preview(
        {
            "schema": "visualization.preview.page-aware",
            "version": "1.1",
            "page_count": 2,
            "svg": "<svg><text>legacy first page</text></svg>",
            "export_ready": True,
            "single_page_fallback": False,
        }
    )

    assert normalized.pages == ()
    assert normalized.ok is False
    assert "page_aware_preview_pages_missing" in normalized.issues
    assert "page_aware_preview_page_count_mismatch:2:0" in normalized.issues


def test_docx_and_html_consume_the_same_direct_multi_page_contract() -> None:
    physical = _prepared()
    report = build_hydrocarbon_report_payload(_frame(), include_plot=False, locale="ru")
    assert report.presentation_model is not None
    model = replace(
        report.presentation_model,
        visualization_payloads=(physical.report_payload,),
    )

    html_result = build_presentation_html_report(
        model,
        options=PresentationHtmlOptions(include_figures=True),
    )
    html = html_result.content.decode("utf-8")
    assert html.count("<div class='visualization-preview-page") == 2
    assert "data-preview-schema='visualization.preview.page-aware'" in html
    assert "Страницы: 2" in html
    assert "Страница 1 из 2" in html
    assert "Страница 2 из 2" in html

    document = build_engineering_document(model, include_figures=True)
    docx_result = render_engineering_document_docx(
        document,
        options=PresentationDocxOptions(include_figures=True),
    )
    with ZipFile(BytesIO(docx_result.content)) as package:
        media = [name for name in package.namelist() if name.startswith("word/media/")]
        document_xml = package.read("word/document.xml").decode("utf-8")
    assert len(media) == 2
    assert "Страницы: 2" in document_xml
    assert "Страница 1 из 2" in document_xml
    assert "Страница 2 из 2" in document_xml


@pytest.mark.parametrize(
    ("locale", "summary_token", "page_label", "profile_label"),
    (
        ("ru", "Страницы: 2", "Страница 1 из 2", "A4 · Книжная · 96 DPI · 2 страницы"),
        ("kk", "Беттер: 2", "2 беттің 1-беті", "A4 · Кітаптық · 96 DPI · 2 бет"),
        ("en", "Pages: 2", "Page 1 of 2", "A4 · Portrait · 96 DPI · 2 pages"),
    ),
)
def test_direct_preview_contract_is_localized_in_three_languages(
    locale: str, summary_token: str, page_label: str, profile_label: str
) -> None:
    physical = _prepared(locale=locale)
    preview = normalize_visualization_preview(physical.report_payload["preview"])
    view = build_professional_print_center_view(
        physical.prepared,
        project_id="demo",
        locale=locale,
        title="Well A",
        output_format="html",
    )

    from reports.visualization_preview import (
        visualization_preview_page_label,
        visualization_preview_summary_text,
    )

    assert preview.locale == locale
    assert summary_token in visualization_preview_summary_text(preview)
    assert visualization_preview_page_label(1, 2, locale) == page_label
    assert view.exact_profile_label == profile_label
    assert view.page_count == 2


def test_visible_streamlit_print_center_has_physical_package_action() -> None:
    source = open("app/streamlit_app.py", encoding="utf-8").read()
    assert "Рассчитать точный физический пакет" in source
    assert "ReportPageAwarePreviewService().prepare" in source
    assert "DOCX/HTML получают все страницы напрямую" in source
    assert "visualization_payloads=(" in source
    assert '"bundle"' in source
    assert "Нақты физикалық пакетті есептеу" in source
    assert "Calculate exact physical package" in source
