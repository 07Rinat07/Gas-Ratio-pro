from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Sequence

import plotly.io as pio

from reports.document_model import (
    DocumentNotice,
    DocumentPlot,
    DocumentVisualizationPreview,
    DocumentTable,
    EngineeringDocument,
    build_engineering_document,
)
from reports.export_html import HtmlReportTable
from reports.presentation_model import PresentationModel


@dataclass(frozen=True)
class PresentationHtmlOptions:
    """Options for the engineer-first HTML/PDF-oriented report renderer.

    This renderer consumes a ready PresentationModel and therefore must not
    rerun interval detection, gas-ratio calculations or interpretation rules.
    It is the first step toward PDF/DOCX exporters: a single presentation model
    is rendered into a printable document profile.
    """

    include_figures: bool = True
    include_technical_appendix: bool = False
    page_title: str = "Gas Ratio Professional Report"
    language: str = "ru"
    paper_size: str = "A4"
    orientation: str = "portrait"
    print_margin_mm: int = 10
    compact_tables: bool = True


def _safe_paper_size(value: str) -> str:
    text = str(value or "A4").strip().upper()
    return text if text in {"A4", "A3", "LETTER"} else "A4"


def _safe_orientation(value: str) -> str:
    text = str(value or "portrait").strip().lower()
    return text if text in {"portrait", "landscape"} else "portrait"


