from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from reports.export_html import HtmlReportTable
from reports.presentation_model import PresentationModel


@dataclass(frozen=True)
class DocumentMetadata:
    """Renderer-neutral metadata for generated engineering documents.

    This object intentionally stores only presentation metadata. Technical row
    counters, dataframe statistics and diagnostics remain optional appendix
    content and must not be promoted to the primary report header.
    """

    title: str
    subtitle: str = ""
    rows: tuple[tuple[str, str], ...] = ()
    notes: tuple[str, ...] = ()
    profile: str = "engineering"


@dataclass(frozen=True)
class DocumentTable:
    """Renderer-neutral table block.

    HTML, future PDF and future DOCX exporters should consume this block rather
    than rebuilding table content independently from PresentationModel.
    """

    title: str
    headers: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]

    @classmethod
    def from_html_report_table(cls, table: HtmlReportTable) -> "DocumentTable":
        return cls(title=table.title, headers=table.headers, rows=table.rows)


@dataclass(frozen=True)
class DocumentPlot:
    """Renderer-neutral plot block.

    The figure object is kept opaque so Plotly/Matplotlib/SVG renderers can be
    plugged in later without changing the engineering document structure.
    """

    title: str
    figure: object


@dataclass(frozen=True)
class DocumentVisualizationPreview:
    """Renderer-neutral visualization preview block for reports and exports.

    The block carries a prepared SVG preview from the Visualization Engine.
    Concrete renderers may embed it or show a placeholder, but they must not
    reconstruct LAS curves or interval overlays from raw source data.
    """

    title: str
    preview: Mapping[str, Any]


@dataclass(frozen=True)
class DocumentNotice:
    """Short renderer-neutral informational block."""

    title: str
    text: str
    role: str = "notice"


DocumentBlock = DocumentTable | DocumentPlot | DocumentVisualizationPreview | DocumentNotice


@dataclass(frozen=True)
class DocumentSection:
    """Logical document section shared by HTML, PDF, DOCX and UI renderers."""

    title: str
    blocks: tuple[DocumentBlock, ...] = ()
    page_break_before: bool = False
    avoid_break_inside: bool = True


@dataclass(frozen=True)
class EngineeringDocument:
    """Single document object model for all report formats.

    The key architectural rule is: engineering content is assembled once into
    this model, and format-specific renderers only draw it. They must not rerun
    interpretation rules, rebuild interval cards or select different interval
    lists.
    """

    metadata: DocumentMetadata
    sections: tuple[DocumentSection, ...]
    schema: str = "gas-ratio-pro/document/model/v1"

    @property
    def table_titles(self) -> tuple[str, ...]:
        titles: list[str] = []
        for section in self.sections:
            for block in section.blocks:
                if isinstance(block, DocumentTable):
                    titles.append(block.title)
        return tuple(titles)

    @property
    def plot_count(self) -> int:
        return sum(
            1
            for section in self.sections
            for block in section.blocks
            if isinstance(block, DocumentPlot)
        )

    @property
    def visualization_preview_count(self) -> int:
        return sum(
            1
            for section in self.sections
            for block in section.blocks
            if isinstance(block, DocumentVisualizationPreview)
        )


def _technical_appendix_notice() -> DocumentNotice:
    return DocumentNotice(
        title="Техническое приложение: состав",
        text=(
            "Полные расчетные таблицы, диагностика, предупреждения качества данных и служебные сведения "
            "доступны в экспертном профиле отчета. Инженерный профиль намеренно показывает сначала выводы, "
            "интервалы, достоверность, рекомендации и ограничения."
        ),
        role="technical-appendix-notice",
    )


_USER_TEXT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("contains_missing_ratio_values", "Имеются пропуски отдельных расчетных коэффициентов"),
    ("Data confidence", "Достоверность данных"),
    ("geological confidence", "Геологическая достоверность"),
    ("decreasing", "снижающийся"),
    ("increasing", "возрастающий"),
    ("stable", "стабильный"),
    ("above:", "выше: "),
    ("below:", "ниже: "),
    ("вероятному нефтяной коллектору", "вероятному нефтяному коллектору"),
    ("вероятному газовый коллектору", "вероятному газовому коллектору"),
    ("вероятному газоконденсатный коллектору", "вероятному газоконденсатному коллектору"),
)


