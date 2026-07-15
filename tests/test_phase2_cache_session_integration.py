from pathlib import Path


def test_cache_metrics_are_registered_behind_application_boundary() -> None:
    ui_source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    diagnostics_source = Path(
        "services/runtime_diagnostics_application_service.py"
    ).read_text(encoding="utf-8")
    presentation_source = Path(
        "services/interpretation_presentation_application_service.py"
    ).read_text(encoding="utf-8")

    assert '"cache_metrics_registry"' not in ui_source
    assert '"cache_metrics_registry"' in diagnostics_source
    assert '"dataframe_runtime"' in presentation_source
    assert "self._dataframe_max_samples" in presentation_source
    assert "runtime_state_diagnostics" in ui_source
    assert "audit_session_state(correlation_state_controller.state)" in ui_source
