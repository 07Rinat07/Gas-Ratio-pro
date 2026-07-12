from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from palettes.plot_engine import (
    THEME,
    apply_engineering_layout,
    downsample_frame_for_screen,
    prepare_figure_for_export,
)


def test_screen_theme_is_dark_and_contrasting() -> None:
    fig = go.Figure(go.Scatter(x=[1, 2], y=[100, 200]))
    apply_engineering_layout(fig, title="Контроль")

    assert THEME.template == "plotly_dark"
    assert fig.layout.paper_bgcolor == "#0b1220"
    assert fig.layout.plot_bgcolor == "#0b1220"
    assert fig.layout.font.color == "#e5edf8"
    assert fig.layout.xaxis.color == "#cbd5e1"
    assert fig.layout.yaxis.color == "#cbd5e1"


def test_export_copy_stays_light_and_does_not_mutate_screen_figure() -> None:
    fig = go.Figure(go.Scatter(x=[1, 2], y=[100, 200]))
    apply_engineering_layout(fig)

    exported = prepare_figure_for_export(fig, width=1200, height=800)

    assert exported.layout.paper_bgcolor == "#ffffff"
    assert exported.layout.plot_bgcolor == "#ffffff"
    assert exported.layout.font.color == "#172033"
    assert fig.layout.paper_bgcolor == "#0b1220"
    assert fig.layout.font.color == "#e5edf8"


def test_large_screen_frame_is_deterministically_reduced_without_changing_source() -> None:
    source = pd.DataFrame({"depth": range(10_000), "c1": range(10_000)})

    sampled = downsample_frame_for_screen(source, max_rows=2200)

    assert len(source) == 10_000
    assert len(sampled) <= 2202
    assert sampled.iloc[0]["depth"] == 0
    assert sampled.iloc[-1]["depth"] == 9999
    assert sampled.equals(downsample_frame_for_screen(source, max_rows=2200))
