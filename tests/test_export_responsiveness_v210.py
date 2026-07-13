from pathlib import Path


def test_professional_export_is_explicit_and_format_aware():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "presentation_export_form_" in source
    assert "Подготовить выбранный формат" in source
    assert "presentation_export_started" in source
    assert "presentation_export_completed" in source
    assert "cached_export.get('format_label'" in source


def test_interpretation_figures_are_reused_when_settings_do_not_change():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "interpretation_figure_cache" in source
    assert "interpretation_plot_cache_hit" in source
    assert "interpretation_figure_cache_miss" in source
