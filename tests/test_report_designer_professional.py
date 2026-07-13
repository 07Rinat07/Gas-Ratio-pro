from dataclasses import dataclass

from reports.document_model import DocumentNotice, DocumentPlot, DocumentTable
from reports.report_designer import (
    ReportDesign,
    build_designed_report,
    report_mode_by_id,
    report_modes,
    report_template_by_id,
    report_templates,
    resolve_report_design,
    validate_report_design,
)


@dataclass
class _Metadata:
    title: str = "Original"
    subtitle: str = "Original subtitle"
    report_profile: str = "engineering"

    def as_report_rows(self):
        return (("Проект", "Demo"),)


class _Model:
    metadata = _Metadata()
    figures = (object(),)
    visualization_previews = ()
    engineer_first_tables = ()
    expert_tables = ()


def test_templates_are_stable_and_have_safe_default():
    assert tuple(item.id for item in report_templates()) == ("engineering", "corporate", "minimal")
    assert report_template_by_id("unknown").id == "engineering"


def test_minimal_design_removes_plots_and_page_chrome():
    result = build_designed_report(_Model(), ReportDesign(template_id="minimal", title="Summary"))

    assert result.ready
    assert result.document is not None
    assert result.document.metadata.title == "Summary"
    assert all(not isinstance(block, DocumentPlot) for section in result.document.sections for block in section.blocks)
    assert result.pdf_options is not None
    assert result.pdf_options.show_page_chrome is False
    assert result.pdf_options.include_figures is False


def test_custom_section_order_is_applied(monkeypatch):
    from reports import report_designer as module
    from reports.document_model import DocumentMetadata, DocumentSection, EngineeringDocument

    base = EngineeringDocument(
        metadata=DocumentMetadata(title="Base"),
        sections=(
            DocumentSection("Plot", (DocumentPlot("P", object()),)),
            DocumentSection("Results", (DocumentTable("T", ("A",), ((1,),)),)),
            DocumentSection("Conclusion", (DocumentNotice("N", "Text"),)),
        ),
    )
    monkeypatch.setattr(module, "build_engineering_document", lambda *args, **kwargs: base)

    result = module.build_designed_report(
        _Model(),
        ReportDesign(title="Designed", sections=("conclusion", "results")),
    )

    assert result.ready
    assert result.document is not None
    assert tuple(section.title for section in result.document.sections) == ("Conclusion", "Results")
    assert result.document.schema == "gas-ratio-pro/document/designed/v1"


def test_design_preflight_rejects_missing_title_duplicates_and_bad_margin():
    issues = validate_report_design(
        ReportDesign(title="", sections=("results", "results"), margin_mm=80)
    )
    assert {issue.code for issue in issues} == {"title.required", "sections.duplicate", "margin.invalid"}


def test_designer_builds_synchronized_renderer_options():
    result = build_designed_report(
        _Model(),
        ReportDesign(
            template_id="corporate",
            title="Well A",
            subtitle="Final report",
            document_code="GRP-WA-01",
            classification="INTERNAL",
            footer_text="Approved output",
            orientation="landscape",
            margin_mm=18,
        ),
    )

    assert result.ready
    assert result.pdf_options is not None and result.docx_options is not None
    assert result.pdf_options.title == result.docx_options.title == "Well A"
    assert result.pdf_options.orientation == result.docx_options.orientation == "landscape"
    assert result.pdf_options.margin_mm == result.docx_options.margin_mm == 18
    assert result.pdf_options.document_code == "GRP-WA-01"
    assert result.pdf_options.classification == "INTERNAL"


def test_report_modes_are_stable_and_have_safe_fallback():
    assert tuple(item.id for item in report_modes()) == (
        "custom", "brief", "standard", "full_engineering"
    )
    assert report_mode_by_id("unknown").id == "custom"


def test_standard_mode_resolves_to_compact_corporate_report():
    resolved = resolve_report_design(
        ReportDesign(mode_id="standard", template_id="engineering", sections=("visualizations",))
    )
    assert resolved.template_id == "corporate"
    assert resolved.sections == ("plots", "results", "conclusion")
    assert resolved.include_figures is True
    assert resolved.include_technical_appendix is False


def test_full_engineering_mode_enables_all_sections_and_appendix():
    result = build_designed_report(_Model(), ReportDesign(mode_id="full_engineering", title="Full"))
    assert result.ready
    assert result.design.template_id == "engineering"
    assert result.design.sections == ("plots", "visualizations", "results", "conclusion")
    assert result.pdf_options is not None
    assert result.pdf_options.include_technical_appendix is True


def test_brief_mode_disables_figures_and_technical_appendix():
    result = build_designed_report(_Model(), ReportDesign(mode_id="brief", title="Brief"))
    assert result.ready
    assert result.design.template_id == "minimal"
    assert result.pdf_options is not None
    assert result.pdf_options.include_figures is False
    assert result.pdf_options.include_technical_appendix is False


def test_report_modes_control_toc_and_pdf_bookmarks():
    brief = build_designed_report(_Model(), ReportDesign(mode_id="brief", title="Brief"))
    full = build_designed_report(_Model(), ReportDesign(mode_id="full_engineering", title="Full"))

    assert brief.pdf_options is not None
    assert brief.pdf_options.include_table_of_contents is False
    assert brief.pdf_options.include_pdf_bookmarks is False
    assert full.pdf_options is not None
    assert full.pdf_options.include_table_of_contents is True
    assert full.pdf_options.include_pdf_bookmarks is True


def test_structure_preview_accepts_persisted_document_counts_without_document():
    from reports.report_designer import ReportDocumentCounts, build_report_structure_preview

    preview = build_report_structure_preview(
        ReportDesign(
            template_id="engineering",
            sections=("plots", "results", "conclusion"),
            include_technical_appendix=False,
        ),
        document_counts=ReportDocumentCounts(
            sections=5,
            tables=3,
            table_rows=81,
            plots=4,
            visualizations=0,
            notices=2,
        ),
        target_format="pdf",
    )

    estimates = {item.id: item for item in preview.page_estimates}
    assert estimates["plots"].min_pages == 2
    assert estimates["plots"].max_pages == 4
    assert estimates["results"].min_pages == 3
    assert estimates["results"].max_pages == 8
    assert any(item.code == "estimate.document_counts" for item in preview.diagnostics)


def test_explicit_document_takes_precedence_over_persisted_counts():
    from reports.document_model import DocumentMetadata, DocumentSection, EngineeringDocument
    from reports.report_designer import ReportDocumentCounts, build_report_structure_preview

    document = EngineeringDocument(
        metadata=DocumentMetadata(title="Actual"),
        sections=(DocumentSection("Results", (DocumentTable("T", ("A",), (("1",),)),)),),
    )
    preview = build_report_structure_preview(
        ReportDesign(template_id="minimal", sections=("results",)),
        document=document,
        document_counts=ReportDocumentCounts(tables=99, table_rows=9999),
        target_format="docx",
    )

    diagnostic = next(item for item in preview.diagnostics if item.code == "estimate.document_counts")
    assert "таблиц 1" in diagnostic.message
    assert "строк 1" in diagnostic.message
