from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import os
import sys
from typing import Sequence

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A3, A4, LETTER, landscape, portrait
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - depends on user environment
    colors = None
    TA_LEFT = None
    A3 = A4 = LETTER = landscape = portrait = None
    ParagraphStyle = getSampleStyleSheet = None
    mm = 1
    pdfmetrics = TTFont = None
    Image = PageBreak = Paragraph = SimpleDocTemplate = Spacer = Table = TableStyle = None
    REPORTLAB_AVAILABLE = False

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
class PresentationPdfOptions:
    """Options for renderer-neutral PDF export.

    The PDF renderer consumes EngineeringDocument only. It must not rerun gas
    ratio calculations, interval detection or interpretation rules. This keeps
    HTML, future DOCX and PDF output synchronized with the same presentation
    content.
    """

    include_figures: bool = True
    include_technical_appendix: bool = False
    paper_size: str = "A4"
    orientation: str = "portrait"
    margin_mm: int = 12
    title: str = "Gas Ratio Professional Report"


@dataclass(frozen=True)
class PresentationPdfResult:
    """Rendered PDF payload and document composition metadata."""

    content: bytes
    profile: str
    table_titles: tuple[str, ...]
    figure_count: int
    schema: str = "gas-ratio-pro/presentation/pdf/v1"


_FONT_REGULAR = "GasRatioProSans"
_FONT_BOLD = "GasRatioProSans-Bold"


def _font_candidates() -> tuple[tuple[Path, Path], ...]:
    """Return Unicode-capable regular/bold font pairs for PDF rendering.

    The renderer must work on Windows, Linux and macOS because reports can be
    generated from a desktop workstation or a server.  Built-in PDF fonts such
    as Helvetica do not contain Cyrillic/Kazakh glyphs, therefore the renderer
    must actively discover a real TrueType/OpenType font.
    """

    project_root = Path(__file__).resolve().parents[1]
    configured_regular = os.getenv("GAS_RATIO_PRO_PDF_FONT")
    configured_bold = os.getenv("GAS_RATIO_PRO_PDF_FONT_BOLD")
    configured_pair: tuple[Path, Path] | None = None
    if configured_regular:
        regular = Path(configured_regular)
        bold = Path(configured_bold) if configured_bold else regular
        configured_pair = (regular, bold)

    candidates: list[tuple[Path, Path]] = []
    if configured_pair is not None:
        candidates.append(configured_pair)

    candidates.extend(
        [
            # Optional project-local fonts.  Do not commit proprietary system
            # fonts here; this path is for open fonts when the project owner
            # explicitly decides to bundle them.
            (project_root / "assets" / "fonts" / "NotoSans-Regular.ttf", project_root / "assets" / "fonts" / "NotoSans-Bold.ttf"),
            (project_root / "assets" / "fonts" / "DejaVuSans.ttf", project_root / "assets" / "fonts" / "DejaVuSans-Bold.ttf"),
            # Linux distributions.
            (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
            (Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"), Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf")),
            (Path("/usr/local/share/fonts/NotoSans-Regular.ttf"), Path("/usr/local/share/fonts/NotoSans-Bold.ttf")),
            # Windows.  Arial supports Russian and Kazakh Cyrillic glyphs on
            # standard Windows installations.
            (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
            (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf")),
            (Path("C:/Windows/Fonts/calibri.ttf"), Path("C:/Windows/Fonts/calibrib.ttf")),
            # macOS.
            (Path("/System/Library/Fonts/Supplemental/Arial.ttf"), Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")),
            (Path("/System/Library/Fonts/Supplemental/DejaVu Sans.ttf"), Path("/System/Library/Fonts/Supplemental/DejaVu Sans Bold.ttf")),
        ]
    )
    if sys.platform == "win32":
        windir = Path(os.environ.get("WINDIR", "C:/Windows"))
        candidates.extend(
            [
                (windir / "Fonts" / "arial.ttf", windir / "Fonts" / "arialbd.ttf"),
                (windir / "Fonts" / "segoeui.ttf", windir / "Fonts" / "segoeuib.ttf"),
                (windir / "Fonts" / "calibri.ttf", windir / "Fonts" / "calibrib.ttf"),
            ]
        )
    return tuple(candidates)


def _register_fonts() -> tuple[str, str]:
    """Register Unicode-capable fonts for multilingual engineering reports.

    ReportLab built-in Helvetica is not sufficient for Russian/Kazakh text and
    produces black square placeholders in PDF viewers.  This function searches
    project-local fonts first, then common Linux/Windows/macOS system fonts.
    """

    for regular, bold in _font_candidates():
        if regular.exists() and bold.exists():
            if _FONT_REGULAR not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(_FONT_REGULAR, str(regular)))
            if _FONT_BOLD not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(bold)))
            return _FONT_REGULAR, _FONT_BOLD
    raise RuntimeError(
        "PDF export requires a Unicode TrueType font for Russian/Kazakh text. "
        "Install Noto Sans/DejaVu Sans or set GAS_RATIO_PRO_PDF_FONT and "
        "GAS_RATIO_PRO_PDF_FONT_BOLD to valid .ttf files."
    )

