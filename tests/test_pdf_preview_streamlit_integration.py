from pathlib import Path


def test_professional_export_panel_contains_pdf_preview_controls() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert 'from reports.pdf_preview import (' in source
    assert 'with st.expander("Предпросмотр страниц PDF", expanded=False):' in source
    assert '"Создать предпросмотр"' in source
    assert 'presentation_pdf_preview_' in source
    assert 'build_pdf_preview_signature(' in source
    assert 'build_pdf_preview(' in source
