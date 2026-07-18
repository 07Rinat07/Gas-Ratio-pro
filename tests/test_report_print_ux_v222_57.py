from pathlib import Path

from reports.plot_theme import apply_report_plot_theme
from reports.print_readability_contract import REPORT_PRINT_READABILITY
from tests.visual_rebaseline_helpers import assert_visual_rebaseline


class FakeFigure:
    def __init__(self):
        self.layouts = []
        self.traces = []

    def __deepcopy__(self, memo):
        return self

    def update_layout(self, **kwargs):
        self.layouts.append(kwargs)

    def update_traces(self, **kwargs):
        self.traces.append(kwargs)


def test_report_plot_theme_enforces_print_readability():
    figure = FakeFigure()
    themed = apply_report_plot_theme(figure)
    assert themed is figure
    primary = figure.layouts[0]
    axes = figure.layouts[1]
    assert_visual_rebaseline(
        "tests/test_report_print_ux_v222_57.py::test_report_plot_theme_enforces_print_readability",
        {
            "base_font_pt": int(primary["font"]["size"]),
            "title_font_pt": int(primary["title"]["font"]["size"]),
            "legend_font_pt": int(primary["legend"]["font"]["size"]),
            "axis_tick_font_pt": int(axes["xaxis"]["tickfont"]["size"]),
            "axis_title_font_pt": int(axes["xaxis"]["title"]["font"]["size"]),
            "scatter_line_width": float(figure.traces[0]["line"]["width"]),
            "marker_size": int(figure.traces[1]["marker"]["size"]),
            "legend_visible": bool(primary["showlegend"]),
            "legend_y": float(primary["legend"]["y"]),
        },
    )

def test_report_panel_is_compact_and_action_oriented():
    from app import streamlit_app as app
    from core.ui_behavior_contracts import PROFESSIONAL_EXPORT_BEHAVIOR

    calls = []

    class FallbackStreamlit:
        def markdown(self, *_args, **_kwargs):
            return None
        def expander(self, label, *, expanded=False):
            calls.append((label, expanded))
            return object()

    assert app._print_center_container(FallbackStreamlit()) is not None
    assert calls == [(PROFESSIONAL_EXPORT_BEHAVIOR.panel_label, False)]
    assert PROFESSIONAL_EXPORT_BEHAVIOR.primary_action_label
    assert PROFESSIONAL_EXPORT_BEHAVIOR.download_prefix


def test_print_legends_are_not_micro_text():
    assert REPORT_PRINT_READABILITY.valid
    assert_visual_rebaseline(
        "tests/test_report_print_ux_v222_57.py::test_print_legends_are_not_micro_text",
        REPORT_PRINT_READABILITY.to_dict(),
    )

def test_developer_diagnostics_are_collapsed_by_default():
    source = Path("app/workbench_renderer.py").read_text(encoding="utf-8")
    assert 'i18n("diagnostics.show_advanced")' in source
    assert 'value=False' in source
    assert "if show_advanced:" in source
