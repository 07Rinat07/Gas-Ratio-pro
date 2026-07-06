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

def build_las_curve_comparison_figure(
    wells: Iterable[LasCorrelationWell],
    curve_name: str,
    *,
    depth_range: tuple[float, float] | None = None,
    x_range: tuple[float, float] | None = None,
    height: int = 650,
) -> go.Figure:
    fig = go.Figure()
    selected_curve = str(curve_name)

    for well in wells:
        if well.data.empty or selected_curve not in well.data.columns or well.depth_column not in well.data.columns:
            continue

        depth = _numeric_curve(well.data, well.depth_column)
        values = _numeric_curve(well.data, selected_curve)
        mask = depth.notna() & values.notna()
        if depth_range is not None:
            top_depth, bottom_depth = sorted((float(depth_range[0]), float(depth_range[1])))
            mask &= depth.between(top_depth, bottom_depth, inclusive="both")
        if not mask.any():
            continue

        fig.add_trace(
            go.Scatter(
                x=values.loc[mask],
                y=depth.loc[mask],
                mode="lines",
                name=well.name,
                hovertemplate=f"{well.name}<br>{selected_curve}=%{{x}}<br>Depth=%{{y}}<extra></extra>",
            )
        )

    yaxis_options = {"title": "Depth", "autorange": "reversed"}
    if depth_range is not None:
        top_depth, bottom_depth = sorted((float(depth_range[0]), float(depth_range[1])))
        yaxis_options["range"] = [bottom_depth, top_depth]
        yaxis_options["autorange"] = False
    xaxis_options = {"title": selected_curve, "zeroline": False}
    if x_range is not None:
        xaxis_options["range"] = list(x_range)

    fig.update_yaxes(**yaxis_options)
    fig.update_xaxes(**xaxis_options)
    if not fig.data:
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text=f"Нет числовых данных для кривой {selected_curve}",
            showarrow=False,
        )
    fig.update_layout(
        title=f"Сравнение кривой {selected_curve} между скважинами",
        height=max(480, int(height)),
        margin={"l": 70, "r": 30, "t": 80, "b": 60},
        legend={"orientation": "h", "y": -0.12},
    )
    return fig


def _marker_applies_to_well(marker, well_name: str) -> bool:
    return not marker.well or marker.well == well_name or marker.well == "Все скважины"


def build_correlation_panel_figure(
    panel,
    curve_name: str | None = None,
    *,
    height_per_well: int = 360,
) -> go.Figure:
    """Build a professional multi-well correlation panel with shared depth and markers."""
    selected_wells = [well for well in panel.wells if well.row_count > 0]
    if not selected_wells:
        fig = go.Figure()
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Нет скважин для Correlation Studio",
            showarrow=False,
        )
        return fig

    selected_curve = curve_name or (panel.common_curves[0] if panel.common_curves else "")
    subplot_titles = tuple(well.name for well in selected_wells)
    fig = make_subplots(
        rows=1,
        cols=len(selected_wells),
        shared_yaxes=True,
        horizontal_spacing=0.035,
        subplot_titles=subplot_titles,
    )

    for col_index, well in enumerate(selected_wells, start=1):
        depth = _numeric_curve(well.data, well.depth_column)
        xaxis_title = selected_curve or "Curve"
        if selected_curve and selected_curve in well.data.columns:
            values = _numeric_curve(well.data, selected_curve)
            mask = depth.notna() & values.notna()
            if panel.depth_range is not None:
                top, bottom = sorted((float(panel.depth_range[0]), float(panel.depth_range[1])))
                mask &= depth.between(top, bottom, inclusive="both")
            if mask.any():
                fig.add_trace(
                    go.Scatter(
                        x=values.loc[mask],
                        y=depth.loc[mask],
                        mode="lines",
                        name=f"{well.name}: {selected_curve}",
                        legendgroup=selected_curve,
                        hovertemplate=f"{well.name}<br>{selected_curve}=%{{x}}<br>Depth=%{{y}}<extra></extra>",
                    ),
                    row=1,
                    col=col_index,
                )
        else:
            fig.add_annotation(
                x=0.5,
                y=0.5,
                xref=f"x{col_index if col_index > 1 else ''} domain",
                yref=f"y{col_index if col_index > 1 else ''} domain",
                text="Кривая отсутствует",
                showarrow=False,
            )

        for marker in panel.markers:
            if not _marker_applies_to_well(marker, well.name):
                continue
            fig.add_hline(
                y=marker.depth,
                line_dash="dot",
                line_width=1,
                line_color=marker.color,
                annotation_text=marker.name,
                annotation_position="top left",
                row=1,
                col=col_index,
            )

        yaxis_options = {"title": "Depth", "autorange": "reversed"}
        if panel.depth_range is not None:
            top, bottom = sorted((float(panel.depth_range[0]), float(panel.depth_range[1])))
            yaxis_options["range"] = [bottom, top]
            yaxis_options["autorange"] = False
        fig.update_yaxes(**yaxis_options, row=1, col=col_index)
        fig.update_xaxes(title=xaxis_title, zeroline=False, row=1, col=col_index)

    fig.update_layout(
        title=f"Correlation Studio · {selected_curve or 'без выбранной кривой'}",
        height=max(480, int(height_per_well)),
        margin={"l": 70, "r": 30, "t": 80, "b": 70},
        legend={"orientation": "h", "y": -0.18},
    )
    return fig
