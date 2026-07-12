from __future__ import annotations

import plotly.graph_objects as go

from palettes.plot_engine import (
    DEPTH_AXIS_TITLE,
    LEGEND_HORIZONTAL,
    THEME,
    apply_depth_axis,
    apply_engineering_layout,
    engineering_hover,
    prepare_figure_for_export,
)


def test_common_layout_applies_engineering_theme_and_legend():
    fig = go.Figure(go.Scatter(x=[1, 2], y=[10, 20]))
    apply_engineering_layout(fig, title="Проверка", height=600)
    assert fig.layout.template is not None
    assert fig.layout.font.family == THEME.font_family
    assert fig.layout.height == 600
    assert fig.layout.legend.orientation == LEGEND_HORIZONTAL["orientation"]


def test_depth_axis_is_reversed_and_uses_metric_unit():
    fig = go.Figure()
    apply_depth_axis(fig, 100.0, 250.0)
    assert tuple(fig.layout.yaxis.range) == (250.0, 100.0)
    assert fig.layout.yaxis.title.text == DEPTH_AXIS_TITLE
    assert fig.layout.yaxis.autorange is False


def test_hover_contract_contains_value_and_depth_without_internal_terms():
    hover = engineering_hover("C1")
    assert "C1" in hover
    assert "Глубина, м" in hover
    assert "renderer" not in hover.lower()
    assert "auto" not in hover.lower()


def test_export_copy_preserves_theme_and_does_not_mutate_screen_figure():
    original = go.Figure(go.Scatter(x=[1], y=[2]))
    exported = prepare_figure_for_export(original, width=1600, height=1000)
    assert exported is not original
    assert exported.layout.width == 1600
    assert exported.layout.height == 1000
    assert exported.layout.font.family == THEME.font_family
    assert original.layout.width is None
