from reports.report_designer import ReportDesign, build_report_structure_preview


def test_standard_mode_preview_resolves_renderer_configuration():
    preview = build_report_structure_preview(
        ReportDesign(
            mode_id="standard",
            template_id="minimal",  # mode must override stale manual selection
            title="  Well A engineering report  ",
            sections=("results",),
            include_technical_appendix=True,
            show_page_chrome=False,
        )
    )

    assert preview.ready is True
    assert preview.mode_label == "Стандартный"
    assert preview.template_label == "Corporate"
    assert preview.title == "Well A engineering report"
    assert tuple(item.id for item in preview.sections) == ("plots", "results", "conclusion")
    assert all(item.enabled for item in preview.sections)
    assert preview.include_figures is True
    assert preview.include_technical_appendix is False
    assert preview.show_page_chrome is True
    assert preview.include_table_of_contents is True
    assert preview.include_pdf_bookmarks is True


def test_brief_mode_preview_stays_compact():
    preview = build_report_structure_preview(ReportDesign(mode_id="brief"))

    assert tuple(item.id for item in preview.sections) == ("results", "conclusion")
    assert preview.include_figures is False
    assert preview.include_technical_appendix is False
    assert preview.include_table_of_contents is False
    assert preview.include_pdf_bookmarks is False
    assert preview.show_page_chrome is False


def test_custom_preview_reports_blocking_configuration_issues():
    preview = build_report_structure_preview(
        ReportDesign(mode_id="custom", title="", sections=())
    )

    assert preview.ready is False
    assert any(issue.code == "title.required" for issue in preview.issues)


def test_preview_marks_figure_sections_disabled_when_figures_are_off():
    preview = build_report_structure_preview(
        ReportDesign(
            mode_id="custom",
            sections=("plots", "visualizations", "results"),
            include_figures=False,
        )
    )

    enabled_by_id = {item.id: item.enabled for item in preview.sections}
    assert enabled_by_id == {
        "plots": False,
        "visualizations": False,
        "results": True,
    }


def test_preview_estimates_page_composition_without_rendering():
    preview = build_report_structure_preview(ReportDesign(mode_id="standard"))

    assert preview.estimated_min_pages > 0
    assert preview.estimated_max_pages >= preview.estimated_min_pages
    estimates = {item.id: item for item in preview.page_estimates}
    assert estimates["cover"].min_pages == 1
    assert estimates["toc"].enabled is True
    assert estimates["plots"].max_pages >= estimates["plots"].min_pages
    assert any(item.code == "design.ready" for item in preview.diagnostics)


def test_preview_excludes_disabled_figure_sections_from_page_total():
    preview = build_report_structure_preview(
        ReportDesign(
            mode_id="custom",
            sections=("plots", "results"),
            include_figures=False,
            include_table_of_contents=False,
            include_technical_appendix=False,
        )
    )

    estimates = {item.id: item for item in preview.page_estimates}
    assert estimates["plots"].enabled is False
    assert preview.estimated_min_pages == 2  # cover + results
    assert any(item.code == "sections.disabled" for item in preview.diagnostics)


def test_blocking_design_issue_is_reflected_in_readiness_diagnostics():
    preview = build_report_structure_preview(ReportDesign(mode_id="custom", title="", sections=()))

    assert preview.ready is False
    assert any(item.level == "error" and item.code == "design.blocked" for item in preview.diagnostics)

from reports.document_model import (
    DocumentMetadata,
    DocumentNotice,
    DocumentPlot,
    DocumentSection,
    DocumentTable,
    DocumentVisualizationPreview,
    EngineeringDocument,
)


def _sample_document() -> EngineeringDocument:
    return EngineeringDocument(
        metadata=DocumentMetadata(title="Well A"),
        sections=(
            DocumentSection(
                title="Results",
                blocks=(
                    DocumentTable("Intervals", ("Depth",), tuple((index,) for index in range(72))),
                    DocumentTable("Summary", ("Value",), ((1,), (2,))),
                    DocumentPlot("Ratios", object()),
                    DocumentPlot("Depth", object()),
                    DocumentPlot("Gas", object()),
                    DocumentVisualizationPreview("Tablet", {"svg": "<svg/>"}),
                    DocumentNotice("Limitations", "Text"),
                ),
            ),
        ),
    )


def test_document_model_counts_refine_page_estimate_without_rendering():
    preview = build_report_structure_preview(
        ReportDesign(mode_id="full_engineering"),
        document=_sample_document(),
        target_format="pdf",
    )

    estimates = {item.id: item for item in preview.page_estimates}
    assert estimates["plots"].min_pages == 2
    assert estimates["plots"].max_pages == 3
    assert estimates["results"].min_pages >= 3
    assert any(item.code == "estimate.document_counts" for item in preview.diagnostics)


def test_docx_readiness_warns_that_pdf_bookmarks_are_ignored():
    preview = build_report_structure_preview(
        ReportDesign(mode_id="standard"),
        document=_sample_document(),
        target_format="docx",
    )

    assert any(
        item.code == "format.docx.bookmarks_ignored" and item.level == "warning"
        for item in preview.diagnostics
    )


def test_pdf_readiness_warns_when_page_chrome_is_disabled():
    preview = build_report_structure_preview(
        ReportDesign(
            mode_id="custom",
            sections=("results",),
            show_page_chrome=False,
            include_pdf_bookmarks=False,
        ),
        target_format="pdf",
    )

    assert any(item.code == "format.pdf.no_page_chrome" for item in preview.diagnostics)
