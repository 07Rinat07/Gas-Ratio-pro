from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.hydrocarbon_intervals import HydrocarbonInterval, MARKER_STYLE_BY_FLUID


DEFAULT_TRACK_COLUMNS: tuple[str, ...] = (
    "c1",
    "c2",
    "c3",
    "wh",
    "bh",
    "ch",
    "c1_c2",
    "c1_c3",
    "inverse_oil_indicator",
)

FLUID_PLOT_LABELS: Mapping[str, str] = {
    "gas": "GAS",
    "oil": "OIL",
    "condensate": "COND",
    "gas_oil": "GAS-OIL",
    "oil_gas": "OIL-GAS",
    "mixed": "MIXED",
    "transition": "CHECK",
    "water": "WATER",
    "uncertain": "UNCERTAIN",
}


@dataclass(frozen=True)
class WellLogPlotConfig:
    """Configuration for the professional printable well-log tablet.

    The renderer is report-oriented: it keeps the common depth axis, reduces
    excessive point count before plotting and overlays interpreted intervals as
    explicit engineering zones. It intentionally does not run interpretation
    logic; intervals must come from the frozen Hydrocarbon Interpretation Engine.
    """

    depth_column: str = "depth"
    track_columns: tuple[str, ...] = DEFAULT_TRACK_COLUMNS
    max_points_per_track: int = 2500
    height: int = 850
    title: str = "Professional well-log interpretation tablet"
    show_interval_track: bool = True


@dataclass(frozen=True)
class DownsampleSummary:
    original_points: int
    plotted_points: int
    method: str


@dataclass(frozen=True)
class WellLogPlotResult:
    figure: go.Figure
    plotted_columns: tuple[str, ...]
    downsample: DownsampleSummary
    interval_count: int


def _numeric_depth_frame(df: pd.DataFrame, depth_column: str) -> pd.DataFrame:
    if df is None or df.empty or depth_column not in df.columns:
        return pd.DataFrame()
    frame = df.copy()
    frame[depth_column] = pd.to_numeric(frame[depth_column], errors="coerce")
    frame = frame.dropna(subset=[depth_column])
    if frame.empty:
        return frame
    return frame.sort_values(depth_column).reset_index(drop=True)


def _available_track_columns(df: pd.DataFrame, requested: Sequence[str], depth_column: str) -> tuple[str, ...]:
    columns: list[str] = []
    for column in requested:
        column_name = str(column)
        if column_name == depth_column or column_name not in df.columns:
            continue
        values = pd.to_numeric(df[column_name], errors="coerce")
        if values.notna().any():
            columns.append(column_name)
    return tuple(columns)


