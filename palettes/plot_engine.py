from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
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
    line_width: float = 2.4
    marker_size: int = 10
    grid_color: str = "rgba(148, 163, 184, 0.34)"
    text_color: str = "#e5edf8"
    paper_color: str = "#0b1220"
    plot_color: str = "#0b1220"
    axis_color: str = "#e2e8f0"
    margin_left: int = 72
    margin_right: int = 28
    margin_top: int = 76
    margin_bottom: int = 64


THEME = EngineeringPlotTheme()


CHART_THEME_PROFILES: Mapping[str, EngineeringPlotTheme] = {
    "screen": THEME,
    "print": EngineeringPlotTheme(
        template="plotly_white",
        font_family=THEME.font_family,
        font_size=12,
        title_size=18,
        axis_title_size=13,
        tick_size=11,
        line_width=2.6,
        marker_size=10,
        grid_color="rgba(71,85,105,0.18)",
        text_color="#172033",
        paper_color="#ffffff",
        plot_color="#ffffff",
        axis_color="#334155",
        margin_left=72,
        margin_right=28,
        margin_top=76,
        margin_bottom=64,
    ),
    "presentation": EngineeringPlotTheme(
        template="plotly_white",
        font_family=THEME.font_family,
        font_size=14,
        title_size=22,
        axis_title_size=15,
        tick_size=13,
        line_width=3.2,
        marker_size=12,
        grid_color="rgba(71,85,105,0.16)",
        text_color="#172033",
        paper_color="#ffffff",
        plot_color="#ffffff",
        axis_color="#334155",
        margin_left=82,
        margin_right=34,
        margin_top=88,
        margin_bottom=72,
    ),
}


def get_chart_theme(profile: str = "screen") -> EngineeringPlotTheme:
    """Return a validated immutable chart theme profile."""
    normalized = str(profile or "screen").strip().lower()
    try:
        return CHART_THEME_PROFILES[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(CHART_THEME_PROFILES))
        raise ValueError(f"Unknown chart theme profile '{profile}'. Supported: {supported}.") from exc


