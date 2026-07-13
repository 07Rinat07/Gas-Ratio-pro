from pathlib import Path


def test_professional_export_panel_contains_pdf_preview_controls() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert 'from reports.pdf_preview import (' in source
    assert 'with st.expander("Предпросмотр страниц PDF", expanded=False):' in source
    assert '"Создать предпросмотр"' in source
    assert 'presentation_pdf_preview_' in source
    assert 'build_pdf_preview_signature(' in source
    assert 'build_pdf_preview(' in source
    assert '"Две колонки"' in source
    assert 'render_duration_seconds' in source
    assert 'image_size_bytes' in source
    assert '"С первой страницы"' in source
    assert 'start_page=int(preview_start_page)' in source
    assert '"Очистить кэш предпросмотра"' in source
    assert 'pdf_preview_cache_cleared' in source


def test_pdf_preview_ui_contains_navigation_and_bounded_dpi_controls() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert '"Качество, DPI"' in source
    assert 'options=(72, 90, 110, 144, 180)' in source
    assert '"← Предыдущие"' in source
    assert '"Следующие →"' in source
    assert 'shift_pdf_preview_window(' in source
    assert 'dpi=preview_dpi' in source
