from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import plotly.graph_objects as go


@dataclass(frozen=True, slots=True)
class EngineeringPlotTheme:
    template: str = "plotly_white"
    font_family: str = "Arial, sans-serif"
    font_size: int = 12
    title_size: int = 18
    axis_title_size: int = 13
    tick_size: int = 11
    line_width: float = 1.7
    marker_size: int = 8
    grid_color: str = "rgba(71, 85, 105, 0.18)"
    text_color: str = "#172033"
    paper_color: str = "#ffffff"
    plot_color: str = "#ffffff"
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
    "bgcolor": "rgba(255,255,255,0.78)",
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
        zeroline=False,
        automargin=True,
    )
    fig.update_yaxes(
        title_font={"size": THEME.axis_title_size},
        tickfont={"size": THEME.tick_size},
        gridcolor=THEME.grid_color,
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
    """Return an export copy with the same engineering theme as the screen figure."""
    if not isinstance(fig, go.Figure):
        return fig
    exported = go.Figure(fig)
    apply_engineering_layout(exported, height=height)
    exported.update_layout(width=max(320, int(width)))
    normalize_trace_style(exported)
    return exported
