from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from palettes.config import DEFAULT_PIXLER_ZONES, PixlerZone


PIXLER_RATIOS: tuple[tuple[str, str], ...] = (
    ("c1_c2", "C1/C2"),
    ("c1_c3", "C1/C3"),
    ("c1_c4", "C1/ΣC4"),
    ("c1_c5", "C1/ΣC5"),
)


def _positive_or_none(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def build_pixler_palette(row: pd.Series | dict, zones: tuple[PixlerZone, ...] = DEFAULT_PIXLER_ZONES):
    labels = [label for _, label in PIXLER_RATIOS]
    values = [_positive_or_none(row.get(column)) for column, _ in PIXLER_RATIOS]

    fig = go.Figure()

    for zone in zones:
        fig.add_shape(
            type="rect",
            xref="paper",
            yref="y",
            x0=0,
            x1=1,
            y0=zone.y_min,
            y1=zone.y_max,
            fillcolor=zone.color,
            line_width=0,
            layer="below",
        )
        fig.add_annotation(
            x=0.02,
            xref="paper",
            y=math.sqrt(zone.y_min * zone.y_max),
            text=zone.name,
            showarrow=False,
            font={"size": 16},
            align="left",
        )

    fig.add_trace(
        go.Scatter(
            x=labels,
            y=values,
            mode="lines+markers+text",
            line={"color": "#d62728", "width": 3},
            marker={"size": 9, "color": "#d62728"},
            text=[f"{value:.2f}" if value is not None else "NaN" for value in values],
            textposition="top center",
            name="Выбранный интервал",
        )
    )

    fig.update_layout(
        title="Pixler palette",
        margin={"l": 55, "r": 20, "t": 55, "b": 45},
        showlegend=False,
        height=430,
    )
    fig.update_yaxes(
        title="Gas ratio",
        type="log",
        gridcolor="rgba(120,120,120,0.20)",
        zeroline=False,
    )
    fig.update_xaxes(title="", tickfont={"size": 13})

    if all(value is None for value in values):
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Нет положительных Pixler ratios для логарифмической шкалы",
            showarrow=False,
        )

    return fig
