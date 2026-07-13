from __future__ import annotations

"""Professional Report Designer for renderer-neutral engineering reports.

The designer changes only document composition and presentation options.  It
never recalculates gas ratios, intervals or interpretation results.  A single
``PresentationModel`` is converted to ``EngineeringDocument`` and then shaped
by the selected design before PDF/DOCX renderers consume it.
"""

from dataclasses import asdict, dataclass, replace
import hashlib
import json
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
class ReportPreviewItem:
    """One renderer-neutral item shown in the report structure preview."""

    id: str
    label: str
    description: str
    enabled: bool = True


@dataclass(frozen=True)
class ReportPageEstimate:
    """Estimated page contribution of one report component."""

    id: str
    label: str
    min_pages: int
    max_pages: int
    enabled: bool = True


@dataclass(frozen=True)
class ReportDocumentCounts:
    """Lightweight block counts from an already assembled document model."""

    sections: int = 0
    tables: int = 0
    table_rows: int = 0
    plots: int = 0
    visualizations: int = 0
    notices: int = 0




def build_report_document_counts_signature(
    design: ReportDesign,
    *,
    target_format: str,
    depth_top: float,
    depth_bottom: float,
    source_signature: str = "",
    calculation_revision: int = 0,
    presentation_revision: int = 0,
) -> str:
    """Build a stable context signature for persisted document counts.

    Counts are valid only for the exact resolved design, output format, depth
    interval and source/revision context that produced the document model.
    """
    resolved = resolve_report_design(design)
    top, bottom = sorted((float(depth_top), float(depth_bottom)))
    payload = {
        "schema": 1,
        "design": asdict(resolved),
        "target_format": str(target_format or "").strip().lower().lstrip("."),
        "depth_top": top,
        "depth_bottom": bottom,
        "source_signature": str(source_signature or "").strip(),
        "calculation_revision": int(calculation_revision),
        "presentation_revision": int(presentation_revision),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReportReadinessDiagnostic:
    """Human-readable export-readiness diagnostic for the preview UI."""

    code: str
    level: str
    message: str


@dataclass(frozen=True)
class ReportFormatCapability:
    """One renderer capability exposed before binary export starts."""

    id: str
    label: str
    supported: bool
    detail: str


@dataclass(frozen=True)
class ReportStructurePreview:
    """Resolved report composition for UI review before rendering."""

    mode_label: str
    template_label: str
    title: str
    sections: tuple[ReportPreviewItem, ...]
    include_figures: bool
    include_technical_appendix: bool
    show_page_chrome: bool
    include_table_of_contents: bool
    include_pdf_bookmarks: bool
    paper_size: str
    orientation: str
    margin_mm: int
    page_estimates: tuple[ReportPageEstimate, ...] = ()
    estimated_min_pages: int = 0
    estimated_max_pages: int = 0
    diagnostics: tuple[ReportReadinessDiagnostic, ...] = ()
    format_capabilities: tuple[ReportFormatCapability, ...] = ()
    issues: tuple[ReportDesignIssue, ...] = ()

    @property
    def ready(self) -> bool:
        return bool(self.sections) and not any(issue.blocking for issue in self.issues)

    @property
    def enabled_section_count(self) -> int:
        return sum(1 for item in self.sections if item.enabled)


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




_SECTION_PAGE_ESTIMATES = {
    "plots": (2, 6),
    "visualizations": (2, 8),
    "results": (1, 4),
    "conclusion": (1, 2),
}


_SECTION_PREVIEW = {
    "plots": ("Инженерные графики", "Кривые, газовые отношения и глубинные графики."),
    "visualizations": ("Планшеты и визуализации", "Интерпретационные планшеты и графические приложения."),
    "results": ("Расчётные результаты", "Таблицы коэффициентов, интервалов и итоговых показателей."),
    "conclusion": ("Заключение и ограничения", "Инженерные выводы, ограничения метода и примечания."),
}


def report_document_counts(document: EngineeringDocument | None) -> ReportDocumentCounts | None:
    """Count renderer-neutral blocks without rebuilding engineering content."""
    if document is None:
        return None
    tables = table_rows = plots = visualizations = notices = 0
    for section in document.sections:
        for block in section.blocks:
            if isinstance(block, DocumentTable):
                tables += 1
                table_rows += len(block.rows)
            elif isinstance(block, DocumentPlot):
                plots += 1
            elif isinstance(block, DocumentVisualizationPreview):
                visualizations += 1
            elif isinstance(block, DocumentNotice):
                notices += 1
    return ReportDocumentCounts(
        sections=len(document.sections), tables=tables, table_rows=table_rows,
        plots=plots, visualizations=visualizations, notices=notices,
    )


def build_report_structure_preview(
    design: ReportDesign | None = None,
    *,
    document: EngineeringDocument | None = None,
    document_counts: ReportDocumentCounts | None = None,
    target_format: str | None = None,
) -> ReportStructurePreview:
    """Resolve report composition without building plots, tables or binary files.

    The function is intentionally lightweight and safe to call after every UI
    control change.  It mirrors the exact template/mode resolution used by the
    render pipeline, so the preview cannot drift from the exported document.
    """

    resolved = resolve_report_design(design or ReportDesign())
    template = report_template_by_id(resolved.template_id)
    mode = report_mode_by_id(resolved.mode_id)
    sections = resolved.sections or template.default_sections
    issues = validate_report_design(resolved)

    include_figures = template.include_figures if resolved.include_figures is None else bool(resolved.include_figures)
    include_technical = (
        template.include_technical_appendix
        if resolved.include_technical_appendix is None
        else bool(resolved.include_technical_appendix)
    )
    page_chrome = template.show_page_chrome if resolved.show_page_chrome is None else bool(resolved.show_page_chrome)
    include_toc = (
        template.include_table_of_contents
        if resolved.include_table_of_contents is None
        else bool(resolved.include_table_of_contents)
    )
    include_bookmarks = (
        template.include_pdf_bookmarks
        if resolved.include_pdf_bookmarks is None
        else bool(resolved.include_pdf_bookmarks)
    )

    preview_sections = tuple(
        ReportPreviewItem(
            id=section_id,
            label=_SECTION_PREVIEW[section_id][0],
            description=_SECTION_PREVIEW[section_id][1],
            enabled=(section_id not in {"plots", "visualizations"} or include_figures),
        )
        for section_id in sections
        if section_id in _SECTION_PREVIEW
    )

    page_estimates: list[ReportPageEstimate] = [
        ReportPageEstimate("cover", "Титульная страница", 1, 1),
    ]
    if include_toc:
        page_estimates.append(ReportPageEstimate("toc", "Оглавление", 1, 2))
    for item in preview_sections:
        min_pages, max_pages = _SECTION_PAGE_ESTIMATES[item.id]
        page_estimates.append(
            ReportPageEstimate(item.id, item.label, min_pages, max_pages, item.enabled)
        )
    if include_technical:
        page_estimates.append(ReportPageEstimate("technical_appendix", "Техническое приложение", 2, 6))

    counts = report_document_counts(document) if document is not None else document_counts
    if counts is not None:
        refined: list[ReportPageEstimate] = []
        for item in page_estimates:
            min_pages, max_pages = item.min_pages, item.max_pages
            if item.id == "plots" and item.enabled:
                min_pages = max(1, (counts.plots + 1) // 2) if counts.plots else 1
                max_pages = max(min_pages, counts.plots or 1)
            elif item.id == "visualizations" and item.enabled:
                min_pages = max(1, counts.visualizations)
                max_pages = max(min_pages, counts.visualizations * 2 or 1)
            elif item.id == "results" and item.enabled:
                row_pages = (counts.table_rows + 34) // 35
                min_pages = max(1, counts.tables, row_pages)
                max_pages = max(min_pages, counts.tables + (counts.table_rows + 19) // 20)
            elif item.id == "conclusion" and item.enabled:
                min_pages = 1
                max_pages = max(1, min(3, counts.notices + 1))
            refined.append(ReportPageEstimate(item.id, item.label, min_pages, max_pages, item.enabled))
        page_estimates = refined

    enabled_estimates = tuple(item for item in page_estimates if item.enabled)
    estimated_min_pages = sum(item.min_pages for item in enabled_estimates)
    estimated_max_pages = sum(item.max_pages for item in enabled_estimates)

    diagnostics: list[ReportReadinessDiagnostic] = []
    if any(issue.blocking for issue in issues):
        diagnostics.append(ReportReadinessDiagnostic(
            "design.blocked", "error", "Экспорт заблокирован: исправьте обязательные параметры отчёта."
        ))
    else:
        diagnostics.append(ReportReadinessDiagnostic(
            "design.ready", "success", "Структура отчёта готова к формированию PDF/DOCX."
        ))
    disabled_sections = tuple(item.label for item in preview_sections if not item.enabled)
    if disabled_sections:
        diagnostics.append(ReportReadinessDiagnostic(
            "sections.disabled", "warning",
            "Отключены разделы без графического содержимого: " + ", ".join(disabled_sections) + "."
        ))
    if estimated_max_pages >= 15:
        diagnostics.append(ReportReadinessDiagnostic(
            "pages.large", "info",
            "Ожидается объёмный отчёт; фоновый экспорт рекомендуется для стабильной работы интерфейса."
        ))
    if include_bookmarks and not include_toc:
        diagnostics.append(ReportReadinessDiagnostic(
            "navigation.bookmarks_only", "info",
            "PDF-закладки включены без печатного оглавления."
        ))

    normalized_format = str(target_format or "").strip().lower().lstrip(".")
    format_capabilities: list[ReportFormatCapability] = []
    capability_matrix = {
        "pdf": (
            ("paged_document", "Многостраничный документ", True, "Поддерживается промышленная PDF-пагинация."),
            ("table_of_contents", "Печатное оглавление", include_toc, "Формируется с фактическими номерами страниц." if include_toc else "Отключено настройками отчёта."),
            ("bookmarks", "PDF-закладки", include_bookmarks, "Добавляются в outline PDF." if include_bookmarks else "Отключены настройками отчёта."),
            ("editable_content", "Редактируемое содержимое", False, "PDF предназначен для распространения и печати, а не редактирования."),
        ),
        "docx": (
            ("paged_document", "Многостраничный документ", True, "Поддерживается редактируемый DOCX-документ."),
            ("table_of_contents", "Печатное оглавление", include_toc, "Добавляется поле оглавления DOCX." if include_toc else "Отключено настройками отчёта."),
            ("bookmarks", "PDF-закладки", False, "PDF outline не поддерживается форматом DOCX."),
            ("editable_content", "Редактируемое содержимое", True, "Текст и таблицы доступны для последующего редактирования."),
        ),
        "bundle": (
            ("paged_document", "PDF и DOCX в одном пакете", True, "ZIP-пакет содержит оба профессиональных документа."),
            ("table_of_contents", "Печатное оглавление", include_toc, "Применяется к PDF и DOCX." if include_toc else "Отключено настройками отчёта."),
            ("bookmarks", "PDF-закладки", include_bookmarks, "Применяются только к PDF внутри пакета." if include_bookmarks else "Отключены настройками отчёта."),
            ("editable_content", "Редактируемая версия", True, "DOCX включён в состав пакета."),
        ),
        "png": (
            ("paged_document", "Многостраничный документ", False, "PNG экспортирует отдельное растровое изображение."),
            ("table_of_contents", "Оглавление", False, "Не поддерживается статическим изображением."),
            ("bookmarks", "Закладки", False, "Не поддерживаются статическим изображением."),
            ("editable_content", "Редактируемое содержимое", False, "Результат является растровым изображением."),
        ),
        "svg": (
            ("paged_document", "Многостраничный документ", False, "SVG экспортирует отдельную векторную визуализацию."),
            ("table_of_contents", "Оглавление", False, "Не поддерживается отдельной SVG-визуализацией."),
            ("bookmarks", "Закладки", False, "Не поддерживаются отдельной SVG-визуализацией."),
            ("editable_content", "Векторное содержимое", True, "Геометрия может редактироваться в совместимом редакторе."),
        ),
        "xlsx": (
            ("paged_document", "Многостраничный документ", False, "XLSX является табличным экспортом, а не отчётом с пагинацией."),
            ("table_of_contents", "Оглавление", False, "Не применяется к табличному экспорту."),
            ("bookmarks", "Закладки", False, "Не применяются к табличному экспорту."),
            ("editable_content", "Редактируемые таблицы", True, "Данные доступны для анализа и редактирования в электронных таблицах."),
        ),
    }
    for capability_id, label, supported, detail in capability_matrix.get(normalized_format, ()):
        format_capabilities.append(ReportFormatCapability(capability_id, label, supported, detail))

    if normalized_format and normalized_format not in capability_matrix:
        diagnostics.append(ReportReadinessDiagnostic(
            "format.unknown", "warning",
            f"Для формата {normalized_format.upper()} не зарегистрирован профиль возможностей renderer-а."
        ))
    if normalized_format == "bundle" and include_bookmarks:
        diagnostics.append(ReportReadinessDiagnostic(
            "format.bundle.bookmarks_pdf_only", "info",
            "PDF-закладки будут добавлены только в PDF-файл внутри ZIP-пакета."
        ))
    if normalized_format in {"png", "svg", "xlsx"}:
        diagnostics.append(ReportReadinessDiagnostic(
            f"format.{normalized_format}.specialized_export", "info",
            "Выбран специализированный экспорт: настройки пагинации профессионального отчёта к нему не применяются."
        ))
    if normalized_format == "docx" and include_bookmarks:
        diagnostics.append(ReportReadinessDiagnostic(
            "format.docx.bookmarks_ignored", "warning",
            "PDF-закладки не применяются к DOCX; в документе сохранится только печатное оглавление."
        ))
    if normalized_format == "pdf" and not page_chrome:
        diagnostics.append(ReportReadinessDiagnostic(
            "format.pdf.no_page_chrome", "warning",
            "PDF формируется без колонтитулов и нумерации страниц."
        ))
    if normalized_format in {"pdf", "docx"} and counts is not None and counts.tables == 0:
        diagnostics.append(ReportReadinessDiagnostic(
            f"format.{normalized_format}.no_tables", "info",
            "В собранной модели документа отсутствуют табличные блоки."
        ))
    if counts is not None:
        diagnostics.append(ReportReadinessDiagnostic(
            "estimate.document_counts", "success",
            f"Оценка уточнена по модели документа: разделов {counts.sections}, таблиц {counts.tables}, "
            f"строк {counts.table_rows}, графиков {counts.plots}, планшетов {counts.visualizations}."
        ))

    return ReportStructurePreview(
        mode_label=mode.label,
        template_label=template.label,
        title=_clean_text(resolved.title, "Gas Ratio Professional Report"),
        sections=preview_sections,
        include_figures=include_figures,
        include_technical_appendix=include_technical,
        show_page_chrome=page_chrome,
        include_table_of_contents=include_toc,
        include_pdf_bookmarks=include_bookmarks,
        paper_size=str(resolved.paper_size or template.paper_size).strip().upper(),
        orientation=str(resolved.orientation or template.orientation).strip().lower(),
        margin_mm=template.margin_mm if resolved.margin_mm is None else int(resolved.margin_mm),
        page_estimates=tuple(page_estimates),
        estimated_min_pages=estimated_min_pages,
        estimated_max_pages=estimated_max_pages,
        diagnostics=tuple(diagnostics),
        format_capabilities=tuple(format_capabilities),
        issues=issues,
    )


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
    "ReportPreviewItem",
    "ReportPageEstimate",
    "ReportDocumentCounts",
    "report_document_counts",
    "build_report_document_counts_signature",
    "ReportFormatCapability",
    "ReportReadinessDiagnostic",
    "ReportStructurePreview",
    "ReportSectionId",
    "ReportTemplate",
    "ReportTemplateId",
    "build_designed_report",
    "build_report_structure_preview",
    "report_mode_by_id",
    "report_modes",
    "report_template_by_id",
    "resolve_report_design",
    "report_templates",
    "require_designed_report",
    "validate_report_design",
]
