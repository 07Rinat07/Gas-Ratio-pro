from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from palettes.config import TernaryRegion


TERNARY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("c2_sumc", "C2/ΣC"),
    ("c3_sumc", "C3/ΣC"),
    ("nc4_sumc", "nC4/ΣC"),
)


def _finite_or_none(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _ternary_values(row: pd.Series | dict) -> list[float | None]:
    values = [_finite_or_none(row.get(column)) for column, _ in TERNARY_COLUMNS]
    if any(value is None for value in values):
        return values
    if sum(value for value in values if value is not None) <= 0:
        return [None, None, None]
    return values


def _add_regions(fig: go.Figure, regions: tuple[TernaryRegion, ...]) -> None:
    for region in regions:
        fig.add_trace(
            go.Scatterternary(
                a=list(region.a) + [region.a[0]],
                b=list(region.b) + [region.b[0]],
                c=list(region.c) + [region.c[0]],
                mode="lines",
                fill="toself",
                fillcolor=region.color,
                line={"color": "rgba(80, 80, 80, 0.25)", "width": 1},
                name=region.name,
                hoverinfo="name",
            )
        )


def build_ternary_palette(row: pd.Series | dict, regions: tuple[TernaryRegion, ...] = ()):
    values = _ternary_values(row)

    fig = go.Figure()
    _add_regions(fig, regions)

    if any(value is None for value in values):
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Недостаточно данных для ternary palette",
            showarrow=False,
        )
    else:
        fig.add_trace(
            go.Scatterternary(
                a=[values[0]],
                b=[values[1]],
                c=[values[2]],
                mode="markers+text",
                marker={"size": 13, "color": "#d62728"},
                text=["Выбранный интервал"],
                textposition="top center",
                name="Интервал",
            )
        )

    fig.update_layout(
        title="Ternary palette",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        ternary={
            "sum": 1,
            "aaxis": {"title": "C2/ΣC", "min": 0.0},
            "baxis": {"title": "C3/ΣC", "min": 0.0},
            "caxis": {"title": "nC4/ΣC", "min": 0.0},
        },
        showlegend=bool(regions),
        legend={"orientation": "h", "y": -0.15},
    )
    return fig