from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
REQUIREMENTS = (ROOT / "requirements.txt").read_text(encoding="utf-8")


def test_professional_export_panel_is_a_streamlit_fragment() -> None:
    assert '@_streamlit_fragment(run_every="2s")\ndef _render_professional_export_panel(' in APP
    assert 'fragment = getattr(st, "fragment", None)' in APP
    assert 'fragment_decorator = fragment(run_every=run_every)' in APP
    assert 'decorated = fragment_decorator(target)' in APP


def test_interpretation_workspace_calls_isolated_export_panel() -> None:
    assert "_render_professional_export_panel(" in APP
    assert 'with st.expander("🖨️ ПЕЧАТЬ И ПРОФЕССИОНАЛЬНЫЙ ЭКСПОРТ"' in APP
    route_start = APP.index("def _render_interpretation_graphs_tab")
    helper_call = APP.index("_render_professional_export_panel(", route_start)
    chart_loop = APP.index("for figure_index, figure in enumerate(figures):", helper_call)
    assert helper_call < chart_loop


def test_fragment_keeps_expensive_rendering_outside_its_body() -> None:
    start = APP.index("def _render_professional_export_panel(")
    end = APP.index("def _render_interpretation_graphs_tab(", start)
    fragment_body = APP[start:end]
    assert "st.plotly_chart(" not in fragment_body
    assert "build_depth_gas_tracks(" not in fragment_body
    assert "build_well_log_tablet(" not in fragment_body
    assert "ExportController(" in fragment_body


def test_streamlit_version_supports_fragments() -> None:
    assert "streamlit>=1.37.0" in REQUIREMENTS
