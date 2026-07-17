from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import os
import sys
from typing import Sequence, Callable

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A3, A4, LETTER, landscape, portrait
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        Image,
        PageBreak,
        PageTemplate,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.platypus.tableofcontents import TableOfContents
    REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - depends on user environment
    colors = None
    TA_LEFT = None
    A3 = A4 = LETTER = landscape = portrait = None
    ParagraphStyle = getSampleStyleSheet = None
    mm = 1
    pdfmetrics = TTFont = None
    BaseDocTemplate = Frame = Image = PageBreak = PageTemplate = Paragraph = SimpleDocTemplate = Spacer = Table = TableStyle = None
    TableOfContents = None
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
from reports.plot_theme import apply_report_plot_theme


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
    show_page_chrome: bool = True
    document_code: str = "GRP-REPORT"
    footer_text: str = "Gas Ratio Pro · Engineering report"
    classification: str = "ENGINEERING USE"
    include_table_of_contents: bool = True
    include_pdf_bookmarks: bool = True


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


def _single_line(value: object, *, fallback: str = "", max_length: int = 96) -> str:
    """Normalize user-controlled page chrome text to one printable line."""

    text = " ".join(_clean_text(value).split()) or fallback
    return text[:max_length]


def _build_page_decorator(
    *,
    options: PresentationPdfOptions,
    document_title: str,
    page_size: tuple[float, float],
    regular_font: str,
    bold_font: str,
):
    """Create a deterministic ReportLab callback for industrial page chrome.

    The callback draws directly on the canvas and does not participate in the
    Platypus flow.  Header/footer geometry is therefore stable even when a long
    table is split across several pages.
    """

    width, height = page_size
    title = _single_line(document_title, fallback=options.title, max_length=72)
    document_code = _single_line(options.document_code, fallback="GRP-REPORT", max_length=32)
    footer_text = _single_line(options.footer_text, fallback="Gas Ratio Pro", max_length=72)
    classification = _single_line(options.classification, fallback="ENGINEERING USE", max_length=28)

    def decorate(canvas, doc) -> None:
        canvas.saveState()
        canvas.setAuthor("Gas Ratio Pro")
        canvas.setTitle(title)
        canvas.setSubject("Gas-ratio engineering interpretation report")
        canvas.setKeywords("gas ratio, LAS, mud gas, engineering report")

        # Header: document identity on the left, controlled document code on the right.
        canvas.setStrokeColor(colors.HexColor("#9aa8ba"))
        canvas.setLineWidth(0.45)
        canvas.line(doc.leftMargin, height - 13 * mm, width - doc.rightMargin, height - 13 * mm)
        canvas.setFillColor(colors.HexColor("#26364d"))
        canvas.setFont(bold_font, 7.5)
        canvas.drawString(doc.leftMargin, height - 9.5 * mm, title)
        canvas.setFont(regular_font, 7.2)
        canvas.drawRightString(width - doc.rightMargin, height - 9.5 * mm, document_code)

        # Footer: classification, product identity and physical page number.
        canvas.line(doc.leftMargin, 12 * mm, width - doc.rightMargin, 12 * mm)
        canvas.setFillColor(colors.HexColor("#4b5870"))
        canvas.setFont(bold_font, 6.8)
        canvas.drawString(doc.leftMargin, 8 * mm, classification)
        canvas.setFont(regular_font, 6.8)
        canvas.drawCentredString(width / 2.0, 8 * mm, footer_text)
        canvas.drawRightString(width - doc.rightMargin, 8 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    return decorate



class _EngineeringPdfDocTemplate(BaseDocTemplate):
    """ReportLab document template with deterministic TOC and PDF outlines."""

    def __init__(
        self,
        *args,
        on_first_page=None,
        on_later_pages=None,
        include_pdf_bookmarks: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._heading_counter = 0
        self._include_pdf_bookmarks = bool(include_pdf_bookmarks)
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="report-body",
        )
        self.addPageTemplates(
            [
                PageTemplate(
                    id="report-first",
                    frames=frame,
                    onPage=on_first_page or (lambda canvas, doc: None),
                    pagesize=self.pagesize,
                    autoNextPageTemplate="report-later",
                ),
                PageTemplate(
                    id="report-later",
                    frames=frame,
                    onPage=on_later_pages or (lambda canvas, doc: None),
                    pagesize=self.pagesize,
                ),
            ]
        )

    def beforeDocument(self) -> None:  # noqa: N802 - ReportLab API
        self._heading_counter = 0

    def afterFlowable(self, flowable) -> None:  # noqa: N802 - ReportLab API
        if not isinstance(flowable, Paragraph):
            return
        style_name = getattr(getattr(flowable, "style", None), "name", "")
        if style_name not in {"GasRatioTitle", "GasRatioHeading2"}:
            return
        text = flowable.getPlainText().strip()
        if not text:
            return
        is_title = style_name == "GasRatioTitle"
        level = 0 if is_title else 1
        key = f"grp-heading-{self._heading_counter}"
        self._heading_counter += 1
        self.canv.bookmarkPage(key)
        if self._include_pdf_bookmarks:
            self.canv.addOutlineEntry(text, key, level=level, closed=False)
        if not is_title and text != "Оглавление":
            self.notify("TOCEntry", (0, text, self.page, key))


def _table_of_contents(styles: dict[str, ParagraphStyle]) -> object:
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "GasRatioTocLevel1",
            parent=styles["body"],
            fontName=styles["body"].fontName,
            fontSize=9,
            leading=12,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=2,
        )
    ]
    return toc

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
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#4b5870"),
        ),
        "table_cell": ParagraphStyle(
            "GasRatioTableCell",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=8.5,
            leading=10.5,
        ),
        "table_header": ParagraphStyle(
            "GasRatioTableHeader",
            parent=base["BodyText"],
            fontName=bold,
            fontSize=8.5,
            leading=10.5,
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




def _adaptive_pdf_column_widths(headers: Sequence[str], rows: Sequence[Sequence[str]], *, total_width_mm: float = 160.0) -> list[float]:
    """Allocate printable widths from visible content without creating tiny cells."""
    if not headers:
        return []
    weights: list[float] = []
    for index, header in enumerate(headers):
        samples = [str(header)] + [str(row[index]) for row in rows[:40] if index < len(row)]
        longest = max((len(value.strip()) for value in samples), default=1)
        # Long narrative columns receive more space, numeric/ID columns remain compact.
        weight = max(4.0, min(22.0, longest ** 0.72))
        weights.append(weight)
    total = sum(weights) or 1.0
    raw = [total_width_mm * weight / total for weight in weights]
    minimum = 14.0 if len(headers) >= 7 else 18.0
    adjusted = [max(minimum, width) for width in raw]
    scale = total_width_mm / sum(adjusted)
    return [width * scale * mm for width in adjusted]


def _document_table(block: DocumentTable, styles: dict[str, ParagraphStyle]) -> list[object]:
    if not block.headers or not block.rows:
        return []
    original_cols = len(block.headers)
    # PDF must contain only actual engineering columns. Hidden renderer metadata
    # is never represented by a synthetic user-visible column.
    max_cols = min(original_cols, 8)
    visible_headers = list(block.headers[:max_cols])
    data: list[list[Paragraph]] = [
        [_paragraph(header, styles["table_header"]) for header in visible_headers]
    ]
    for row in block.rows:
        cells = list(row[:max_cols])
        if len(cells) < max_cols:
            cells.extend([""] * (max_cols - len(cells)))
        data.append([_paragraph(cell, styles["table_cell"]) for cell in cells])
    max_cols = len(visible_headers)

    # Technical appendix tables can contain many LAS/calculation columns.  Auto
    # column sizing may allocate a cell width smaller than ReportLab paddings,
    # which breaks PDF export.  Use deterministic compact widths so expert
    # reports stay printable even when tables are wide.
    compact = max_cols >= 7
    col_widths = _adaptive_pdf_column_widths(visible_headers, [list(row[:max_cols]) for row in block.rows])
    table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=col_widths)
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


