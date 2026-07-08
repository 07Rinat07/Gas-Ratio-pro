from __future__ import annotations

from pathlib import Path


APP_PATH = Path("app/streamlit_app.py")


def _function_source(name: str) -> str:
    source = APP_PATH.read_text(encoding="utf-8")
    start_marker = f"def {name}"
    start = source.index(start_marker)
    next_def = source.find("\ndef ", start + len(start_marker))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


def test_repository_management_panels_use_runtime_refresh_helper() -> None:
    """Repository-backed UI panels should not call ``st.rerun`` directly.

    Sprint 1 introduces ``ApplicationRuntimeController`` as the single refresh
    request path for project/well/LAS/export management actions.  The remaining
    direct reruns in navigation-only widgets are legacy debt, but repository
    mutation panels must go through the central helper so events and diagnostics
    stay consistent.
    """

    for function_name in (
        "_render_saved_wells_panel",
        "_render_las_editor",
        "_render_project_exports_panel",
        "_render_project_las_files_panel",
    ):
        function_source = _function_source(function_name)
        assert "st.rerun()" not in function_source, function_name
        assert "_request_ui_refresh_and_rerun" in function_source, function_name


def test_project_mutation_ui_keeps_refresh_reason_codes() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    expected_reasons = (
        "saved_well_version_deleted",
        "saved_well_deleted",
        "las_editor_working_state_cleared",
        "project_exports_refreshed",
        "project_export_deleted",
        "project_exports_cleared",
        "project_las_files_saved",
        "project_las_file_archived",
        "project_las_file_deleted",
        "project_las_file_restored",
    )
    for reason in expected_reasons:
        assert reason in source
