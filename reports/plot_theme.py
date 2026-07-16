"""Corporate print theme for GAS RATIO PRO engineering figures.

The function is intentionally renderer-neutral at the call boundary: any object
with Plotly-compatible ``update_layout``/``update_traces`` methods can be used.
It mutates a cloned figure when ``full_copy`` is available and otherwise applies
safe layout changes in place.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def apply_report_plot_theme(figure: Any) -> Any:
    """Return a print-ready figure with readable fonts and engineering styling."""
    if figure is None:
        return figure
    try:
        themed = figure.full_copy() if callable(getattr(figure, "full_copy", None)) else deepcopy(figure)
    except Exception:
        themed = figure

    update_layout = getattr(themed, "update_layout", None)
    if callable(update_layout):
        update_layout(
            template="plotly_white",
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font={"family": "Arial, DejaVu Sans, sans-serif", "size": 15, "color": "#172033"},
            title={"font": {"size": 20, "color": "#111827"}, "x": 0.02, "xanchor": "left"},
            legend={
                "font": {"size": 14, "color": "#172033"},
                "bgcolor": "rgba(255,255,255,0.94)",
                "bordercolor": "#cbd5e1",
                "borderwidth": 1,
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "left",
                "x": 0.0,
            },
            margin={"l": 78, "r": 36, "t": 120, "b": 72},
        )
        # Plotly accepts these magic-underscore properties for all axes.
        update_layout(
            xaxis={
                "showgrid": True,
                "gridcolor": "#dbe3ec",
                "gridwidth": 1,
                "zeroline": False,
                "tickfont": {"size": 13},
                "title": {"font": {"size": 15}},
                "linecolor": "#64748b",
                "linewidth": 1,
                "mirror": True,
            },
            yaxis={
                "showgrid": True,
                "gridcolor": "#dbe3ec",
                "gridwidth": 1,
                "zeroline": False,
                "tickfont": {"size": 13},
                "title": {"font": {"size": 15}},
                "linecolor": "#64748b",
                "linewidth": 1,
                "mirror": True,
            },
        )
    update_traces = getattr(themed, "update_traces", None)
    if callable(update_traces):
        try:
            update_traces(line={"width": 2.2}, selector={"type": "scatter"})
        except Exception:
            pass
        try:
            update_traces(marker={"size": 8}, selector={"mode": "markers"})
        except Exception:
            pass
    return themed
