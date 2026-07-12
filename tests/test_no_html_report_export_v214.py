from reports.presentation_ui import export_format_options, normalize_export_format


def test_user_facing_report_formats_do_not_include_html():
    formats = export_format_options()
    assert [item.id for item in formats] == ["pdf", "docx", "bundle"]
    assert all(item.extension != "html" for item in formats)
    assert normalize_export_format("html") == "pdf"


def test_interpretation_workspace_has_no_legacy_html_export_controls():
    source = open("app/streamlit_app.py", encoding="utf-8").read()
    assert "Подготовить HTML и отчет интервала" not in source
    assert "HTML графиков" not in source
    assert "gas_ratio_interval_report.html" not in source
    assert "Подготовить HTML корреляции" not in source
    assert "HTML для печати графика" not in source
