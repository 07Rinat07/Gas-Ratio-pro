from pathlib import Path


def test_streamlit_ui_does_not_construct_correlation_runtime_cache() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "CorrelationRuntimeCache(" not in source
    assert 'ensure_runtime_service(\n        "correlation_runtime_cache"' not in source
    assert 'get_runtime_service("correlation_runtime_cache")' not in source
    assert ".correlation_presentation(" in source
