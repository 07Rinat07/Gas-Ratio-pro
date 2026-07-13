from __future__ import annotations

import plotly.graph_objects as go
import pytest

from palettes.plot_engine import (
    CHART_THEME_PROFILES,
    apply_chart_theme,
    chart_theme_signature,
    get_chart_theme,
    prepare_figure_for_export,
)


def test_theme_registry_contains_screen_print_and_presentation_profiles():
    assert set(CHART_THEME_PROFILES) == {"screen", "print", "presentation"}
    assert get_chart_theme("screen").paper_color != get_chart_theme("print").paper_color
    assert get_chart_theme("presentation").font_size > get_chart_theme("print").font_size


def test_unknown_theme_profile_is_rejected():
    with pytest.raises(ValueError, match="Unknown chart theme profile"):
        get_chart_theme("unknown")


def test_apply_chart_theme_preserves_data_and_axis_range():
    fig = go.Figure(go.Scatter(x=[1, 2], y=[100, 200], mode="lines+markers"))
    fig.update_yaxes(range=[250, 50])

    apply_chart_theme(fig, profile="presentation", width=1400, height=900)

    assert list(fig.data[0].x) == [1, 2]
    assert tuple(fig.layout.yaxis.range) == (250, 50)
    assert fig.layout.width == 1400
    assert fig.layout.height == 900
    assert fig.layout.font.size == get_chart_theme("presentation").font_size
    assert fig.data[0].line.width >= get_chart_theme("presentation").line_width


def test_export_profile_does_not_mutate_screen_figure():
    source = go.Figure(go.Scatter(x=[1], y=[2]))
    exported = prepare_figure_for_export(source, width=1200, height=800, profile="print")

    assert exported is not source
    assert exported.layout.paper_bgcolor == "#ffffff"
    assert source.layout.paper_bgcolor is None


def test_theme_signature_is_stable_and_profile_specific():
    assert chart_theme_signature("screen") == chart_theme_signature("screen")
    assert chart_theme_signature("screen") != chart_theme_signature("print")
