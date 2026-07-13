from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
REQUIREMENTS = (ROOT / "requirements.txt").read_text(encoding="utf-8")


def test_professional_export_panel_is_a_streamlit_fragment() -> None:
    assert "@_streamlit_fragment\ndef _render_professional_export_panel(" in APP
    assert 'fragment = getattr(st, "fragment", None)' in APP


def test_interpretation_workspace_calls_isolated_export_panel() -> None:
    assert "_render_professional_export_panel(" in APP
    assert 'with st.expander("Профессиональный экспорт отчета"' in APP
    # The heavy panel must no longer be nested directly below the chart loop.
    chart_loop = APP.index("for figure in figures:")
    helper_call = APP.index("_render_professional_export_panel(", chart_loop)
    summary = APP.index('st.subheader("Инженерная сводка УВ-интервалов")', helper_call)
    assert chart_loop < helper_call < summary


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
