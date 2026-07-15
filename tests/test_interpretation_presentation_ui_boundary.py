from pathlib import Path


def test_streamlit_ui_does_not_construct_interpretation_runtime_caches() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "DataframeRuntimeCache(" not in source
    assert "PlotCache(" not in source
    assert 'ensure_runtime_service(\n        "dataframe_runtime_cache"' not in source
    assert 'ensure_runtime_service(\n        "interpretation_plot_cache"' not in source
    assert ".interpretation_presentation(" in source