def _figure_report_legend(figure: object) -> dict[str, object]:
    """Read renderer-neutral legend metadata embedded by the print plot builder."""

    layout = getattr(figure, "layout", None)
    meta = getattr(layout, "meta", None) if layout is not None else None
    if not isinstance(meta, dict):
        return {}
    payload = meta.get("gas_ratio_report_legend", {})
    return dict(payload) if isinstance(payload, dict) else {}


def _legend_table_pdf(
    title: str,
    entries: Sequence[dict[str, object]],
    styles: dict[str, ParagraphStyle],
    *,
    marker_mode: bool = False,
) -> list[object]:
    """Render a readable one-item-per-row legend for printed reports."""

    if not entries:
        return []
    rows: list[list[object]] = [[
        _paragraph("Знак", styles["table_header"]),
        _paragraph("Обозначение", styles["table_header"]),
        _paragraph("Инженерное значение", styles["table_header"]),
    ]]
    style_commands: list[tuple[object, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0f7")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_index, entry in enumerate(entries, start=1):
        color = str(entry.get("color", "#64748b"))
        symbol = str(entry.get("symbol", "◆" if marker_mode else "●"))
        rows.append([
            symbol,
            _paragraph(str(entry.get("label", "")), styles["small"]),
            _paragraph(str(entry.get("description", "")), styles["small"]),
        ])
        try:
            style_commands.append(("TEXTCOLOR", (0, row_index), (0, row_index), colors.HexColor(color)))
        except ValueError:
            pass
    table = Table(rows, colWidths=[12 * mm, 42 * mm, 114 * mm], hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle(style_commands))
    return [_paragraph(title, styles["h2"]), table, Spacer(1, 7)]


def _statistics_table_pdf(entries: Sequence[dict[str, object]], styles: dict[str, ParagraphStyle]) -> list[object]:
    if not entries:
        return []
    rows = [[_paragraph(name, styles["table_header"]) for name in ("Кривая", "Мин.", "Макс.", "Среднее", "Сумма")]]
    for entry in entries:
        rows.append([
            _paragraph(str(entry.get("label", "")), styles["table_cell"]),
            _paragraph(f"{float(entry.get('minimum', 0)):.4g}", styles["table_cell"]),
            _paragraph(f"{float(entry.get('maximum', 0)):.4g}", styles["table_cell"]),
            _paragraph(f"{float(entry.get('mean', 0)):.4g}", styles["table_cell"]),
            _paragraph(f"{float(entry.get('sum', 0)):.5g}", styles["table_cell"]),
        ])
    table = Table(rows, colWidths=[35*mm, 27*mm, 27*mm, 32*mm, 38*mm], hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eaf0f7")),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return [_paragraph("Статистика кривых", styles["h2"]), table, Spacer(1, 7)]


def _document_plot(block: DocumentPlot, styles: dict[str, ParagraphStyle]) -> list[object]:
    """Render a Plotly-compatible engineering figure into the PDF.

    Kaleido is used when available.  Failure is isolated to this block so the
    rest of the report remains downloadable, but the user receives an explicit
    dependency message instead of a silent placeholder.
    """

    title = block.title or "Профессиональный планшет интерпретации"
    items: list[object] = [_paragraph(title, styles["h2"])]
    figure = apply_report_plot_theme(block.figure)
    legend = _figure_report_legend(figure)
    depth_range = legend.get("depth_range", {}) if isinstance(legend.get("depth_range", {}), dict) else {}
    if depth_range:
        items.extend([
            _paragraph(
                f"Показан инженерно значимый диапазон глубин: "
                f"{float(depth_range.get('top', 0)):g}–{float(depth_range.get('base', 0)):g} м. "
                "Цветные зоны обозначают вероятный тип флюида; границы интервалов показаны маркерами кровли и подошвы.",
                styles["small"],
            ),
            Spacer(1, 5),
        ])
    intervals = list(legend.get("intervals", []) or [])
    if str(legend.get("report_kind", "")) == "detail" and intervals:
        card_rows = [[
            _paragraph("Интервал", styles["table_header"]),
            _paragraph("Глубина, м", styles["table_header"]),
            _paragraph("Мощность, м", styles["table_header"]),
            _paragraph("Флюид", styles["table_header"]),
            _paragraph("Достоверность", styles["table_header"]),
        ]]
        for item in intervals:
            card_rows.append([
                _paragraph(str(item.get("id", "")), styles["table_cell"]),
                _paragraph(f"{float(item.get('top', 0)):g}–{float(item.get('base', 0)):g}", styles["table_cell"]),
                _paragraph(f"{float(item.get('thickness', 0)):g}", styles["table_cell"]),
                _paragraph(str(item.get("fluid", "")), styles["table_cell"]),
                _paragraph(f"{float(item.get('confidence', 0)):g}%", styles["table_cell"]),
            ])
        card = Table(card_rows, colWidths=[24*mm, 34*mm, 28*mm, 42*mm, 32*mm], hAlign="LEFT")
        card.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eaf0f7")),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        items.extend([card, Spacer(1, 6)])
    try:
        if hasattr(figure, "to_image"):
            png = figure.to_image(format="png", width=2800, height=2400, scale=1)
        elif hasattr(figure, "write_image"):
            buffer = BytesIO()
            figure.write_image(buffer, format="png", width=2800, height=2400)
            png = buffer.getvalue()
        else:
            raise TypeError("Figure backend does not support raster export")
        image = Image(BytesIO(png))
        max_width = 185 * mm
        max_height = 205 * mm
        ratio = min(max_width / image.imageWidth, max_height / image.imageHeight)
        image.drawWidth = image.imageWidth * ratio
        image.drawHeight = image.imageHeight * ratio
        items.extend([image, Spacer(1, 8)])
        items.extend(_statistics_table_pdf(list(legend.get("statistics", []) or []), styles))
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
        include_technical_appendix=True if include_technical else None,
    )
    return render_engineering_document_pdf(document, options=opts)


def render_engineering_document_pdf(
    document: EngineeringDocument,
    *,
    options: PresentationPdfOptions | None = None,
    on_progress: Callable[[int, str], None] | None = None,
    check_cancelled: Callable[[], None] | None = None,
) -> PresentationPdfResult:
    """Render a renderer-neutral EngineeringDocument into PDF bytes.

    The function is deliberately deterministic and renderer-only: it consumes
    sections, tables, notices and plot placeholders from the Document Model and
    never rebuilds report content from lower-level hydrocarbon calculations.
    """

    def _check() -> None:
        if check_cancelled is not None:
            check_cancelled()

    def _progress(value: int, message: str) -> None:
        if on_progress is not None:
            on_progress(value, message)
        _check()

    _progress(2, "Инициализация PDF")
    ensure_reportlab_available()
    opts = options or PresentationPdfOptions()
    styles = _styles()
    buffer = BytesIO()
    margin = _safe_margin_mm(opts.margin_mm) * mm
    page_size = _page_size(opts)
    # Page chrome occupies fixed header/footer bands. Preserve the requested
    # content margin, but never allow flowables to overlap controlled-document
    # metadata or the physical page number.
    vertical_margin = max(margin, 18 * mm) if opts.show_page_chrome else margin
    decorator = None
    if opts.show_page_chrome:
        regular_font, bold_font = _register_fonts()
        decorator = _build_page_decorator(
            options=opts,
            document_title=document.metadata.title or opts.title,
            page_size=page_size,
            regular_font=regular_font,
            bold_font=bold_font,
        )
    doc = _EngineeringPdfDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=vertical_margin,
        bottomMargin=vertical_margin,
        title=document.metadata.title or opts.title,
        author="Gas Ratio Pro",
        subject="Gas-ratio engineering interpretation report",
        keywords="gas ratio, LAS, mud gas, engineering report",
        on_first_page=decorator,
        on_later_pages=decorator,
        include_pdf_bookmarks=opts.include_pdf_bookmarks,
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

    if opts.include_table_of_contents and document.sections:
        story.extend([
            PageBreak(),
            _paragraph("Оглавление", styles["h2"]),
            Spacer(1, 4),
            _table_of_contents(styles),
            PageBreak(),
        ])

    section_total = max(1, len(document.sections))
    for index, section in enumerate(document.sections):
        _progress(10 + int((index / section_total) * 68), f"PDF: раздел {index + 1} из {section_total}")
        if section.page_break_before and story:
            story.append(PageBreak())
        if section.title and (index > 0 or section.title not in {"Ключевые результаты", "Инженерные результаты и расчетные приложения"}):
            story.append(_paragraph(section.title, styles["h2"]))
        for block in section.blocks:
            _check()
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

    _progress(82, "Компоновка страниц PDF")
    if opts.include_table_of_contents:
        doc.multiBuild(story)
    else:
        doc.build(story)
    _progress(98, "PDF сформирован")
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
    "_build_page_decorator",
    "_font_candidates",
    "ensure_reportlab_available",
    "build_presentation_pdf_report",
    "render_engineering_document_pdf",
]
