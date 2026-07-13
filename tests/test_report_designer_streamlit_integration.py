from pathlib import Path


def test_streamlit_export_panel_uses_report_designer_contract():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "build_report_structure_preview" in source
    assert "build_designed_report_artifact(" in source
    assert '"Режим отчёта"' in source
    assert '"Шаблон оформления"' in source
    assert '"Разделы отчёта"' in source
    assert "mode={report_design.mode_id}" in source
    assert "template={report_design.template_id}" in source


def test_streamlit_export_panel_renders_structure_preview():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert '"Предпросмотр структуры отчёта"' in source
    assert "structure_preview.sections" in source
    assert "structure_preview.include_table_of_contents" in source
    assert "structure_preview.include_pdf_bookmarks" in source


def test_streamlit_preview_renders_format_capabilities():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "Возможности выбранного формата" in source
    assert "structure_preview.format_capabilities" in source
