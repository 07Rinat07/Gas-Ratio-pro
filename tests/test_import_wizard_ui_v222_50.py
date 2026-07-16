from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")


def test_professional_import_wizard_is_wired_to_data_workspace():
    assert "def _render_professional_import_wizard" in SOURCE
    assert "submit_batch_import_job" in SOURCE
    assert "retry_failed_import_job" in SOURCE
    assert "list_import_history" in SOURCE
    assert "_render_professional_import_wizard(logger, active_project)" in SOURCE


def test_wizard_uses_multilingual_keys_and_multiple_files():
    assert 'i18n("import.wizard.title")' in SOURCE
    assert "accept_multiple_files=True" in SOURCE
    assert 'i18n("import.wizard.retry")' in SOURCE
