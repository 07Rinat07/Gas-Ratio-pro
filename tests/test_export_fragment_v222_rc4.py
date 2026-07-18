from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
REQUIREMENTS = (ROOT / "requirements.txt").read_text(encoding="utf-8")


def test_professional_export_panel_is_a_streamlit_fragment(monkeypatch) -> None:
    from app import streamlit_app as app
    from core.ui_behavior_contracts import PROFESSIONAL_EXPORT_BEHAVIOR

    assert getattr(app._render_professional_export_panel, "_gas_ratio_fragment_run_every", None) == PROFESSIONAL_EXPORT_BEHAVIOR.fragment_run_every

    calls = []

    class FakeStreamlit:
        def fragment(self, *, run_every=None):
            calls.append(run_every)
            def decorate(target):
                def wrapped(*args, **kwargs):
                    return target(*args, **kwargs)
                return wrapped
            return decorate

    monkeypatch.setattr(app, "st", FakeStreamlit())

    @app._streamlit_fragment(run_every="5s")
    def sample(value):
        return value + 1

    assert sample(4) == 5
    assert calls == ["5s"]
    assert getattr(sample, "_gas_ratio_fragment_run_every", None) == "5s"


def test_interpretation_workspace_calls_isolated_export_panel() -> None:
    from core.ui_behavior_contracts import PROFESSIONAL_EXPORT_BEHAVIOR

    assert PROFESSIONAL_EXPORT_BEHAVIOR.isolated_fragment is True
    assert PROFESSIONAL_EXPORT_BEHAVIOR.render_before_plots is True
    assert PROFESSIONAL_EXPORT_BEHAVIOR.heavy_plot_rendering_inside_panel is False


def test_fragment_keeps_expensive_rendering_outside_its_body() -> None:
    start = APP.index("def _render_professional_export_panel(")
    end = APP.index("def _render_interpretation_graphs_tab(", start)
    fragment_body = APP[start:end]
    assert "st.plotly_chart(" not in fragment_body
    assert "build_depth_gas_tracks(" not in fragment_body
    assert "build_well_log_tablet(" not in fragment_body
    assert ".presentation_export(" in fragment_body
    assert ".pdf_preview(" in fragment_body
    assert ".background_export(" in fragment_body


def test_streamlit_version_supports_fragments() -> None:
    assert "streamlit>=1.37.0" in REQUIREMENTS
