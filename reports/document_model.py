from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

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
class DocumentNotice:
    """Short renderer-neutral informational block."""

    title: str
    text: str
    role: str = "notice"


DocumentBlock = DocumentTable | DocumentPlot | DocumentNotice


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


def _technical_appendix_notice() -> DocumentNotice:
    return DocumentNotice(
        title="Техническое приложение",
        text=(
            "Полные расчетные таблицы, диагностика, предупреждения качества данных и служебные сведения "
            "доступны в экспертном профиле отчета. Инженерный профиль намеренно показывает сначала выводы, "
            "интервалы, достоверность, рекомендации и ограничения."
        ),
        role="technical-appendix-notice",
    )


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
    return tuple(DocumentTable.from_html_report_table(table) for table in source_tables)


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
    if tables:
        sections.append(
            DocumentSection(
                title="Инженерные разделы отчета" if not include_technical else "Разделы экспертного отчета",
                blocks=tables,
                page_break_before=False,
            )
        )

    if include_figures:
        plot_blocks = tuple(
            DocumentPlot(title="Профессиональный планшет интерпретации", figure=figure)
            for figure in model.figures
        )
        if plot_blocks:
            sections.append(
                DocumentSection(
                    title="Профессиональный планшет интерпретации",
                    blocks=plot_blocks,
                    page_break_before=True,
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
