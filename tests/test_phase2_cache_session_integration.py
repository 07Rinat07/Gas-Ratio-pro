from pathlib import Path


def test_streamlit_runtime_registers_cache_metrics_and_session_audit() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert '"cache_metrics_registry"' in source
    assert 'metrics=cache_metrics_registry.counter("dataframe_runtime", max_entries=8)' in source
    assert "runtime_state_diagnostics" in source
    assert "audit_session_state(correlation_state_controller.state)" in source
