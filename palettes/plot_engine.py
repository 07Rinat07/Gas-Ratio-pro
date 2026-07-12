from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import plotly.graph_objects as go


@dataclass(frozen=True, slots=True)
class EngineeringPlotTheme:
    template: str = "plotly_dark"
    font_family: str = "Arial, sans-serif"
    font_size: int = 12
    title_size: int = 18
    axis_title_size: int = 13
    tick_size: int = 11
    line_width: float = 1.7
    marker_size: int = 8
    grid_color: str = "rgba(148, 163, 184, 0.24)"
    text_color: str = "#e5edf8"
    paper_color: str = "#0b1220"
    plot_color: str = "#0b1220"
    axis_color: str = "#cbd5e1"
    margin_left: int = 72
    margin_right: int = 28
    margin_top: int = 76
    margin_bottom: int = 64


THEME = EngineeringPlotTheme()

ENGINEERING_COLORS: Mapping[str, str] = {
    "primary": "#1f77b4",
    "secondary": "#2a9d8f",
    "accent": "#e76f51",
    "warning": "#f4a261",
    "neutral": "#6c757d",
    "muted": "#94a3b8",
    "gas": "#ff9f1c",
    "condensate": "#e76f51",
    "oil": "#2a9d8f",
    "water": "#457b9d",
    "unknown": "#adb5bd",
}

LEGEND_HORIZONTAL: Mapping[str, Any] = {
    "orientation": "h",
    "y": -0.16,
    "x": 0.0,
    "xanchor": "left",
    "yanchor": "top",
    "font": {"size": THEME.tick_size},
    "bgcolor": "rgba(11,18,32,0.88)",
    "bordercolor": "rgba(148,163,184,0.28)",
    "borderwidth": 1,
}

DEPTH_AXIS_TITLE = "Глубина, м"

AXIS_TITLES: Mapping[str, str] = {
    "depth": DEPTH_AXIS_TITLE,
    "gas": "Содержание газа, усл. ед.",
    "ratio": "Отношение компонентов, доли ед.",
    "pixler": "Отношение компонентов",
    "interpretation": "Интерпретация",
}


def engineering_hover(value_label: str, *, value_format: str = ".4g", depth_label: str = DEPTH_AXIS_TITLE) -> str:
    return f"{value_label}: %{{x:{value_format}}}<br>{depth_label}: %{{y:.2f}}<extra></extra>"


def apply_engineering_layout(
    fig: go.Figure,
    *,
    title: str | Mapping[str, Any] | None = None,
    height: int | None = None,
    showlegend: bool | None = None,
    legend: Mapping[str, Any] | None = None,
    margin: Mapping[str, int] | None = None,
    hovermode: str = "closest",
) -> go.Figure:
    layout: dict[str, Any] = {
        "template": THEME.template,
        "font": {"family": THEME.font_family, "size": THEME.font_size, "color": THEME.text_color},
        "paper_bgcolor": THEME.paper_color,
        "plot_bgcolor": THEME.plot_color,
        "hovermode": hovermode,
        "margin": dict(margin or {
            "l": THEME.margin_left,
            "r": THEME.margin_right,
            "t": THEME.margin_top,
            "b": THEME.margin_bottom,
        }),
    }
    if title is not None:
        layout["title"] = title
    if height is not None:
        layout["height"] = int(height)
    if showlegend is not None:
        layout["showlegend"] = bool(showlegend)
    if legend is not None:
        layout["legend"] = dict(legend)
    elif showlegend is not False:
        layout["legend"] = dict(LEGEND_HORIZONTAL)
    fig.update_layout(**layout)
    fig.update_xaxes(
        title_font={"size": THEME.axis_title_size},
        tickfont={"size": THEME.tick_size},
        gridcolor=THEME.grid_color,
        color=THEME.axis_color,
        linecolor=THEME.axis_color,
        tickcolor=THEME.axis_color,
        zeroline=False,
        automargin=True,
    )
    fig.update_yaxes(
        title_font={"size": THEME.axis_title_size},
        tickfont={"size": THEME.tick_size},
        gridcolor=THEME.grid_color,
        color=THEME.axis_color,
        linecolor=THEME.axis_color,
        tickcolor=THEME.axis_color,
        zeroline=False,
        automargin=True,
    )
    return fig


