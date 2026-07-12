from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Sequence

try:
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt
    DOCX_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - depends on user environment
    Document = None
    WD_ORIENT = WD_TABLE_ALIGNMENT = WD_CELL_VERTICAL_ALIGNMENT = WD_ALIGN_PARAGRAPH = None
    Inches = Pt = None
    DOCX_AVAILABLE = False

from reports.document_model import (
    DocumentNotice,
    DocumentPlot,
    DocumentVisualizationPreview,
    DocumentTable,
    EngineeringDocument,
    build_engineering_document,
)
from reports.presentation_model import PresentationModel


@dataclass(frozen=True)
class PresentationDocxOptions:
    """Options for renderer-neutral DOCX export.

    The DOCX renderer consumes EngineeringDocument only. It does not rerun gas
    ratio calculations, interpretation rules, evidence selection or report-card
    logic. This keeps HTML, PDF and DOCX synchronized through the same document
    model.
    """

    include_figures: bool = True
    include_technical_appendix: bool = False
    paper_size: str = "A4"
    orientation: str = "portrait"
    margin_mm: int = 14
    title: str = "Gas Ratio Professional Report"


@dataclass(frozen=True)
class PresentationDocxResult:
    """Rendered DOCX payload and document composition metadata."""

    content: bytes
    profile: str
    table_titles: tuple[str, ...]
    figure_count: int
    schema: str = "gas-ratio-pro/presentation/docx/v1"


def ensure_docx_available() -> None:
    """Raise a clear runtime error when DOCX export dependency is missing."""

    if not DOCX_AVAILABLE:
        raise RuntimeError(
            "DOCX export requires the optional dependency 'python-docx'. "
            "Install project dependencies with: pip install -r requirements.txt"
        )


def _clean_text(value: object) -> str:
    return str(value if value is not None else "").strip()


def _safe_orientation(value: str) -> str:
    text = str(value or "portrait").strip().lower()
    return text if text in {"portrait", "landscape"} else "portrait"