def downsample_depth_frame(
    df: pd.DataFrame,
    *,
    depth_column: str = "depth",
    track_columns: Sequence[str] = (),
    max_points: int = 2500,
) -> tuple[pd.DataFrame, DownsampleSummary]:
    """Return a depth-sorted frame with bounded point count for readable plots.

    Large LAS files can contain tens or hundreds of thousands of rows. Plotting
    every row makes browser-based reports look like vertical fences and slows
    printing. This function uses deterministic stride downsampling and always
    keeps the last row, which preserves the displayed depth interval boundaries
    without adding random or non-reproducible behavior.
    """

    frame = _numeric_depth_frame(df, depth_column)
    original_points = len(frame)
    if frame.empty:
        return frame, DownsampleSummary(original_points=0, plotted_points=0, method="empty")

    safe_max_points = max(2, int(max_points or 2500))
    if original_points <= safe_max_points:
        return frame, DownsampleSummary(original_points=original_points, plotted_points=original_points, method="none")

    stride = max(1, original_points // safe_max_points)
    sampled = frame.iloc[::stride].copy()
    last_index = frame.index[-1]
    if sampled.index[-1] != last_index:
        sampled = pd.concat([sampled, frame.iloc[[-1]]], ignore_index=False)
    sampled = sampled.drop_duplicates(subset=[depth_column], keep="last").reset_index(drop=True)
    return sampled, DownsampleSummary(original_points=original_points, plotted_points=len(sampled), method=f"stride:{stride}")


def _interval_label(interval: HydrocarbonInterval, index: int) -> str:
    fluid = FLUID_PLOT_LABELS.get(interval.fluid_type, str(interval.fluid_type or "HC").upper())
    confidence = f"{interval.confidence_score}%" if interval.confidence_score else str(interval.confidence or "")
    return f"HC-{index:03d}<br>{fluid}<br>{confidence}"


def _interval_style(fluid_type: str) -> Mapping[str, str]:
    return MARKER_STYLE_BY_FLUID.get(fluid_type, {"color": "#7f7f7f", "fill": "rgba(127,127,127,0.14)", "label": "HC"})


def _curve_range(values: pd.Series) -> tuple[float, float] | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    low = float(numeric.quantile(0.02))
    high = float(numeric.quantile(0.98))
    if low == high:
        low = float(numeric.min())
        high = float(numeric.max())
    if low == high:
        pad = abs(low) * 0.05 or 1.0
        return low - pad, high + pad
    pad = (high - low) * 0.05
    return low - pad, high + pad


def build_professional_well_log_plot(
    df: pd.DataFrame,
    intervals: Sequence[HydrocarbonInterval] = (),
    *,
    config: WellLogPlotConfig | None = None,
) -> WellLogPlotResult:
    """Build the first professional report tablet for interpreted intervals.

    The plot is designed for reports: one common reversed depth axis, one
    optional interval column, bounded curve point count, interval background
    zones across all tracks and readable labels inside the interval track.
    """

    cfg = config or WellLogPlotConfig()
    prepared = _numeric_depth_frame(df, cfg.depth_column)
    if prepared.empty:
        fig = go.Figure()
        fig.update_layout(title=cfg.title, height=cfg.height, annotations=[{"text": "Нет данных глубины для планшета", "showarrow": False}])
        return WellLogPlotResult(fig, (), DownsampleSummary(0, 0, "empty"), len(intervals))

    plotted_columns = _available_track_columns(prepared, cfg.track_columns, cfg.depth_column)
    sampled, summary = downsample_depth_frame(
        prepared,
        depth_column=cfg.depth_column,
        track_columns=plotted_columns,
        max_points=cfg.max_points_per_track,
    )

    column_titles = (["Интервалы"] if cfg.show_interval_track else []) + list(plotted_columns)
    if not column_titles:
        fig = go.Figure()
        fig.update_layout(title=cfg.title, height=cfg.height, annotations=[{"text": "Нет числовых треков для планшета", "showarrow": False}])
        return WellLogPlotResult(fig, plotted_columns, summary, len(intervals))

    widths = ([0.18] if cfg.show_interval_track else []) + [1.0] * len(plotted_columns)
    fig = make_subplots(
        rows=1,
        cols=len(column_titles),
        shared_yaxes=True,
        horizontal_spacing=0.018,
        column_widths=widths,
        subplot_titles=column_titles,
    )

    depth = sampled[cfg.depth_column]
    first_curve_col = 2 if cfg.show_interval_track else 1

    if cfg.show_interval_track:
        fig.add_trace(
            go.Scatter(
                x=[0] * len(depth),
                y=depth,
                mode="lines",
                line={"color": "rgba(0,0,0,0)", "width": 0},
                hoverinfo="skip",
                showlegend=False,
            ),
            row=1,
            col=1,
        )
        fig.update_xaxes(visible=False, range=[0, 1], row=1, col=1)

    for offset, column in enumerate(plotted_columns, start=0):
        col_index = first_curve_col + offset
        values = pd.to_numeric(sampled[column], errors="coerce")
        fig.add_trace(
            go.Scatter(
                x=values,
                y=depth,
                mode="lines",
                name=column,
                line={"width": 1.35},
                connectgaps=False,
                hovertemplate=f"{column}: %{{x}}<br>Depth: %{{y}}<extra></extra>",
                showlegend=False,
            ),
            row=1,
            col=col_index,
        )
        curve_range = _curve_range(values)
        fig.update_xaxes(title_text=column, zeroline=False, showgrid=True, row=1, col=col_index)
        if curve_range is not None:
            fig.update_xaxes(range=list(curve_range), row=1, col=col_index)

    top_depth = float(prepared[cfg.depth_column].min())
    bottom_depth = float(prepared[cfg.depth_column].max())
    fig.update_yaxes(title_text="Depth, m", autorange=False, range=[bottom_depth, top_depth], showgrid=True)

    shapes: list[dict[str, object]] = []
    annotations = list(fig.layout.annotations or ())
    for index, interval in enumerate(intervals, start=1):
        interval_top = min(float(interval.top), float(interval.base))
        interval_base = max(float(interval.top), float(interval.base))
        style = _interval_style(interval.fluid_type)
        fill = str(style.get("fill", "rgba(127,127,127,0.14)"))
        color = str(style.get("color", "#7f7f7f"))
        shapes.append(
            {
                "type": "rect",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": interval_top,
                "y1": interval_base,
                "fillcolor": fill,
                "line": {"color": color, "width": 0.8},
                "layer": "below",
            }
        )
        if cfg.show_interval_track:
            annotations.append(
                {
                    "xref": "x",
                    "yref": "y",
                    "x": 0.5,
                    "y": (interval_top + interval_base) / 2,
                    "text": _interval_label(interval, index),
                    "showarrow": False,
                    "font": {"size": 11, "color": "#172033"},
                    "bgcolor": "rgba(255,255,255,0.82)",
                    "bordercolor": color,
                    "borderwidth": 1,
                }
            )

    fig.update_layout(
        title=cfg.title,
        height=cfg.height,
        margin={"l": 70, "r": 40, "t": 90, "b": 45},
        template="plotly_white",
        shapes=shapes,
        annotations=annotations,
        showlegend=False,
    )
    return WellLogPlotResult(fig, plotted_columns, summary, len(intervals))
