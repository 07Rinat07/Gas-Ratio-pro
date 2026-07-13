from pathlib import Path


def test_streamlit_export_panel_uses_report_designer_contract():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "from reports.report_designer import ReportDesign, report_modes, report_templates" in source
    assert "build_designed_report_artifact(" in source
    assert '"Режим отчёта"' in source
    assert '"Шаблон оформления"' in source
    assert '"Разделы отчёта"' in source
    assert "mode={report_design.mode_id}" in source
    assert "template={report_design.template_id}" in source
