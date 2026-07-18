from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import fitz
import pytest

from reports.document_model import (
    DocumentMetadata,
    DocumentPlot,
    DocumentSection,
    DocumentTable,
    EngineeringDocument,
)
from reports.presentation_docx import PresentationDocxOptions, render_engineering_document_docx
from reports.presentation_html import PresentationHtmlOptions, build_presentation_html_report
from reports.presentation_pdf import PresentationPdfOptions, render_engineering_document_pdf
from reports.print_readability_contract import REPORT_PRINT_READABILITY


@dataclass(frozen=True)
class _WideSvgFigure:
    svg: str
    depth_start: float = 1000.0
    depth_stop: float = 1500.0
    report_title: str = "Wide engineering tablet"


def _wide_svg() -> str:
    labels = "".join(
        f'<text x="{140 + index * 600}" y="640" font-size="92">Track {index + 1}</text>'
        for index in range(10)
    )
    frames = "".join(
        f'<rect x="{100 + index * 600}" y="400" width="520" height="3300" '
        'fill="none" stroke="#2563eb" stroke-width="12"/>'
        for index in range(10)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="6200" height="4200" '
        'viewBox="0 0 6200 4200">'
        '<rect width="6200" height="4200" fill="#fff" stroke="#111" stroke-width="20"/>'
        + frames
        + labels
        + "</svg>"
    )


def _document() -> EngineeringDocument:
    headers = tuple(f"Колонка {index}" for index in range(1, 9))
    rows = tuple(tuple(f"Значение {row}-{column}" for column in range(1, 9)) for row in range(1, 4))
    return EngineeringDocument(
        metadata=DocumentMetadata(
            title="Landscape frame utilization",
            rows=(("Источник", "demo.csv"), ("Профиль", "Инженерный")),
        ),
        sections=(
            DocumentSection(
                title="Engineering tablet",
                blocks=(DocumentPlot("Engineering tablet", _WideSvgFigure(_wide_svg())),),
                page_break_before=True,
            ),
            DocumentSection(
                title="Text report",
                blocks=(DocumentTable("Full-width results", headers, rows),),
                page_break_before=True,
            ),
        ),
    )


def test_print_readability_contract_requires_page_aware_full_frame_layout():
    assert REPORT_PRINT_READABILITY.valid
    assert REPORT_PRINT_READABILITY.layout_width_policy == "available-frame"
    assert REPORT_PRINT_READABILITY.plot_aspect_policy == "page-aware"
    assert REPORT_PRINT_READABILITY.landscape_minimum_frame_utilization >= 0.9


@pytest.mark.skipif(fitz is None, reason="PyMuPDF is required")
def test_a3_landscape_pdf_uses_right_side_of_plot_and_table_pages():
    rendered = render_engineering_document_pdf(
        _document(),
        options=PresentationPdfOptions(
            paper_size="A3",
            orientation="landscape",
            margin_mm=10,
            include_table_of_contents=False,
        ),
    )
    pdf = fitz.open(stream=rendered.content, filetype="pdf")
    assert pdf.page_count == 3

    plot_page = pdf.load_page(1)
    plot_hits = plot_page.search_for("Track 10")
    assert plot_hits
    assert max(rect.x1 for rect in plot_hits) > plot_page.rect.width * 0.78

    table_page = pdf.load_page(2)
    last_header = table_page.search_for("Колонка 8")
    assert last_header
    assert max(rect.x1 for rect in last_header) > table_page.rect.width * 0.82


def test_a3_landscape_docx_embeds_plot_at_section_width():
    rendered = render_engineering_document_docx(
        _document(),
        options=PresentationDocxOptions(
            paper_size="A3",
            orientation="landscape",
            margin_mm=10,
        ),
    )
    with ZipFile(BytesIO(rendered.content)) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    namespace = {"wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
    extents = root.findall(".//wp:extent", namespace)
    assert extents
    widest_inches = max(int(item.attrib["cx"]) for item in extents) / 914400.0
    assert widest_inches > 14.5


def test_landscape_html_declares_responsive_full_width_layout(monkeypatch):
    # Build a tiny presentation-model shim accepted by the document composer.
    from types import SimpleNamespace
    from reports.presentation_html import _render_document_plot

    html = _render_document_plot(DocumentPlot("Engineering tablet", _WideSvgFigure(_wide_svg())), include_plotlyjs=True)
    assert "visualization-preview" in html
    assert "width=\"6200\"" in html

    opts = PresentationHtmlOptions(paper_size="A3", orientation="landscape")
    # The renderer-level CSS contract is deterministic and does not depend on a browser.
    from reports.presentation_html import _print_css
    css = _print_css(opts)
    assert "@page{size:A3 landscape" in css
    assert ".visualization-preview-page svg{max-width:100%" in css