def _safe_paper_size(value: str):
    text = str(value or "A4").strip().upper()
    return {"A4": A4, "A3": A3, "LETTER": LETTER}.get(text, A4)


def _safe_orientation(value: str) -> str:
    text = str(value or "portrait").strip().lower()
    return text if text in {"portrait", "landscape"} else "portrait"


def _safe_margin_mm(value: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 12
    return max(6, min(number, 25))


def _page_size(options: PresentationPdfOptions):
    base = _safe_paper_size(options.paper_size)
    return landscape(base) if _safe_orientation(options.orientation) == "landscape" else portrait(base)


def _clean_text(value: object) -> str:
    return str(value if value is not None else "").strip()


def _styles() -> dict[str, ParagraphStyle]:
    regular, bold = _register_fonts()
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "GasRatioTitle",
            parent=base["Title"],
            fontName=bold,
            fontSize=18,
            leading=22,
            spaceAfter=8,
            alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "GasRatioSubtitle",
            parent=base["Normal"],
            fontName=regular,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#4b5870"),
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "GasRatioHeading2",
            parent=base["Heading2"],
            fontName=bold,
            fontSize=13,
            leading=16,
            spaceBefore=8,
            spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "GasRatioBody",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=9,
            leading=12,
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "GasRatioSmall",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#4b5870"),
        ),
        "table_cell": ParagraphStyle(
            "GasRatioTableCell",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=7,
            leading=9,
        ),
        "table_header": ParagraphStyle(
            "GasRatioTableHeader",
            parent=base["BodyText"],
            fontName=bold,
            fontSize=7,
            leading=9,
        ),
    }


def _paragraph(text: object, style: ParagraphStyle) -> Paragraph:
    # ReportLab Paragraph accepts a small subset of XML. Escaping here keeps
    # user-provided well names and notes from being parsed as markup.
    from xml.sax.saxutils import escape

    return Paragraph(escape(_clean_text(text)), style)


