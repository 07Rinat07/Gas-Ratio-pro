from __future__ import annotations

"""Professional Report Designer for renderer-neutral engineering reports.

The designer changes only document composition and presentation options.  It
never recalculates gas ratios, intervals or interpretation results.  A single
``PresentationModel`` is converted to ``EngineeringDocument`` and then shaped
by the selected design before PDF/DOCX renderers consume it.
"""

from dataclasses import dataclass, replace
from typing import Literal

from reports.document_model import (
    DocumentNotice,
    DocumentPlot,
    DocumentTable,
    DocumentVisualizationPreview,
    EngineeringDocument,
    build_engineering_document,
)
from reports.presentation_docx import PresentationDocxOptions
from reports.presentation_model import PresentationModel
from reports.presentation_pdf import PresentationPdfOptions

ReportTemplateId = Literal["engineering", "corporate", "minimal"]
ReportModeId = Literal["custom", "brief", "standard", "full_engineering"]
ReportSectionId = Literal["plots", "visualizations", "results", "conclusion"]


@dataclass(frozen=True)
class ReportTemplate:
    id: ReportTemplateId
    label: str
    description: str
    default_sections: tuple[ReportSectionId, ...]
    include_technical_appendix: bool
    include_figures: bool
    paper_size: str = "A4"
    orientation: str = "portrait"
    margin_mm: int = 12
    show_page_chrome: bool = True
    include_table_of_contents: bool = True
    include_pdf_bookmarks: bool = True


@dataclass(frozen=True)
class ReportMode:
    id: ReportModeId
    label: str
    description: str
    template_id: ReportTemplateId
    sections: tuple[ReportSectionId, ...]
    include_figures: bool
    include_technical_appendix: bool
    show_page_chrome: bool
    include_table_of_contents: bool
    include_pdf_bookmarks: bool


@dataclass(frozen=True)
class ReportDesign:
    """User-selected professional report composition."""

    mode_id: ReportModeId = "custom"
    template_id: ReportTemplateId = "engineering"
    title: str = "Gas Ratio Professional Report"
    subtitle: str = "Инженерное заключение по вероятным УВ-интервалам"
    document_code: str = "GRP-REPORT"
    classification: str = "ENGINEERING USE"
    footer_text: str = "Gas Ratio Pro · Engineering report"
    sections: tuple[ReportSectionId, ...] = ()
    include_figures: bool | None = None
    include_technical_appendix: bool | None = None
    show_page_chrome: bool | None = None
    include_table_of_contents: bool | None = None
    include_pdf_bookmarks: bool | None = None
    paper_size: str = ""
    orientation: str = ""
    margin_mm: int | None = None


@dataclass(frozen=True)
class ReportDesignIssue:
    code: str
    message: str
    field: str
    blocking: bool = True


@dataclass(frozen=True)
class ReportDesignResult:
    design: ReportDesign
    document: EngineeringDocument | None
    pdf_options: PresentationPdfOptions | None
    docx_options: PresentationDocxOptions | None
    issues: tuple[ReportDesignIssue, ...] = ()

    @property
    def ready(self) -> bool:
        return self.document is not None and not any(issue.blocking for issue in self.issues)


_TEMPLATES: tuple[ReportTemplate, ...] = (
    ReportTemplate(
        id="engineering",
        label="Engineering",
        description="Полный инженерный отчет с планшетами, результатами и техническими приложениями.",
        default_sections=("plots", "visualizations", "results", "conclusion"),
        include_technical_appendix=True,
        include_figures=True,
        margin_mm=12,
    ),
    ReportTemplate(
        id="corporate",
        label="Corporate",
        description="Отчет для согласования и передачи заказчику с компактным составом разделов.",
        default_sections=("plots", "results", "conclusion"),
        include_technical_appendix=False,
        include_figures=True,
        margin_mm=14,
    ),
    ReportTemplate(
        id="minimal",
        label="Minimal",
        description="Краткое заключение с ключевыми результатами без графических приложений.",
        default_sections=("results", "conclusion"),
        include_technical_appendix=False,
        include_figures=False,
        margin_mm=16,
        show_page_chrome=False,
        include_table_of_contents=False,
        include_pdf_bookmarks=False,
    ),
)