def _safe_margin_mm(value: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 10
    return max(5, min(number, 25))


def _print_css(opts: PresentationHtmlOptions) -> str:
    paper = _safe_paper_size(opts.paper_size)
    orientation = _safe_orientation(opts.orientation)
    margin = _safe_margin_mm(opts.print_margin_mm)
    table_font = "11px" if opts.compact_tables else "12px"
    return "\n".join(
        (
            f"@page{{size:{paper} {orientation};margin:{margin}mm;}}",
            ".page-break-before{page-break-before:always;}",
            ".avoid-break{page-break-inside:avoid;break-inside:avoid;}",
            ".report-cover{page-break-after:avoid;}",
            ".report-section{page-break-inside:avoid;break-inside:avoid;}",
            ".report-table{font-size:" + table_font + ";}",
            ".report-table th,.report-table td{padding:4px 6px;}",
            ".report-plot{page-break-before:always;}",
            ".visualization-preview-page-next{page-break-before:always;break-before:page;}",
            ".visualization-preview-page svg{max-width:100%;height:auto;}",
            "@media print{body{margin:0;} .modebar{display:none!important;} a{text-decoration:none;color:inherit;}}",
        )
    )


@dataclass(frozen=True)
class PresentationHtmlResult:
    """Rendered presentation document plus the table profile actually used."""

    content: bytes
    table_titles: tuple[str, ...]
    figure_count: int
    profile: str


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _metadata_table(rows: Sequence[tuple[str, str]]) -> str:
    clean_rows = [(label, value) for label, value in rows if _clean_text(label) and _clean_text(value)]
    if not clean_rows:
        return ""
    body = "\n".join(f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>" for label, value in clean_rows)
    return f"<table class='meta'>{body}</table>"


def _notes(notes: Sequence[str]) -> str:
    clean_notes = [_clean_text(note) for note in notes if _clean_text(note)]
    if not clean_notes:
        return ""
    return "<ul class='notes'>" + "".join(f"<li>{escape(note)}</li>" for note in clean_notes) + "</ul>"


def _render_table(table: HtmlReportTable) -> str:
    headers = tuple(_clean_text(header) for header in table.headers if _clean_text(header))
    if not headers or not table.rows:
        return ""
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    rows: list[str] = []
    for row in table.rows:
        cells = tuple(row[: len(headers)])
        if not cells:
            continue
        body = "".join(f"<td>{escape(_clean_text(cell))}</td>" for cell in cells)
        rows.append(f"<tr>{body}</tr>")
    if not rows:
        return ""
    return (
        "<section class='report-section avoid-break'>"
        f"<h2>{escape(_clean_text(table.title) or 'Таблица')}</h2>"
        "<table class='report-table'>"
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></section>"
    )


def _render_tables(tables: Sequence[HtmlReportTable]) -> str:
    return "\n".join(html for table in tables if (html := _render_table(table)))


def _render_figures(figures: Sequence[object]) -> str:
    parts: list[str] = []
    include_plotlyjs = True
    for figure in figures:
        parts.append("<section class='report-section report-plot avoid-break'>")
        parts.append("<h2>Профессиональный планшет интерпретации</h2>")
        parts.append(pio.to_html(figure, include_plotlyjs=include_plotlyjs, full_html=False))
        parts.append("</section>")
        include_plotlyjs = False
    return "\n".join(parts)


def _technical_appendix_notice() -> str:
    return (
        "<section class='technical-appendix-notice'>"
        "<h2>Техническое приложение</h2>"
        "<p>Полные расчетные таблицы, диагностика, предупреждения качества данных и служебные сведения "
        "доступны в экспертном профиле отчета. Инженерный профиль намеренно показывает сначала выводы, "
        "интервалы, достоверность, рекомендации и ограничения.</p>"
        "</section>"
    )




def _render_document_table(table: DocumentTable) -> str:
    return _render_table(HtmlReportTable(title=table.title, headers=table.headers, rows=table.rows))


def _render_document_notice(notice: DocumentNotice) -> str:
    title = escape(_clean_text(notice.title) or "Примечание")
    text = escape(_clean_text(notice.text))
    css_class = "technical-appendix-notice" if notice.role == "technical-appendix-notice" else "report-section"
    return f"<section class='{css_class}'><h2>{title}</h2><p>{text}</p></section>"


def _render_document_plot(plot: DocumentPlot, *, include_plotlyjs: bool) -> str:
    figure = plot.figure
    native_svg = str(getattr(figure, "svg", "") or "").strip()
    if native_svg.startswith("<svg"):
        rendered_figure = f"<div class='visualization-preview'>{native_svg}</div>"
    else:
        rendered_figure = pio.to_html(
            figure,
            include_plotlyjs=include_plotlyjs,
            full_html=False,
        )
    return "\n".join(
        (
            "<section class='report-section report-plot avoid-break'>",
            f"<h2>{escape(_clean_text(plot.title) or 'Профессиональный планшет интерпретации')}</h2>",
            rendered_figure,
            "</section>",
        )
    )



def _render_visualization_preview(block: DocumentVisualizationPreview) -> str:
    preview = dict(block.preview or {})
    declared_pages = preview.get("page_svgs")
    pages = [str(item).strip() for item in declared_pages] if isinstance(declared_pages, (list, tuple)) else []
    if not pages:
        pages = [str(preview.get("svg") or "").strip()]
    pages = [item for item in pages if item.startswith("<svg")]
    if not pages:
        return ""
    meta = (
        f"Tracks: {escape(_clean_text(preview.get('track_count')))} · "
        f"Curves: {escape(_clean_text(preview.get('curve_count')))} · "
        f"Overlays: {escape(_clean_text(preview.get('overlay_count')))}"
    )
    rendered_pages = []
    for index, svg in enumerate(pages, start=1):
        page_class = " visualization-preview-page-next" if index > 1 else ""
        rendered_pages.append(
            f"<div class='visualization-preview-page{page_class}' data-page='{index}'>{svg}</div>"
        )
    return "\n".join((
        "<section class='report-section visualization-preview'>",
        f"<h2>{escape(_clean_text(block.title) or 'LAS visualization preview')}</h2>",
        *rendered_pages,
        f"<p class='visualization-preview-meta'>{meta} · Pages: {len(pages)}</p>",
        "</section>",
    ))

def _render_document_sections(document: EngineeringDocument) -> str:
    parts: list[str] = []
    include_plotlyjs = True
    for section in document.sections:
        section_classes = ["document-section"]
        if section.page_break_before:
            section_classes.append("page-break-before")
        if section.avoid_break_inside:
            section_classes.append("avoid-break")
        for block in section.blocks:
            if isinstance(block, DocumentTable):
                rendered = _render_document_table(block)
            elif isinstance(block, DocumentPlot):
                rendered = _render_document_plot(block, include_plotlyjs=include_plotlyjs)
                include_plotlyjs = False
            elif isinstance(block, DocumentVisualizationPreview):
                rendered = _render_visualization_preview(block)
            elif isinstance(block, DocumentNotice):
                rendered = _render_document_notice(block)
            else:
                rendered = ""
            if rendered:
                parts.append(rendered)
    return "\n".join(parts)


def select_presentation_tables(
    model: PresentationModel,
    *,
    include_technical_appendix: bool | None = None,
) -> tuple[HtmlReportTable, ...]:
    """Select the report table profile without rebuilding report content."""

    include_technical = (
        model.metadata.report_profile == "expert"
        if include_technical_appendix is None
        else bool(include_technical_appendix)
    )
    return model.expert_tables if include_technical else model.engineer_first_tables


def build_presentation_html_report(
    model: PresentationModel,
    *,
    options: PresentationHtmlOptions | None = None,
) -> PresentationHtmlResult:
    """Render an engineer-first printable HTML report from PresentationModel.

    The HTML renderer now consumes a renderer-neutral EngineeringDocument. This
    prevents HTML, future PDF and future DOCX exporters from duplicating
    engineering report composition rules.
    """

    opts = options or PresentationHtmlOptions()
    include_technical = opts.include_technical_appendix or model.metadata.report_profile == "expert"
    document = build_engineering_document(
        model,
        include_figures=opts.include_figures,
        include_technical_appendix=True if include_technical else None,
    )

    parts = [
        "<!doctype html>",
        f"<html lang='{escape(opts.language)}'><head><meta charset='utf-8'>",
        f"<title>{escape(document.metadata.title or opts.page_title)}</title>",
        "<style>",
        "body{font-family:Arial,sans-serif;margin:22px;color:#172033;background:#fff;}",
        ".report-cover{border-bottom:2px solid #d7dde8;margin-bottom:22px;padding-bottom:16px;}",
        "h1{font-size:25px;margin:0 0 8px 0;}",
        "h2{font-size:17px;margin:0 0 10px 0;}",
        ".subtitle{color:#4b5870;margin:0 0 14px 0;}",
        ".meta{border-collapse:collapse;margin-top:10px;font-size:13px;}",
        ".meta th{background:#f1f4f8;text-align:left;min-width:150px;}",
        ".meta th,.meta td{border:1px solid #d7dde8;padding:6px 9px;vertical-align:top;}",
        ".notes{font-size:12px;color:#4b5870;margin-top:12px;}",
        ".report-section{page-break-inside:avoid;margin:18px 0 24px 0;}",
        ".document-section{margin:0;}",
        ".report-table{border-collapse:collapse;width:100%;font-size:12px;}",
        ".report-table th{background:#f1f4f8;text-align:left;}",
        ".report-table th,.report-table td{border:1px solid #d7dde8;padding:5px 7px;vertical-align:top;white-space:pre-line;}",
        ".report-plot{page-break-before:always;}",
        ".visualization-preview{border:1px solid #d7dde8;padding:10px;margin:12px 0;background:#fff;}",
        ".visualization-preview svg{max-width:100%;height:auto;display:block;}",
        ".visualization-preview-meta{font-size:11px;color:#4b5870;margin-top:6px;}",
        ".technical-appendix-notice{border-top:1px solid #d7dde8;margin-top:28px;padding-top:14px;color:#4b5870;font-size:12px;}",
        _print_css(opts),
        "</style>",
        "</head><body>",
        "<section class='report-cover'>",
        f"<h1>{escape(document.metadata.title or opts.page_title)}</h1>",
    ]
    if document.metadata.subtitle:
        parts.append(f"<p class='subtitle'>{escape(document.metadata.subtitle)}</p>")
    parts.append(_metadata_table(document.metadata.rows))
    parts.append(_notes(document.metadata.notes))
    parts.append("</section>")
    parts.append(_render_document_sections(document))
    parts.append("</body></html>")

    return PresentationHtmlResult(
        content="\n".join(parts).encode("utf-8"),
        table_titles=document.table_titles,
        figure_count=document.plot_count + document.visualization_preview_count,
        profile=document.metadata.profile,
    )
