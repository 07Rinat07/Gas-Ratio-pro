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
    assert 'start_page=effective_preview_start' in source
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


def test_pdf_preview_ui_contains_direct_page_jump_validation_feedback() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "validate_pdf_preview_page_jump(" in source
    assert "effective_preview_start" in source
    assert "page_jump_validation.adjusted" in source
    assert "Доступно страниц" in source


def test_pdf_preview_ui_contains_opt_in_adjacent_range_prefetch() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert '"Предзагрузить следующую группу страниц"' in source
    assert "next_pdf_preview_start_page(" in source
    assert "store_pdf_preview_cache(" in source
    assert "inspect_pdf_preview_cache(" in source
    assert "pdf_preview_prefetched" in source
    assert "max_entries=3" in source


def test_pdf_preview_cache_and_prefetch_telemetry_are_logged() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "pdf_preview_cache_lookup" in source
    assert "pdf_preview_prefetch_cache_hit" in source
    assert "duration_ms=%.2f bytes=%d backend=%s" in source