_REPORT_MODES: tuple[ReportMode, ...] = (
    ReportMode(
        id="custom",
        label="По шаблону",
        description="Ручная настройка шаблона, разделов и приложений.",
        template_id="engineering",
        sections=(),
        include_figures=True,
        include_technical_appendix=True,
        show_page_chrome=True,
        include_table_of_contents=True,
        include_pdf_bookmarks=True,
    ),
    ReportMode(
        id="brief",
        label="Краткий",
        description="Ключевые результаты и заключение без графических приложений.",
        template_id="minimal",
        sections=("results", "conclusion"),
        include_figures=False,
        include_technical_appendix=False,
        show_page_chrome=False,
        include_table_of_contents=False,
        include_pdf_bookmarks=False,
    ),
    ReportMode(
        id="standard",
        label="Стандартный",
        description="Основные инженерные графики, результаты и заключение.",
        template_id="corporate",
        sections=("plots", "results", "conclusion"),
        include_figures=True,
        include_technical_appendix=False,
        show_page_chrome=True,
        include_table_of_contents=True,
        include_pdf_bookmarks=True,
    ),
    ReportMode(
        id="full_engineering",
        label="Полный инженерный",
        description="Полный комплект графиков, планшетов, результатов и технических приложений.",
        template_id="engineering",
        sections=("plots", "visualizations", "results", "conclusion"),
        include_figures=True,
        include_technical_appendix=True,
        show_page_chrome=True,
        include_table_of_contents=True,
        include_pdf_bookmarks=True,
    ),
)


def report_modes() -> tuple[ReportMode, ...]:
    return _REPORT_MODES


def report_mode_by_id(mode_id: str | None) -> ReportMode:
    normalized = str(mode_id or "custom").strip().lower()
    return next((item for item in _REPORT_MODES if item.id == normalized), _REPORT_MODES[0])


def resolve_report_design(design: ReportDesign) -> ReportDesign:
    """Apply a predefined report mode while preserving user metadata fields."""

    mode = report_mode_by_id(design.mode_id)
    if mode.id == "custom":
        return design
    return replace(
        design,
        template_id=mode.template_id,
        sections=mode.sections,
        include_figures=mode.include_figures,
        include_technical_appendix=mode.include_technical_appendix,
        show_page_chrome=mode.show_page_chrome,
        include_table_of_contents=mode.include_table_of_contents,
        include_pdf_bookmarks=mode.include_pdf_bookmarks,
    )

def report_templates() -> tuple[ReportTemplate, ...]:
    return _TEMPLATES


def report_template_by_id(template_id: str | None) -> ReportTemplate:
    normalized = str(template_id or "engineering").strip().lower()
    return next((item for item in _TEMPLATES if item.id == normalized), _TEMPLATES[0])


def _section_id(section) -> ReportSectionId:
    if any(isinstance(block, DocumentPlot) for block in section.blocks):
        return "plots"
    if any(isinstance(block, DocumentVisualizationPreview) for block in section.blocks):
        return "visualizations"
    if any(isinstance(block, DocumentTable) for block in section.blocks):
        return "results"
    if any(isinstance(block, DocumentNotice) for block in section.blocks):
        return "conclusion"
    return "conclusion"


