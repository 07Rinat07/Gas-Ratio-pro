from pathlib import Path


def test_presentation_export_ui_uses_application_service_boundary() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "ExportWizardDraftRepository" not in source
    assert "ExportHistoryRepository" not in source
    assert "ReportPreviewCountsRepository" not in source
    assert "application_service_container(export_state).presentation_export" in source
    assert "export_application.load_draft()" in source
    assert "export_application.record_history(" in source
