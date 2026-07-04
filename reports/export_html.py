from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Iterable, Sequence

import plotly.io as pio


@dataclass(frozen=True)
class HtmlReportTable:
    """Small escaped table section for printable engineering reports."""

    title: str
    headers: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]


@dataclass(frozen=True)
class HtmlReportMetadata:
    title: str
    subtitle: str = ""
    rows: tuple[tuple[str, str], ...] = ()
    notes: tuple[str, ...] = ()
    tables: tuple[HtmlReportTable, ...] = ()


STATIC_EXPORT_FORMATS: tuple[str, ...] = ("png", "pdf", "svg")


def _metadata_table(rows: Iterable[tuple[str, str]]) -> str:
    clean_rows = [
        (str(label).strip(), str(value).strip())
        for label, value in rows
        if str(label).strip() and str(value).strip()
    ]
    if not clean_rows:
        return ""
    table_rows = "\n".join(
        f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>"
        for label, value in clean_rows
    )
    return f"<table class='meta'>{table_rows}</table>"


def _notes_list(notes: Iterable[str]) -> str:
    clean_notes = [str(note).strip() for note in notes if str(note).strip()]
    if not clean_notes:
        return ""
    items = "\n".join(f"<li>{escape(note)}</li>" for note in clean_notes)
    return f"<ul class='notes'>{items}</ul>"



def _report_tables(tables: Sequence[HtmlReportTable]) -> str:
    sections: list[str] = []
    for table in tables:
        headers = tuple(str(header).strip() for header in table.headers if str(header).strip())
        if not headers or not table.rows:
            continue
        head_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
        body_rows: list[str] = []
        for row in table.rows:
            cells = tuple(row[: len(headers)])
            if not cells:
                continue
            cell_html = "".join(f"<td>{escape(str(value))}</td>" for value in cells)
            body_rows.append(f"<tr>{cell_html}</tr>")
        if not body_rows:
            continue
        title = escape(str(table.title).strip() or "Таблица")
        sections.append(
            "<section class='report-table-section'>"
            f"<h2>{title}</h2>"
            "<table class='report-table'>"
            f"<thead><tr>{head_html}</tr></thead>"
            f"<tbody>{''.join(body_rows)}</tbody>"
            "</table></section>"
        )
    return "\n".join(sections)

def build_plotly_html_report(figures, metadata: HtmlReportMetadata) -> bytes:
    title = str(metadata.title).strip() or "Gas Ratio Interpreter report"
    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'>",
        f"<title>{escape(title)}</title>",
        "<style>",
        "body{font-family:Arial,sans-serif;margin:24px;color:#172033;background:#fff;}",
        ".report-header{border-bottom:2px solid #d7dde8;margin-bottom:24px;padding-bottom:16px;}",
        "h1{font-size:24px;margin:0 0 8px 0;}",
        ".subtitle{color:#4b5870;margin:0 0 14px 0;}",
        ".meta{border-collapse:collapse;margin-top:10px;font-size:13px;}",
        ".meta th{background:#f1f4f8;text-align:left;min-width:150px;}",
        ".meta th,.meta td{border:1px solid #d7dde8;padding:6px 9px;vertical-align:top;}",
        ".report-table-section{page-break-inside:avoid;margin:18px 0 24px 0;}",
        ".report-table-section h2{font-size:17px;margin:0 0 8px 0;}",
        ".report-table{border-collapse:collapse;width:100%;font-size:12px;}",
        ".report-table th{background:#f1f4f8;text-align:left;}",
        ".report-table th,.report-table td{border:1px solid #d7dde8;padding:5px 7px;vertical-align:top;}",
        ".notes{font-size:12px;color:#4b5870;margin-top:12px;}",
        ".chart{page-break-inside:avoid;margin-bottom:28px;}",
        "@media print{body{margin:10mm;} .chart{page-break-inside:avoid;} .modebar{display:none!important;}}",
        "</style>",
        "</head><body>",
        "<section class='report-header'>",
        f"<h1>{escape(title)}</h1>",
    ]
    if metadata.subtitle:
        parts.append(f"<p class='subtitle'>{escape(metadata.subtitle)}</p>")
    parts.append(_metadata_table(metadata.rows))
    parts.append(_notes_list(metadata.notes))
    parts.append("</section>")
    table_html = _report_tables(metadata.tables)
    if table_html:
        parts.append(table_html)

    include_plotlyjs = True
    for figure in figures:
        parts.append("<div class='chart'>")
        parts.append(pio.to_html(figure, include_plotlyjs=include_plotlyjs, full_html=False))
        parts.append("</div>")
        include_plotlyjs = False
    parts.append("</body></html>")
    return "\n".join(parts).encode("utf-8")