def _clean_text(value: str, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def validate_report_design(design: ReportDesign) -> tuple[ReportDesignIssue, ...]:
    design = resolve_report_design(design)
    issues: list[ReportDesignIssue] = []
    template = report_template_by_id(design.template_id)
    sections = design.sections or template.default_sections

    if not str(design.title or "").strip():
        issues.append(ReportDesignIssue("title.required", "Не задан заголовок отчета.", "title"))
    if not sections:
        issues.append(ReportDesignIssue("sections.required", "Не выбран ни один раздел отчета.", "sections"))
    if len(set(sections)) != len(sections):
        issues.append(ReportDesignIssue("sections.duplicate", "Разделы отчета не должны повторяться.", "sections"))
    unknown = tuple(section for section in sections if section not in {"plots", "visualizations", "results", "conclusion"})
    if unknown:
        issues.append(ReportDesignIssue("sections.unknown", f"Неизвестные разделы: {', '.join(unknown)}.", "sections"))
    if design.margin_mm is not None and not 8 <= int(design.margin_mm) <= 40:
        issues.append(ReportDesignIssue("margin.invalid", "Поля должны быть от 8 до 40 мм.", "margin_mm"))
    return tuple(issues)


def build_designed_report(model: PresentationModel, design: ReportDesign | None = None) -> ReportDesignResult:
    """Build a customized document and synchronized PDF/DOCX options."""

    design = resolve_report_design(design or ReportDesign())
    issues = validate_report_design(design)
    if any(issue.blocking for issue in issues):
        return ReportDesignResult(design, None, None, None, issues)

    template = report_template_by_id(design.template_id)
    include_figures = template.include_figures if design.include_figures is None else bool(design.include_figures)
    include_technical = (
        template.include_technical_appendix
        if design.include_technical_appendix is None
        else bool(design.include_technical_appendix)
    )
    selected_sections = design.sections or template.default_sections

    source = build_engineering_document(
        model,
        include_figures=include_figures,
        include_technical_appendix=include_technical,
    )
    grouped = {section_id: [] for section_id in ("plots", "visualizations", "results", "conclusion")}
    for section in source.sections:
        grouped[_section_id(section)].append(section)

    ordered_sections = []
    for section_id in selected_sections:
        ordered_sections.extend(grouped.get(section_id, ()))

    title = _clean_text(design.title, source.metadata.title)
    subtitle = _clean_text(design.subtitle, source.metadata.subtitle)
    document = replace(
        source,
        metadata=replace(source.metadata, title=title, subtitle=subtitle),
        sections=tuple(ordered_sections),
        schema="gas-ratio-pro/document/designed/v1",
    )

    paper_size = str(design.paper_size or template.paper_size).strip().upper()
    orientation = str(design.orientation or template.orientation).strip().lower()
    margin_mm = template.margin_mm if design.margin_mm is None else int(design.margin_mm)
    page_chrome = template.show_page_chrome if design.show_page_chrome is None else bool(design.show_page_chrome)
    include_toc = (
        template.include_table_of_contents
        if design.include_table_of_contents is None
        else bool(design.include_table_of_contents)
    )
    include_bookmarks = (
        template.include_pdf_bookmarks
        if design.include_pdf_bookmarks is None
        else bool(design.include_pdf_bookmarks)
    )

    pdf_options = PresentationPdfOptions(
        include_figures=include_figures,
        include_technical_appendix=include_technical,
        paper_size=paper_size,
        orientation=orientation,
        margin_mm=margin_mm,
        title=title,
        show_page_chrome=page_chrome,
        document_code=_clean_text(design.document_code, "GRP-REPORT"),
        footer_text=_clean_text(design.footer_text, "Gas Ratio Pro · Engineering report"),
        classification=_clean_text(design.classification, "ENGINEERING USE"),
        include_table_of_contents=include_toc,
        include_pdf_bookmarks=include_bookmarks,
    )
    docx_options = PresentationDocxOptions(
        include_figures=include_figures,
        include_technical_appendix=include_technical,
        paper_size=paper_size,
        orientation=orientation,
        margin_mm=margin_mm,
        title=title,
    )
    return ReportDesignResult(design, document, pdf_options, docx_options, issues)


def require_designed_report(model: PresentationModel, design: ReportDesign | None = None) -> ReportDesignResult:
    result = build_designed_report(model, design)
    if not result.ready:
        message = "; ".join(issue.message for issue in result.issues if issue.blocking)
        raise ValueError(f"Report designer is not ready: {message}")
    return result


__all__ = [
    "ReportDesign",
    "ReportMode",
    "ReportModeId",
    "ReportDesignIssue",
    "ReportDesignResult",
    "ReportSectionId",
    "ReportTemplate",
    "ReportTemplateId",
    "build_designed_report",
    "report_mode_by_id",
    "report_modes",
    "report_template_by_id",
    "resolve_report_design",
    "report_templates",
    "require_designed_report",
    "validate_report_design",
]
