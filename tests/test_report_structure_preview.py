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
