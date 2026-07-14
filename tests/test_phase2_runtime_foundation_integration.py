from pathlib import Path


def test_empty_calculation_no_longer_emits_normal_state_warning() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert '"active_calculation_missing project_id=%s contract_type=%s"' not in source
    assert '"active_calculation_contract_invalid project_id=%s contract_keys=%s"' in source


def test_correlation_pipeline_has_stage_level_diagnostics() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    for stage in (
        "correlation.cache_lookup",
        "correlation.panel",
        "correlation.studio_figure",
        "correlation.main_figure",
        "correlation.cache_store",
        "correlation.frontend_dispatch",
        "correlation.total",
    ):
        assert stage in source
    assert "las_correlation_performance" in source