def _clean_user_cell(value: object) -> str:
    text = "" if value is None else str(value)
    for source, target in _USER_TEXT_REPLACEMENTS:
        text = text.replace(source, target)
    return text


def _printable_table(table: HtmlReportTable, *, technical: bool) -> DocumentTable:
    # Raw dictionaries, evidence trees and rule traces belong in CSV/JSON, not
    # in a printable engineering report. Keep a bounded, human-readable appendix.
    headers = list(table.headers)
    rows = list(table.rows)
    blocked = {
        "context", "evidence_tree", "explanation", "confidence_factors",
        "applied_rule_ids", "rule_traces", "evidence_items",
        "evidence_provenance", "structured_limitations",
        "structured_recommendations",
    }
    keep_indexes = [i for i, header in enumerate(headers) if str(header) not in blocked]
    if technical and len(keep_indexes) > 10:
        keep_indexes = keep_indexes[:10]
    if technical:
        rows = rows[:40]
    clean_headers = tuple(_clean_user_cell(headers[i]) for i in keep_indexes)
    clean_rows = tuple(
        tuple(_clean_user_cell(row[i]) if i < len(row) else "" for i in keep_indexes)
        for row in rows
    )
    return DocumentTable(title=_clean_user_cell(table.title), headers=clean_headers, rows=clean_rows)


def select_document_tables(
    model: PresentationModel,
    *,
    include_technical_appendix: bool | None = None,
) -> tuple[DocumentTable, ...]:
    """Select report tables from PresentationModel and convert to Document blocks.

    This function is the document-level equivalent of the table selector used by
    the previous HTML renderer. It is intentionally deterministic and does not
    rebuild or reinterpret any engineering content.
    """

    include_technical = (
        model.metadata.report_profile == "expert"
        if include_technical_appendix is None
        else bool(include_technical_appendix)
    )
    source_tables = model.expert_tables if include_technical else model.engineer_first_tables
    engineering_ids = {id(table) for table in model.engineer_first_tables}
    return tuple(
        _printable_table(table, technical=id(table) not in engineering_ids)
        for table in source_tables
    )


def build_engineering_document(
    model: PresentationModel,
    *,
    include_figures: bool = True,
    include_technical_appendix: bool | None = None,
) -> EngineeringDocument:
    """Build a renderer-neutral document from PresentationModel.

    This is the foundation for consistent HTML, PDF, DOCX and future UI report
    renderers. Only this function decides the engineering document composition;
    concrete renderers must consume the resulting blocks.
    """

    include_technical = (
        model.metadata.report_profile == "expert"
        if include_technical_appendix is None
        else bool(include_technical_appendix)
    )
    tables = select_document_tables(model, include_technical_appendix=include_technical)

    sections: list[DocumentSection] = []

    # Put the engineering visualization immediately after the executive
    # metadata.  Previously dozens of table pages pushed the well-log plot to
    # the end of the PDF, making the report look like a raw table dump.
    if include_figures:
        plot_blocks = tuple(
            DocumentPlot(title="Профессиональный планшет интерпретации", figure=figure)
            for figure in model.figures
        )
        preview_blocks = tuple(
            DocumentVisualizationPreview(title="LAS visualization preview", preview=preview)
            for preview in model.visualization_previews
        )
        combined_blocks = plot_blocks + preview_blocks
        if combined_blocks:
            sections.append(
                DocumentSection(
                    title="Графическая интерпретация",
                    blocks=combined_blocks,
                    page_break_before=False,
                )
            )

    if tables:
        sections.append(
            DocumentSection(
                title="Инженерные разделы отчета" if not include_technical else "Разделы экспертного отчета",
                blocks=tables,
                page_break_before=bool(sections),
            )
        )

    if not include_technical:
        sections.append(
            DocumentSection(
                title="Техническое приложение",
                blocks=(_technical_appendix_notice(),),
                page_break_before=False,
            )
        )

    metadata = DocumentMetadata(
        title=model.metadata.title,
        subtitle=model.metadata.subtitle,
        rows=model.metadata.as_report_rows(),
        notes=(
            "Каждая интерпретация является инженерной гипотезой и должна оцениваться совместно с ГИС, литологией, керном и испытаниями.",
        ),
        profile="expert" if include_technical else "engineering",
    )
    return EngineeringDocument(metadata=metadata, sections=tuple(sections))
