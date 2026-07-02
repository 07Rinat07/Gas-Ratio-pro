from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from las_correlation.core import DEFAULT_GAS_GROUPS, DEFAULT_GIS_GROUPS, LasCorrelationWell


def _columns_for_groups(well: LasCorrelationWell, groups: Iterable[str]) -> tuple[str, ...]:
    columns: list[str] = []
    for group in groups:
        columns.extend(well.curve_groups.get(group, ()))
    return tuple(dict.fromkeys(columns))


def _numeric_curve(data: pd.DataFrame, column: str) -> pd.Series:
    if column not in data.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(data[column], errors="coerce")


def _add_curve_traces(
    fig: go.Figure,
    well: LasCorrelationWell,
    columns: Iterable[str],
    *,
    row: int,
    col: int,
    group_title: str,
) -> None:
    depth = _numeric_curve(well.data, well.depth_column)
    for column in columns:
        values = _numeric_curve(well.data, column)
        if values.empty or values.isna().all():
            continue
        fig.add_trace(
            go.Scatter(
                x=values,
                y=depth,
                mode="lines",
                name=f"{well.name}: {column}",
                legendgroup=f"{group_title}:{column}",
                hovertemplate=f"{well.name}<br>{column}=%{{x}}<br>Depth=%{{y}}<extra></extra>",
            ),
            row=row,
            col=col,
        )


def build_las_correlation_figure(
    wells: Iterable[LasCorrelationWell],
    *,
    gis_groups: Iterable[str] = DEFAULT_GIS_GROUPS,
    gas_groups: Iterable[str] = DEFAULT_GAS_GROUPS,
    depth_range: tuple[float, float] | None = None,
    gis_x_range: tuple[float, float] | None = None,
    gas_x_range: tuple[float, float] | None = None,
    height_per_well: int = 430,
) -> go.Figure:
    selected_wells = [well for well in wells if well.row_count > 0]
    if not selected_wells:
        fig = go.Figure()
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Нет LAS-скважин для корреляции",
            showarrow=False,
        )
        return fig

    subplot_titles: list[str] = []
    for well in selected_wells:
        subplot_titles.extend((f"{well.name}: ГИС", f"{well.name}: Газы"))

    fig = make_subplots(
        rows=len(selected_wells),
        cols=2,
        shared_yaxes=True,
        horizontal_spacing=0.06,
        vertical_spacing=0.08,
        subplot_titles=tuple(subplot_titles),
    )

    for row_index, well in enumerate(selected_wells, start=1):
        gis_columns = _columns_for_groups(well, gis_groups)
        gas_columns = _columns_for_groups(well, gas_groups)
        _add_curve_traces(fig, well, gis_columns, row=row_index, col=1, group_title="gis")
        _add_curve_traces(fig, well, gas_columns, row=row_index, col=2, group_title="gas")

        yaxis_options = {"title": "Depth", "autorange": "reversed"}
        if depth_range is not None:
            top_depth, bottom_depth = depth_range
            yaxis_options["range"] = [bottom_depth, top_depth]
            yaxis_options["autorange"] = False
        fig.update_yaxes(**yaxis_options, row=row_index, col=1)
        fig.update_yaxes(**yaxis_options, row=row_index, col=2)
        gis_xaxis_options = {"title": "ГИС", "zeroline": False}
        gas_xaxis_options = {"title": "Газы", "zeroline": False}
        if gis_x_range is not None:
            gis_xaxis_options["range"] = list(gis_x_range)
        if gas_x_range is not None:
            gas_xaxis_options["range"] = list(gas_x_range)
        fig.update_xaxes(**gis_xaxis_options, row=row_index, col=1)
        fig.update_xaxes(**gas_xaxis_options, row=row_index, col=2)

    if not fig.data:
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Выбранные LAS не содержат числовых ГИС/газовых кривых",
            showarrow=False,
        )

    fig.update_layout(
        title="Multi-LAS correlation: ГИС рядом с газами",
        height=max(480, height_per_well * len(selected_wells)),
        margin={"l": 70, "r": 30, "t": 80, "b": 60},
        legend={"orientation": "h", "y": -0.12},
    )
    return fig