def _metadata_table(rows: Sequence[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table | None:
    clean_rows = [(label, value) for label, value in rows if _clean_text(label) and _clean_text(value)]
    if not clean_rows:
        return None
    data = [[_paragraph(label, styles["table_header"]), _paragraph(value, styles["table_cell"])] for label, value in clean_rows]
    table = Table(data, colWidths=(45 * mm, 115 * mm), hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f4f8")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7dde8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d7dde8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _document_table(block: DocumentTable, styles: dict[str, ParagraphStyle]) -> list[object]:
    if not block.headers or not block.rows:
        return []
    original_cols = len(block.headers)
    max_cols = min(original_cols, 8)
    visible_headers = list(block.headers[:max_cols])
    if original_cols > max_cols:
        visible_headers.append("…")
    data: list[list[Paragraph]] = [
        [_paragraph(header, styles["table_header"]) for header in visible_headers]
    ]
    for row in block.rows:
        cells = list(row[:max_cols])
        if len(cells) < max_cols:
            cells.extend([""] * (max_cols - len(cells)))
        if original_cols > max_cols:
            cells.append(f"+{original_cols - max_cols} колонок в HTML/DOCX")
        data.append([_paragraph(cell, styles["table_cell"]) for cell in cells])
    max_cols = len(visible_headers)

    # Technical appendix tables can contain many LAS/calculation columns.  Auto
    # column sizing may allocate a cell width smaller than ReportLab paddings,
    # which breaks PDF export.  Use deterministic compact widths so expert
    # reports stay printable even when tables are wide.
    compact = max_cols > 8
    col_width = (12 * mm) if compact else max(22 * mm, min(42 * mm, (160 * mm) / max_cols))
    table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[col_width] * max_cols)
    cell_padding = 2 if compact else 4
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f4f8")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7dde8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d7dde8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), cell_padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), cell_padding),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return [_paragraph(block.title or "Таблица", styles["h2"]), table, Spacer(1, 8)]


def _document_notice(block: DocumentNotice, styles: dict[str, ParagraphStyle]) -> list[object]:
    return [
        _paragraph(block.title or "Примечание", styles["h2"]),
        _paragraph(block.text, styles["small"] if block.role == "technical-appendix-notice" else styles["body"]),
        Spacer(1, 6),
    ]


def _document_plot(block: DocumentPlot, styles: dict[str, ParagraphStyle]) -> list[object]:
    """Render a Plotly-compatible engineering figure into the PDF.

    Kaleido is used when available.  Failure is isolated to this block so the
    rest of the report remains downloadable, but the user receives an explicit
    dependency message instead of a silent placeholder.
    """

    title = block.title or "Профессиональный планшет интерпретации"
    items: list[object] = [_paragraph(title, styles["h2"])]
    figure = block.figure
    try:
        if hasattr(figure, "to_image"):
            png = figure.to_image(format="png", width=1500, height=2100, scale=1)
        elif hasattr(figure, "write_image"):
            buffer = BytesIO()
            figure.write_image(buffer, format="png", width=1500, height=2100)
            png = buffer.getvalue()
        else:
            raise TypeError("Figure backend does not support raster export")
        image = Image(BytesIO(png))
        max_width = 185 * mm
        max_height = 245 * mm
        ratio = min(max_width / image.imageWidth, max_height / image.imageHeight)
        image.drawWidth = image.imageWidth * ratio
        image.drawHeight = image.imageHeight * ratio
        items.extend([image, Spacer(1, 8)])
    except Exception as exc:
        items.extend([
            _paragraph(
                "График не встроен в PDF: установите совместимую версию kaleido "
                f"для статического экспорта Plotly ({type(exc).__name__}).",
                styles["small"],
            ),
            Spacer(1, 8),
        ])
    return items


def _document_visualization_preview(block: DocumentVisualizationPreview, styles: dict[str, ParagraphStyle]) -> list[object]:
    preview = dict(block.preview or {})
    return [
        _paragraph(block.title or "LAS visualization preview", styles["h2"]),
        _paragraph(
            f"SVG preview prepared by Visualization Engine: "
            f"tracks={preview.get('track_count', 0)}, curves={preview.get('curve_count', 0)}, overlays={preview.get('overlay_count', 0)}.",
            styles["small"],
        ),
        Spacer(1, 8),
    ]


def ensure_reportlab_available() -> None:
    """Raise a clear runtime error when PDF export dependency is missing."""

    if not REPORTLAB_AVAILABLE:
        raise RuntimeError(
            "PDF export requires the optional dependency 'reportlab'. "
            "Install project dependencies with: pip install -r requirements.txt"
        )


def build_presentation_pdf_report(
    model: PresentationModel,
    *,
    options: PresentationPdfOptions | None = None,
) -> PresentationPdfResult:
    """Render a print-ready PDF from PresentationModel through EngineeringDocument."""

    ensure_reportlab_available()
    opts = options or PresentationPdfOptions()
    include_technical = opts.include_technical_appendix or model.metadata.report_profile == "expert"
    document = build_engineering_document(
        model,
        include_figures=opts.include_figures,
        include_technical_appendix=include_technical,
    )
    return render_engineering_document_pdf(document, options=opts)


def render_engineering_document_pdf(
    document: EngineeringDocument,
    *,
    options: PresentationPdfOptions | None = None,
) -> PresentationPdfResult:
    """Render a renderer-neutral EngineeringDocument into PDF bytes.

    The function is deliberately deterministic and renderer-only: it consumes
    sections, tables, notices and plot placeholders from the Document Model and
    never rebuilds report content from lower-level hydrocarbon calculations.
    """

    ensure_reportlab_available()
    opts = options or PresentationPdfOptions()
    styles = _styles()
    buffer = BytesIO()
    margin = _safe_margin_mm(opts.margin_mm) * mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=_page_size(opts),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=document.metadata.title or opts.title,
        author="Gas Ratio Pro",
    )

    story: list[object] = []
    story.append(_paragraph(document.metadata.title or opts.title, styles["title"]))
    if document.metadata.subtitle:
        story.append(_paragraph(document.metadata.subtitle, styles["subtitle"]))
    metadata_table = _metadata_table(document.metadata.rows, styles)
    if metadata_table is not None:
        story.extend([metadata_table, Spacer(1, 8)])
    for note in document.metadata.notes:
        story.append(_paragraph(note, styles["small"]))
    if document.metadata.notes:
        story.append(Spacer(1, 8))

    for index, section in enumerate(document.sections):
        if section.page_break_before and story:
            story.append(PageBreak())
        if section.title and (index > 0 or section.title not in {"Инженерные разделы отчета", "Разделы экспертного отчета"}):
            story.append(_paragraph(section.title, styles["h2"]))
        for block in section.blocks:
            if isinstance(block, DocumentTable):
                story.extend(_document_table(block, styles))
            elif isinstance(block, DocumentNotice):
                story.extend(_document_notice(block, styles))
            elif isinstance(block, DocumentPlot):
                story.extend(_document_plot(block, styles))
            elif isinstance(block, DocumentVisualizationPreview):
                story.extend(_document_visualization_preview(block, styles))

    if not story:
        story.append(_paragraph("Gas Ratio Pro report", styles["body"]))

    doc.build(story)
    return PresentationPdfResult(
        content=buffer.getvalue(),
        profile=document.metadata.profile,
        table_titles=document.table_titles,
        figure_count=document.plot_count + document.visualization_preview_count,
    )


__all__ = [
    "PresentationPdfOptions",
    "PresentationPdfResult",
    "REPORTLAB_AVAILABLE",
    "_font_candidates",
    "ensure_reportlab_available",
    "build_presentation_pdf_report",
    "render_engineering_document_pdf",
]
