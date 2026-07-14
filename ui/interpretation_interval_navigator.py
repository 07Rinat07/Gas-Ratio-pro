from __future__ import annotations

"""Interactive depth navigator for manually managed interpretation intervals.

The module is deliberately independent from Streamlit.  It builds a Plotly
figure and extracts a selected interval UUID from Streamlit's Plotly selection
payload.  Only JSON-compatible identifiers are returned to application state.
"""

from collections.abc import Mapping, Sequence
from typing import Any

import plotly.graph_objects as go


def build_manual_interval_navigator(
    intervals: Sequence[object],
    *,
    selected_interval_id: str = "",
    height: int = 360,
) -> go.Figure:
    """Build a compact clickable depth track for manual intervals."""

    prepared: list[tuple[str, str, float, float, str, str, str]] = []
    for interval in intervals or ():
        try:
            interval_id = str(getattr(interval, "id"))
            top = float(getattr(interval, "top"))
            base = float(getattr(interval, "base"))
        except (AttributeError, TypeError, ValueError):
            continue
        if not interval_id or top == base:
            continue
        clean_top, clean_base = sorted((top, base))
        prepared.append(
            (
                interval_id,
                str(getattr(interval, "label", "") or "Ручной интервал"),
                clean_top,
                clean_base,
                str(getattr(interval, "interval_type", "") or "undefined"),
                str(getattr(interval, "color", "") or "#4C78A8"),
                str(getattr(interval, "comment", "") or ""),
            )
        )

    figure = go.Figure()
    if not prepared:
        figure.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Нет ручных интервалов",
            showarrow=False,
        )
        figure.update_layout(height=max(220, int(height)), margin={"l": 70, "r": 20, "t": 45, "b": 30})
        return figure

    prepared.sort(key=lambda item: (item[2], item[3], item[1].lower()))
    selected_id = str(selected_interval_id or "")

    for interval_id, label, top, base, interval_type, color, _comment in prepared:
        selected = interval_id == selected_id
        figure.add_shape(
            type="rect",
            xref="paper",
            yref="y",
            x0=0.08,
            x1=0.92,
            y0=top,
            y1=base,
            fillcolor=color,
            opacity=0.34 if selected else 0.16,
            line={"color": color, "width": 2.5 if selected else 0.8},
            layer="below",
        )

    customdata = []
    y_values = []
    labels = []
    colors = []
    sizes = []
    symbols = []
    line_widths = []
    for interval_id, label, top, base, interval_type, color, comment in prepared:
        thickness = base - top
        customdata.append([interval_id, label, top, base, thickness, interval_type, comment])
        y_values.append((top + base) / 2.0)
        labels.append(label)
        colors.append(color)
        selected = interval_id == selected_id
        sizes.append(18 if selected else 13)
        symbols.append("diamond" if selected else "square")
        line_widths.append(3 if selected else 1)

    figure.add_trace(
        go.Scatter(
            x=[0.5] * len(prepared),
            y=y_values,
            mode="markers+text",
            text=labels,
            textposition="middle right",
            customdata=customdata,
            marker={
                "color": colors,
                "size": sizes,
                "symbol": symbols,
                "line": {"color": "#ffffff", "width": line_widths},
            },
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>"
                "Верх: %{customdata[2]:.3f} м<br>"
                "Низ: %{customdata[3]:.3f} м<br>"
                "Мощность: %{customdata[4]:.3f} м<br>"
                "Тип: %{customdata[5]}<br>"
                "Комментарий: %{customdata[6]}"
                "<extra></extra>"
            ),
            showlegend=False,
            name="Ручные интервалы",
        )
    )

    top_depth = min(item[2] for item in prepared)
    base_depth = max(item[3] for item in prepared)
    margin = max(0.5, (base_depth - top_depth) * 0.04)
    figure.update_layout(
        title={"text": "Навигатор ручных интервалов", "x": 0.01, "xanchor": "left"},
        height=max(260, int(height)),
        margin={"l": 78, "r": 180, "t": 52, "b": 28},
        clickmode="event+select",
        dragmode="select",
        hovermode="closest",
        showlegend=False,
    )
    figure.update_xaxes(visible=False, range=[0.0, 1.0], fixedrange=True)
    figure.update_yaxes(
        title="Глубина, м",
        range=[base_depth + margin, top_depth - margin],
        autorange=False,
        showgrid=True,
    )
    return figure


def selected_interval_id_from_plotly_event(
    event: Any,
    *,
    valid_interval_ids: Sequence[str] = (),
) -> str:
    """Extract a selected UUID from a Streamlit Plotly event payload."""

    if event is None:
        return ""

    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, Mapping):
        selection = event.get("selection", event)
    if selection is None:
        return ""

    points = getattr(selection, "points", None)
    if points is None and isinstance(selection, Mapping):
        points = selection.get("points", ())
    if not points:
        return ""

    point = points[-1]
    customdata = getattr(point, "customdata", None)
    if customdata is None and isinstance(point, Mapping):
        customdata = point.get("customdata")

    if isinstance(customdata, str):
        candidate = customdata
    elif isinstance(customdata, Sequence) and not isinstance(customdata, (bytes, bytearray)) and customdata:
        candidate = str(customdata[0] or "")
    else:
        candidate = ""

    allowed = {str(value) for value in valid_interval_ids}
    if candidate and (not allowed or candidate in allowed):
        return candidate
    return ""
