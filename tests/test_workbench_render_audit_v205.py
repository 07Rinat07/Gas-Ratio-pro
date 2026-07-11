from __future__ import annotations

from pathlib import Path

from core.workbench_runtime_diagnostics import (
    DIAGNOSTIC_RENDER_AUDIT_KEY,
    diagnostics_snapshot,
    record_render_audit,
)


def test_render_audit_is_compact_serializable_and_visible_in_snapshot() -> None:
    state: dict[str, object] = {}
    record = record_render_audit(
        state,
        route_id="nav.las_workspace",
        renderer="render_las",
        provider="las-workflows",
        phase="completed",
        success=True,
        duration_ms=12.345,
        expected_controls=("file-uploader", "las-editor"),
        details={"project_id": "default"},
    )
    assert record["duration_ms"] == 12.35
    assert state[DIAGNOSTIC_RENDER_AUDIT_KEY]["success"] is True
    snapshot = diagnostics_snapshot(state)
    assert snapshot["render_audit"]["provider"] == "las-workflows"
    assert snapshot["render_audit"]["expected_controls"] == ("file-uploader", "las-editor")


def test_deprecated_streamlit_component_html_is_forbidden() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "import streamlit.components.v1" not in source
    assert "components.html(" not in source


def test_route_renderer_records_start_completed_and_failed_phases() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert 'phase="start"' in source
    assert 'phase="completed"' in source
    assert 'phase="failed"' in source
    assert "WORKBENCH_ROUTE_EXPECTED_CONTROLS" in source
