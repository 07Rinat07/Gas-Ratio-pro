from pathlib import Path


def test_static_export_controls_do_not_capture_workspace_locals() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    start = source.index("def _render_static_export_controls(")
    end = source.index("\ndef _las_editor_reference_state", start)
    function_source = source[start:end]

    assert "active_project" not in function_source
    assert "current_export_request" not in function_source


def test_report_export_builds_data_revision_in_request_scope() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    request_position = source.index("current_export_request = ExportRequest(")
    revision_position = source.index("current_data_revision = build_export_data_revision(", request_position)
    prepare_position = source.index("if prepare_export:", request_position)

    assert request_position < revision_position < prepare_position