def apply_depth_axis(
    fig: go.Figure,
    top_depth: float,
    bottom_depth: float,
    *,
    title: str = DEPTH_AXIS_TITLE,
    **kwargs: Any,
) -> go.Figure:
    options: dict[str, Any] = {
        "title": title,
        "range": [float(bottom_depth), float(top_depth)],
        "autorange": False,
        "gridcolor": THEME.grid_color,
        "color": THEME.axis_color,
        "linecolor": THEME.axis_color,
        "tickcolor": THEME.axis_color,
        "zeroline": False,
        "automargin": True,
    }
    options.update(kwargs)
    fig.update_yaxes(**options)
    return fig


def normalize_trace_style(fig: go.Figure) -> go.Figure:
    """Apply common widths and marker sizes without overriding explicit semantics."""
    for trace in fig.data:
        if hasattr(trace, "line") and trace.line is not None and getattr(trace.line, "width", None) is None:
            trace.line.width = THEME.line_width
        if hasattr(trace, "marker") and trace.marker is not None and getattr(trace.marker, "size", None) is None:
            trace.marker.size = THEME.marker_size
    return fig


def prepare_figure_for_export(fig: go.Figure, *, width: int, height: int) -> go.Figure:
    """Return a light, print-safe copy without mutating the dark screen figure."""
    if not isinstance(fig, go.Figure):
        return fig
    exported = go.Figure(fig)
    exported.update_layout(
        template="plotly_white",
        width=max(320, int(width)),
        height=int(height),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"family": THEME.font_family, "size": THEME.font_size, "color": "#172033"},
        legend={**dict(LEGEND_HORIZONTAL), "font": {"size": THEME.tick_size, "color": "#172033"}, "bgcolor": "rgba(255,255,255,0.90)", "bordercolor": "rgba(71,85,105,0.22)"},
    )
    exported.update_xaxes(
        color="#334155", linecolor="#64748b", tickcolor="#64748b",
        gridcolor="rgba(71,85,105,0.18)", zeroline=False, automargin=True,
    )
    exported.update_yaxes(
        color="#334155", linecolor="#64748b", tickcolor="#64748b",
        gridcolor="rgba(71,85,105,0.18)", zeroline=False, automargin=True,
    )
    # Ternary axes do not inherit x/y axis styling.
    if getattr(exported.layout, "ternary", None):
        exported.update_layout(ternary={
            "bgcolor": "#ffffff",
            "aaxis": {"color": "#334155", "gridcolor": "rgba(71,85,105,0.25)", "linecolor": "#64748b"},
            "baxis": {"color": "#334155", "gridcolor": "rgba(71,85,105,0.25)", "linecolor": "#64748b"},
            "caxis": {"color": "#334155", "gridcolor": "rgba(71,85,105,0.25)", "linecolor": "#64748b"},
        })
    if getattr(exported.layout, "annotations", None):
        for annotation in exported.layout.annotations:
            annotation.font = {**(annotation.font.to_plotly_json() if annotation.font else {}), "color": "#172033"}
    normalize_trace_style(exported)
    return exported


def downsample_frame_for_screen(frame, *, max_rows: int = 2200):
    """Uniformly reduce large frames for interactive Plotly rendering.

    Calculations, tables and report exports keep the full dataframe. Only the
    browser-facing figure receives this deterministic sample, which avoids
    serialising tens of thousands of points on every Streamlit rerun.
    """
    if frame is None or len(frame) <= max_rows or max_rows < 3:
        return frame
    import numpy as np
    positions = np.linspace(0, len(frame) - 1, num=max_rows, dtype=int)
    positions = np.unique(np.concatenate(([0], positions, [len(frame) - 1])))
    return frame.iloc[positions].copy()


PLOTLY_SCREEN_CONFIG: Mapping[str, Any] = {
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
}
