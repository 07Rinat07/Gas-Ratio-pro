from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Iterable

import plotly.io as pio


@dataclass(frozen=True)
class HtmlReportMetadata:
    title: str
    subtitle: str = ""
    rows: tuple[tuple[str, str], ...] = ()
    notes: tuple[str, ...] = ()


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

    include_plotlyjs = True
    for figure in figures:
        parts.append("<div class='chart'>")
        parts.append(pio.to_html(figure, include_plotlyjs=include_plotlyjs, full_html=False))
        parts.append("</div>")
        include_plotlyjs = False
    parts.append("</body></html>")
    return "\n".join(parts).encode("utf-8")