def chart_theme_signature(profile: str = "screen") -> str:
    """Stable signature for cache invalidation after visual-style changes."""
    payload = json.dumps(asdict(get_chart_theme(profile)), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()[:16]


def apply_chart_theme(
    fig: go.Figure,
    *,
    profile: str = "screen",
    width: int | None = None,
    height: int | None = None,
    preserve_legend_position: bool = False,
) -> go.Figure:
    """Apply one visual contract to screen, print or presentation figures.

    The function changes presentation only. Trace data, axis ranges and domain
    semantics remain untouched.
    """
    if not isinstance(fig, go.Figure):
        return fig
    theme = get_chart_theme(profile)
    legend = dict(LEGEND_HORIZONTAL)
    legend.update({
        "font": {"size": theme.tick_size, "color": theme.text_color},
        "bgcolor": "rgba(11,18,32,0.88)" if profile == "screen" else "rgba(255,255,255,0.90)",
        "bordercolor": "rgba(148,163,184,0.28)" if profile == "screen" else "rgba(71,85,105,0.22)",
    })
    layout: dict[str, Any] = {
        "template": theme.template,
        "paper_bgcolor": theme.paper_color,
        "plot_bgcolor": theme.plot_color,
        "font": {"family": theme.font_family, "size": theme.font_size, "color": theme.text_color},
        "margin": {
            "l": theme.margin_left, "r": theme.margin_right,
            "t": theme.margin_top, "b": theme.margin_bottom,
        },
        "uirevision": f"gas-ratio-pro-{profile}-theme",
    }
    if width is not None:
        layout["width"] = max(320, int(width))
    if height is not None:
        layout["height"] = int(height)
    if not preserve_legend_position:
        layout["legend"] = legend
    fig.update_layout(**layout)
    fig.update_xaxes(
        title_font={"size": theme.axis_title_size}, tickfont={"size": theme.tick_size},
        color=theme.axis_color, linecolor=theme.axis_color, tickcolor=theme.axis_color,
        gridcolor=theme.grid_color, zeroline=False, automargin=True,
    )
    fig.update_yaxes(
        title_font={"size": theme.axis_title_size}, tickfont={"size": theme.tick_size},
        color=theme.axis_color, linecolor=theme.axis_color, tickcolor=theme.axis_color,
        gridcolor=theme.grid_color, zeroline=False, automargin=True,
    )
    if getattr(fig.layout, "ternary", None):
        fig.update_layout(ternary={
            "bgcolor": theme.plot_color,
            "aaxis": {"color": theme.axis_color, "gridcolor": theme.grid_color, "linecolor": theme.axis_color},
            "baxis": {"color": theme.axis_color, "gridcolor": theme.grid_color, "linecolor": theme.axis_color},
            "caxis": {"color": theme.axis_color, "gridcolor": theme.grid_color, "linecolor": theme.axis_color},
        })
    return normalize_trace_style(fig, theme=theme)

ENGINEERING_COLORS: Mapping[str, str] = {
    "primary": "#38bdf8",
    "secondary": "#34d399",
    "accent": "#fb7185",
    "warning": "#fbbf24",
    "neutral": "#cbd5e1",
    "muted": "#94a3b8",
    "gas": "#fbbf24",
    "condensate": "#fb7185",
    "oil": "#22d3ee",
    "water": "#60a5fa",
    "unknown": "#d1d5db",
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
        "uirevision": "gas-ratio-pro-engineering-view",
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


def normalize_trace_style(fig: go.Figure, *, theme: EngineeringPlotTheme = THEME) -> go.Figure:
    """Apply common widths and marker sizes without overriding explicit semantics."""
    for trace in fig.data:
        if hasattr(trace, "line") and trace.line is not None:
            current_width = getattr(trace.line, "width", None)
            if current_width is None or float(current_width) < theme.line_width:
                trace.line.width = theme.line_width
        if hasattr(trace, "marker") and trace.marker is not None:
            current_size = getattr(trace.marker, "size", None)
            if current_size is None:
                trace.marker.size = theme.marker_size
            elif isinstance(current_size, (int, float)) and float(current_size) < theme.marker_size:
                trace.marker.size = theme.marker_size
    return fig



def enhance_screen_visibility(fig: go.Figure) -> go.Figure:
    """Apply a final browser-facing visibility pass without changing semantics.

    Individual plot builders keep control over colors and analytical meaning,
    while this pass guarantees that curves and markers remain readable on the
    dark engineering surface.  Filled traces are intentionally left unchanged
    so hydrocarbon zones do not become visually dominant.
    """
    if not isinstance(fig, go.Figure):
        return fig
    for trace in fig.data:
        mode = str(getattr(trace, "mode", "") or "")
        if "lines" in mode and getattr(trace, "line", None) is not None:
            width = getattr(trace.line, "width", None)
            if width is None or float(width) < THEME.line_width:
                trace.line.width = THEME.line_width
            opacity = getattr(trace, "opacity", None)
            if opacity is None or float(opacity) < 0.88:
                trace.opacity = 0.96
        if "markers" in mode and getattr(trace, "marker", None) is not None:
            size = getattr(trace.marker, "size", None)
            if size is None or (isinstance(size, (int, float)) and float(size) < THEME.marker_size):
                trace.marker.size = THEME.marker_size
            marker_line = getattr(trace.marker, "line", None)
            if marker_line is not None:
                if getattr(marker_line, "width", None) is None or float(marker_line.width or 0) < 1.2:
                    marker_line.width = 1.2
                if not getattr(marker_line, "color", None):
                    marker_line.color = "rgba(255,255,255,0.88)"
    fig.update_layout(
        uirevision="gas-ratio-pro-engineering-view",
        hoverlabel={
            "bgcolor": "#111827",
            "bordercolor": "#64748b",
            "font": {"color": "#f8fafc", "family": THEME.font_family, "size": 12},
        },
    )
    return fig

def prepare_figure_for_export(
    fig: go.Figure,
    *,
    width: int,
    height: int,
    profile: str = "print",
) -> go.Figure:
    """Return a print-safe themed copy without mutating the screen figure."""
    if not isinstance(fig, go.Figure):
        return fig
    exported = go.Figure(fig)
    apply_chart_theme(exported, profile=profile, width=width, height=height)
    theme = get_chart_theme(profile)
    if getattr(exported.layout, "annotations", None):
        for annotation in exported.layout.annotations:
            current = annotation.font.to_plotly_json() if annotation.font else {}
            annotation.font = {**current, "color": theme.text_color, "family": theme.font_family}
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
