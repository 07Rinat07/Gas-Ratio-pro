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


def _report_scope_notice(*, engineering: bool) -> DocumentNotice:
    if engineering:
        return DocumentNotice(
            title="Область применения",
            text=("Результаты предназначены для инженерной интерпретации и должны рассматриваться совместно "
                  "с материалами ГИС, литологией, керном, испытаниями и данными разработки."),
            role="engineering-scope",
        )
    return DocumentNotice(
        title="Ограничения интерпретации",
        text=("Выводы отражают интерпретацию доступных данных газового каротажа. Окончательные решения "
              "принимаются после сопоставления с материалами ГИС, испытаниями и геологической моделью."),
        role="client-limitations",
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
    if technical and len(keep_indexes) > 6:
        keep_indexes = keep_indexes[:6]
    if technical:
        rows = rows[:20]
    clean_headers = tuple(_clean_user_cell(headers[i]) for i in keep_indexes)
    clean_rows = tuple(
        tuple(_clean_user_cell(row[i]) if i < len(row) else "" for i in keep_indexes)
        for row in rows
    )
    return DocumentTable(title=_clean_user_cell(table.title), headers=clean_headers, rows=clean_rows)


def _client_table(table: HtmlReportTable) -> DocumentTable:
    """Return a compact customer-facing table without internal fields."""
    printable = _printable_table(table, technical=False)
    headers = printable.headers[:6]
    rows = tuple(row[: len(headers)] for row in printable.rows[:12])
    return DocumentTable(title=printable.title, headers=headers, rows=rows)


def _client_tables(model: PresentationModel) -> tuple[DocumentTable, ...]:
    preferred = ("заключ", "интервал", "достовер", "рекоменд", "огранич")
    selected = [table for table in model.engineer_first_tables if any(key in str(table.title).lower() for key in preferred)]
    if not selected:
        selected = list(model.engineer_first_tables[:4])
    return tuple(_client_table(table) for table in selected[:5])


def _clean_metadata_rows(rows: Sequence[tuple[str, str]], *, engineering: bool) -> tuple[tuple[str, str], ...]:
    blocked = ("id", "schema", "renderer", "version", "hash", "path", "source_label", "profile")
    clean = []
    for key, value in rows:
        label = _clean_user_cell(key).strip()
        if any(token in label.lower() for token in blocked):
            continue
        clean.append((label, _clean_user_cell(value)))
    return tuple(clean if engineering else clean[:6])


def select_document_tables(
    model: PresentationModel,
    *,
    include_technical_appendix: bool | None = None,
) -> tuple[DocumentTable, ...]:
    """Select client, engineering or technical tables without rebuilding data."""
    profile = str(model.metadata.report_profile or "engineering").strip().lower()
    if include_technical_appendix is False:
        return _client_tables(model)
    include_technical = bool(include_technical_appendix) or profile == "expert"
    if profile in {"client", "customer"} and include_technical_appendix is None:
        return _client_tables(model)
    source_tables = model.expert_tables if include_technical else model.engineer_first_tables
    engineering_ids = {id(table) for table in model.engineer_first_tables}
    return tuple(
        _printable_table(table, technical=include_technical and id(table) not in engineering_ids)
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

    profile = str(model.metadata.report_profile or "engineering").strip().lower()
    client_mode = include_technical_appendix is False or (
        include_technical_appendix is None and profile in {"client", "customer"}
    )
    include_technical = bool(include_technical_appendix) or profile == "expert"
    tables = select_document_tables(
        model,
        include_technical_appendix=(
            include_technical_appendix if include_technical_appendix is not None else None
        ),
    )

    sections: list[DocumentSection] = []

    # Put the engineering visualization immediately after the executive
    # metadata.  Previously dozens of table pages pushed the well-log plot to
    # the end of the PDF, making the report look like a raw table dump.
    if include_figures:
        def _plot_meta(figure: object) -> dict[str, object]:
            try:
                meta = dict(getattr(getattr(figure, "layout", None), "meta", {}) or {})
                return dict(meta.get("gas_ratio_report_legend", {}) or {})
            except Exception:
                return {}

        for figure_index, figure in enumerate(model.figures):
            meta = _plot_meta(figure)
            title = str(meta.get("report_title") or "Профессиональный планшет интерпретации")
            kind = str(meta.get("report_kind") or "overview")
            sections.append(
                DocumentSection(
                    title="",
                    blocks=(DocumentPlot(title=title, figure=figure),),
                    page_break_before=bool(sections) and kind == "detail",
                )
            )

        preview_blocks = tuple(
            DocumentVisualizationPreview(title="LAS visualization preview", preview=preview)
            for preview in model.visualization_previews
        )
        if preview_blocks:
            sections.append(DocumentSection(title="", blocks=preview_blocks, page_break_before=False))

    if tables:
        sections.append(
            DocumentSection(
                title="Ключевые результаты" if not include_technical else "Инженерные результаты и расчетные приложения",
                blocks=tables,
                page_break_before=bool(sections),
            )
        )

    sections.append(
        DocumentSection(
            title="Заключение и ограничения",
            blocks=(_report_scope_notice(engineering=include_technical),),
            page_break_before=False,
        )
    )

    metadata = DocumentMetadata(
        title=model.metadata.title,
        subtitle=model.metadata.subtitle,
        rows=_clean_metadata_rows(model.metadata.as_report_rows(), engineering=include_technical),
        notes=(
            "Каждая интерпретация является инженерной гипотезой и должна оцениваться совместно с ГИС, литологией, керном и испытаниями.",
        ),
        profile="client" if client_mode else "engineering",
    )
    return EngineeringDocument(metadata=metadata, sections=tuple(sections))