def _safe_margin_mm(value: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 14
    return max(6, min(number, 25))


def _safe_paper_size(value: str) -> tuple[float, float]:
    # Dimensions are inches because python-docx exposes section sizes in EMUs
    # via Length helpers. The values are standard ISO/US page sizes.
    text = str(value or "A4").strip().upper()
    sizes = {
        "A4": (8.27, 11.69),
        "A3": (11.69, 16.54),
        "LETTER": (8.5, 11.0),
    }
    return sizes.get(text, sizes["A4"])


def _configure_document(doc: Document, options: PresentationDocxOptions) -> None:
    section = doc.sections[0]
    width, height = _safe_paper_size(options.paper_size)
    if _safe_orientation(options.orientation) == "landscape":
        width, height = height, width
        section.orientation = WD_ORIENT.LANDSCAPE
    else:
        section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Inches(width)
    section.page_height = Inches(height)
    margin = Inches(_safe_margin_mm(options.margin_mm) / 25.4)
    section.left_margin = margin
    section.right_margin = margin
    section.top_margin = margin
    section.bottom_margin = margin

    styles = doc.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(9)
    for style_name, size in (("Title", 18), ("Heading 1", 14), ("Heading 2", 12)):
        try:
            styles[style_name].font.name = "Arial"
            styles[style_name].font.size = Pt(size)
        except KeyError:
            pass


def _add_paragraph(doc: Document, text: object, *, style: str | None = None, bold: bool = False) -> None:
    paragraph = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    run = paragraph.add_run(_clean_text(text))
    run.bold = bold


def _add_metadata_table(doc: Document, rows: Sequence[tuple[str, str]]) -> None:
    clean_rows = [(label, value) for label, value in rows if _clean_text(label) and _clean_text(value)]
    if not clean_rows:
        return
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.style = "Table Grid"
    for label, value in clean_rows:
        cells = table.add_row().cells
        cells[0].text = _clean_text(label)
        cells[1].text = _clean_text(value)
        for paragraph in cells[0].paragraphs:
            for run in paragraph.runs:
                run.bold = True
        for cell in cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    doc.add_paragraph()


def _add_document_table(doc: Document, block: DocumentTable) -> None:
    if not block.headers or not block.rows:
        return
    _add_paragraph(doc, block.title or "Таблица", style="Heading 2")
    table = doc.add_table(rows=1, cols=len(block.headers))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.style = "Table Grid"
    header_cells = table.rows[0].cells
    for index, header in enumerate(block.headers):
        header_cells[index].text = _clean_text(header)
        for paragraph in header_cells[index].paragraphs:
            for run in paragraph.runs:
                run.bold = True
    max_cols = len(block.headers)
    for source_row in block.rows:
        row_cells = table.add_row().cells
        cells = list(source_row[:max_cols])
        if len(cells) < max_cols:
            cells.extend([""] * (max_cols - len(cells)))
        for index, value in enumerate(cells):
            row_cells[index].text = _clean_text(value)
            row_cells[index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    doc.add_paragraph()


def _add_notice(doc: Document, block: DocumentNotice) -> None:
    _add_paragraph(doc, block.title or "Примечание", style="Heading 2")
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.15)
    run = paragraph.add_run(_clean_text(block.text))
    run.italic = block.role not in {"error", "warning"}
    doc.add_paragraph()


def _add_visualization_preview_placeholder(doc: Document, block: DocumentVisualizationPreview) -> None:
    _add_paragraph(doc, block.title or "LAS visualization preview", style="Heading 2")
    preview = dict(block.preview or {})
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(
        f"SVG preview prepared by Visualization Engine: "
        f"tracks={preview.get('track_count', 0)}, curves={preview.get('curve_count', 0)}, overlays={preview.get('overlay_count', 0)}."
    )
    run.italic = True
    doc.add_paragraph()


def _add_plot_placeholder(doc: Document, block: DocumentPlot) -> None:
    """Embed the shared Plotly figure into DOCX; never expose renderer placeholders."""
    _add_paragraph(doc, block.title or "Планшет", style="Heading 2")
    figure = block.figure
    try:
        if hasattr(figure, "to_image"):
            png = figure.to_image(format="png", width=1900, height=1200, scale=1)
        elif hasattr(figure, "write_image"):
            buffer = BytesIO()
            figure.write_image(buffer, format="png", width=1900, height=1200)
            png = buffer.getvalue()
        else:
            raise TypeError("Figure backend does not support raster export")
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.add_run().add_picture(BytesIO(png), width=Inches(6.35))
    except Exception as exc:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(
            "График не удалось встроить в DOCX. Проверьте установку совместимой версии Kaleido "
            f"({type(exc).__name__})."
        )
        run.italic = True
    doc.add_paragraph()


def render_engineering_document_docx(
    document: EngineeringDocument,
    *,
    options: PresentationDocxOptions | None = None,
) -> PresentationDocxResult:
    """Render a renderer-neutral EngineeringDocument into DOCX bytes."""

    opts = options or PresentationDocxOptions()
    ensure_docx_available()
    doc = Document()
    _configure_document(doc, opts)

    title = document.metadata.title or opts.title
    _add_paragraph(doc, title, style="Title")
    if document.metadata.subtitle:
        _add_paragraph(doc, document.metadata.subtitle)
    _add_metadata_table(doc, document.metadata.rows)
    for note in document.metadata.notes:
        _add_paragraph(doc, note)

    for section_index, section in enumerate(document.sections):
        if section.page_break_before and section_index > 0:
            doc.add_page_break()
        if section.title and (section_index > 0 or section.title not in {"Инженерные разделы отчета", "Разделы экспертного отчета"}):
            _add_paragraph(doc, section.title, style="Heading 1")
        for block in section.blocks:
            if isinstance(block, DocumentTable):
                _add_document_table(doc, block)
            elif isinstance(block, DocumentNotice):
                _add_notice(doc, block)
            elif isinstance(block, DocumentPlot):
                _add_plot_placeholder(doc, block)
            elif isinstance(block, DocumentVisualizationPreview):
                _add_visualization_preview_placeholder(doc, block)

    buffer = BytesIO()
    doc.save(buffer)
    return PresentationDocxResult(
        content=buffer.getvalue(),
        profile=document.metadata.profile,
        table_titles=document.table_titles,
        figure_count=document.plot_count + document.visualization_preview_count,
    )


def build_presentation_docx_report(
    model: PresentationModel,
    *,
    options: PresentationDocxOptions | None = None,
) -> PresentationDocxResult:
    """Render a DOCX report from PresentationModel through EngineeringDocument."""

    opts = options or PresentationDocxOptions()
    include_technical = opts.include_technical_appendix or model.metadata.report_profile == "expert"
    document = build_engineering_document(
        model,
        include_figures=opts.include_figures,
        include_technical_appendix=True if include_technical else None,
    )
    return render_engineering_document_docx(document, options=opts)


__all__ = [
    "PresentationDocxOptions",
    "PresentationDocxResult",
    "DOCX_AVAILABLE",
    "ensure_docx_available",
    "build_presentation_docx_report",
    "render_engineering_document_docx",
]
