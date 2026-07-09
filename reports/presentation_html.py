from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Sequence

import plotly.io as pio

from reports.export_html import HtmlReportMetadata, HtmlReportTable
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
        "<section class='report-section'>"
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
        parts.append("<section class='report-section report-plot'>")
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

    The resulting HTML is intentionally suitable for browser printing and future
    PDF conversion. It avoids technical row counters in the header and appends
    raw diagnostics only when the expert profile is explicitly requested.
    """

    opts = options or PresentationHtmlOptions()
    include_technical = opts.include_technical_appendix or model.metadata.report_profile == "expert"
    tables = select_presentation_tables(model, include_technical_appendix=include_technical)
    figures = model.figures if opts.include_figures else ()

    metadata = HtmlReportMetadata(
        title=model.metadata.title or opts.page_title,
        subtitle=model.metadata.subtitle,
        rows=model.metadata.as_report_rows(),
        notes=(
            "Каждая интерпретация является инженерной гипотезой и должна оцениваться совместно с ГИС, литологией, керном и испытаниями.",
        ),
        tables=tables,
    )

    parts = [
        "<!doctype html>",
        f"<html lang='{escape(opts.language)}'><head><meta charset='utf-8'>",
        f"<title>{escape(metadata.title)}</title>",
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
        ".report-table{border-collapse:collapse;width:100%;font-size:12px;}",
        ".report-table th{background:#f1f4f8;text-align:left;}",
        ".report-table th,.report-table td{border:1px solid #d7dde8;padding:5px 7px;vertical-align:top;white-space:pre-line;}",
        ".report-plot{page-break-before:always;}",
        ".technical-appendix-notice{border-top:1px solid #d7dde8;margin-top:28px;padding-top:14px;color:#4b5870;font-size:12px;}",
        "@media print{body{margin:10mm;} .report-section{page-break-inside:avoid;} .modebar{display:none!important;}}",
        "</style>",
        "</head><body>",
        "<section class='report-cover'>",
        f"<h1>{escape(metadata.title)}</h1>",
    ]
    if metadata.subtitle:
        parts.append(f"<p class='subtitle'>{escape(metadata.subtitle)}</p>")
    parts.append(_metadata_table(metadata.rows))
    parts.append(_notes(metadata.notes))
    parts.append("</section>")
    parts.append(_render_tables(tables))
    if figures:
        parts.append(_render_figures(figures))
    if not include_technical:
        parts.append(_technical_appendix_notice())
    parts.append("</body></html>")

    return PresentationHtmlResult(
        content="\n".join(parts).encode("utf-8"),
        table_titles=tuple(table.title for table in tables),
        figure_count=len(figures),
        profile="expert" if include_technical else "engineering",
    )
