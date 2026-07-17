from reports.report_designer import ReportDesign, report_template_by_id, resolve_page_layout


def test_auto_layout_uses_a3_landscape_for_visualizations():
    design = ReportDesign(template_id="engineering", orientation="auto", paper_size="AUTO", sections=("visualizations", "results"))
    paper, orientation = resolve_page_layout(design, report_template_by_id("engineering"), design.sections)
    assert (paper, orientation) == ("A3", "landscape")


def test_auto_layout_uses_a4_portrait_for_text_only():
    design = ReportDesign(template_id="engineering", orientation="auto", paper_size="AUTO", sections=("results", "conclusion"))
    paper, orientation = resolve_page_layout(design, report_template_by_id("engineering"), design.sections)
    assert (paper, orientation) == ("A4", "portrait")


def test_manual_layout_is_preserved():
    design = ReportDesign(template_id="engineering", orientation="portrait", paper_size="A3", sections=("visualizations",))
    paper, orientation = resolve_page_layout(design, report_template_by_id("engineering"), design.sections)
    assert (paper, orientation) == ("A3", "portrait")
