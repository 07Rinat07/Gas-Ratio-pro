from pathlib import Path

from app import streamlit_app, workbench_renderer


def test_documentation_center_uses_interface_locale_and_manifest_documents():
    source = Path(streamlit_app.__file__).read_text(encoding="utf-8")
    assert "language = i18n.language" in source
    assert "_localized_documentation_documents(language)" in source
    assert '"kk": {' in source
    assert '"en": {' in source
    assert "DOCUMENTATION_TAB_DOCS" not in source[source.index("def _render_documentation_tab"):source.index("def _render_las_qc_panel")]


def test_global_language_switcher_has_three_site_style_buttons():
    source = Path(workbench_renderer.__file__).read_text(encoding="utf-8")
    assert 'labels = {"ru": "RU", "kk": "ҚАЗ", "en": "EN"}' in source
    assert 'key=f"workbench_language_button_{code}"' in source
    assert 'type="primary" if code == language else "secondary"' in source


def test_manifest_resolves_kazakh_and_english_documents():
    kk = streamlit_app._localized_documentation_documents("kk")
    en = streamlit_app._localized_documentation_documents("en")
    assert kk and en
    assert all(language == "kk" for _, _, language in kk)
    assert all(language == "en" for _, _, language in en)
    assert all("/kk/" in path for _, path, _ in kk)
    assert all("/en/" in path for _, path, _ in en)
