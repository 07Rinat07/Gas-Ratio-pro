from __future__ import annotations

"""Visual correlation tablet for published multi-well interpretations."""

import html
import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import plotly.graph_objects as go

from projects.interpretation_correlation import (
    CorrelationTie,
    CorrelationWorkspace,
    PublishedInterpretationInput,
)
from projects.interpretation_intervals import InterpretationInterval


@dataclass(frozen=True)
class CorrelationChartSettings:
    depth_min: float | None = None
    depth_max: float | None = None
    interval_opacity: float = 0.28
    tie_width: float = 2.0
    show_interval_labels: bool = True
    show_tie_labels: bool = True

    def normalized(self, *, available_min: float, available_max: float) -> "CorrelationChartSettings":
        low = available_min if self.depth_min is None else float(self.depth_min)
        high = available_max if self.depth_max is None else float(self.depth_max)
        if not math.isfinite(low) or not math.isfinite(high) or low >= high:
            raise ValueError("Некорректный диапазон глубин корреляционного планшета.")
        opacity = min(0.85, max(0.04, float(self.interval_opacity)))
        width = min(8.0, max(0.5, float(self.tie_width)))
        return CorrelationChartSettings(low, high, opacity, width, bool(self.show_interval_labels), bool(self.show_tie_labels))


@dataclass(frozen=True)
class CorrelationChartPayload:
    well_order: tuple[str, ...]
    source_by_well: Mapping[str, PublishedInterpretationInput]
    depth_min: float
    depth_max: float
    visible_ties: tuple[CorrelationTie, ...]


def _source_rank(source: PublishedInterpretationInput) -> tuple[str, str, str]:
    return (source.well_id, source.published_at, source.revision_id)


def select_workspace_sources(
    workspace: CorrelationWorkspace,
    sources: Sequence[PublishedInterpretationInput],
) -> Mapping[str, PublishedInterpretationInput]:
    """Resolve one immutable published source per well used by the workspace.

    Ties pin exact revisions. For wells without ties, the latest published revision is used.
    """
    exact: dict[tuple[str, str, str], PublishedInterpretationInput] = {
        (item.well_id, item.interpretation_id, item.revision_id): item for item in sources
    }
    selected: dict[str, PublishedInterpretationInput] = {}
    for tie in workspace.ties:
        for endpoint in (tie.left, tie.right):
            source = exact.get((endpoint.well_id, endpoint.interpretation_id, endpoint.revision_id))
            if source is None:
                raise ValueError(f"Опубликованный источник недоступен: {endpoint.well_id}.")
            previous = selected.get(endpoint.well_id)
            if previous is not None and previous.revision_id != source.revision_id:
                raise ValueError(f"Для скважины {endpoint.well_id} используются разные опубликованные ревизии.")
            selected[endpoint.well_id] = source
    for well_id in workspace.wells:
        if well_id in selected:
            continue
        candidates = [item for item in sources if item.well_id == well_id]
        if candidates:
            selected[well_id] = sorted(candidates, key=_source_rank, reverse=True)[0]
    return selected


def build_correlation_payload(
    workspace: CorrelationWorkspace,
    sources: Sequence[PublishedInterpretationInput],
    *,
    settings: CorrelationChartSettings | None = None,
) -> tuple[CorrelationChartPayload, CorrelationChartSettings]:
    selected = select_workspace_sources(workspace, sources)
    if len(selected) < 2:
        raise ValueError("Для планшета необходимы как минимум две скважины с опубликованными интерпретациями.")
    wells = tuple(well for well in workspace.wells if well in selected)
    if len(wells) < 2:
        wells = tuple(sorted(selected))
    intervals = [interval for source in selected.values() for interval in source.intervals]
    depths = [value for interval in intervals for value in (interval.top, interval.base)]
    depths.extend(endpoint.depth for tie in workspace.ties for endpoint in (tie.left, tie.right))
    if not depths:
        raise ValueError("В опубликованных источниках отсутствуют интервалы и корреляционные связи.")
    available_min, available_max = min(depths), max(depths)
    if available_min == available_max:
        available_max = available_min + 1.0
    normalized = (settings or CorrelationChartSettings()).normalized(
        available_min=available_min,
        available_max=available_max,
    )
    visible_ties = tuple(
        tie for tie in workspace.ties
        if normalized.depth_min <= tie.left.depth <= normalized.depth_max
        or normalized.depth_min <= tie.right.depth <= normalized.depth_max
    )
    return CorrelationChartPayload(wells, selected, normalized.depth_min, normalized.depth_max, visible_ties), normalized


def _rgba(hex_color: str, opacity: float) -> str:
    clean = str(hex_color or "#4C78A8").lstrip("#")
    if len(clean) != 6:
        clean = "4C78A8"
    try:
        red, green, blue = int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)
    except ValueError:
        red, green, blue = 76, 120, 168
    return f"rgba({red},{green},{blue},{opacity:.3f})"


def build_correlation_figure(
    workspace: CorrelationWorkspace,
    sources: Sequence[PublishedInterpretationInput],
    *,
    settings: CorrelationChartSettings | None = None,
) -> go.Figure:
    payload, normalized = build_correlation_payload(workspace, sources, settings=settings)
    x_by_well = {well: index for index, well in enumerate(payload.well_order)}
    figure = go.Figure()

    for well in payload.well_order:
        x = x_by_well[well]
        source = payload.source_by_well[well]
        figure.add_trace(go.Scatter(
            x=[x, x], y=[payload.depth_min, payload.depth_max], mode="lines",
            line={"color": "rgba(90,90,90,0.55)", "width": 2}, hoverinfo="skip",
            showlegend=False, name=well,
        ))
        for interval in source.intervals:
            if interval.base < payload.depth_min or interval.top > payload.depth_max:
                continue
            top, base = max(interval.top, payload.depth_min), min(interval.base, payload.depth_max)
            text = interval.label if normalized.show_interval_labels else ""
            figure.add_trace(go.Scatter(
                x=[x - 0.17, x + 0.17, x + 0.17, x - 0.17, x - 0.17],
                y=[top, top, base, base, top], mode="lines", fill="toself",
                fillcolor=_rgba(interval.color, normalized.interval_opacity),
                line={"color": interval.color, "width": 1.5},
                text=[text] * 5,
                customdata=[[well, interval.id, interval.label, interval.top, interval.base, interval.interval_type, interval.comment]] * 5,
                hovertemplate=(
                    "<b>%{customdata[2]}</b><br>Скважина: %{customdata[0]}"
                    "<br>Глубина: %{customdata[3]:.3f}–%{customdata[4]:.3f} м"
                    "<br>Тип: %{customdata[5]}<br>%{customdata[6]}<extra></extra>"
                ),
                showlegend=False,
                name=f"{well}: {interval.label}",
            ))
            if normalized.show_interval_labels:
                figure.add_annotation(
                    x=x, y=(top + base) / 2, text=interval.label, showarrow=False,
                    font={"size": 10}, textangle=-90,
                )

    for tie in payload.visible_ties:
        if tie.left.well_id not in x_by_well or tie.right.well_id not in x_by_well:
            continue
        x0, x1 = x_by_well[tie.left.well_id], x_by_well[tie.right.well_id]
        figure.add_trace(go.Scatter(
            x=[x0, x1], y=[tie.left.depth, tie.right.depth], mode="lines+markers",
            line={"width": normalized.tie_width}, marker={"size": 7},
            customdata=[[tie.id, tie.name, tie.note]] * 2,
            hovertemplate="<b>%{customdata[1]}</b><br>%{customdata[2]}<extra></extra>",
            name=tie.name, showlegend=False,
        ))
        if normalized.show_tie_labels:
            figure.add_annotation(
                x=(x0 + x1) / 2, y=(tie.left.depth + tie.right.depth) / 2,
                text=tie.name, showarrow=False, bgcolor="rgba(255,255,255,0.72)",
                font={"size": 10},
            )

    figure.update_layout(
        title=workspace.name,
        xaxis={
            "tickmode": "array", "tickvals": list(x_by_well.values()),
            "ticktext": list(payload.well_order), "side": "top", "fixedrange": True,
            "range": [-0.5, len(payload.well_order) - 0.5],
        },
        yaxis={"title": "Глубина, м", "range": [payload.depth_max, payload.depth_min]},
        hovermode="closest", height=max(520, min(1050, int((payload.depth_max - payload.depth_min) * 2.2))),
        margin={"l": 70, "r": 25, "t": 90, "b": 45},
    )
    return figure


def _interval_svg(interval: InterpretationInterval, x: float, scale_y: float, depth_min: float, opacity: float, show_label: bool) -> str:
    y = 60 + (interval.top - depth_min) * scale_y
    height = max(1.0, (interval.base - interval.top) * scale_y)
    label = html.escape(interval.label)
    color = html.escape(interval.color)
    text = ""
    if show_label and height >= 12:
        text = f'<text x="{x:.1f}" y="{y + height / 2:.1f}" font-size="10" text-anchor="middle" transform="rotate(-90 {x:.1f} {y + height / 2:.1f})">{label}</text>'
    return f'<rect x="{x - 24:.1f}" y="{y:.1f}" width="48" height="{height:.1f}" fill="{color}" fill-opacity="{opacity:.3f}" stroke="{color}"/><title>{label}: {interval.top:g}–{interval.base:g} м</title>{text}'


def export_correlation_svg(
    workspace: CorrelationWorkspace,
    sources: Sequence[PublishedInterpretationInput],
    *,
    settings: CorrelationChartSettings | None = None,
) -> bytes:
    payload, normalized = build_correlation_payload(workspace, sources, settings=settings)
    width = max(760, 220 * len(payload.well_order))
    height = 900
    plot_top, plot_bottom = 60, height - 45
    scale_y = (plot_bottom - plot_top) / (payload.depth_max - payload.depth_min)
    x_by_well = {
        well: 100 + index * ((width - 200) / max(1, len(payload.well_order) - 1))
        for index, well in enumerate(payload.well_order)
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="28" font-size="18" text-anchor="middle">{html.escape(workspace.name)}</text>',
    ]
    for well in payload.well_order:
        x = x_by_well[well]
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{plot_top}" y2="{plot_bottom}" stroke="#666" stroke-width="2"/>')
        parts.append(f'<text x="{x:.1f}" y="50" font-size="13" text-anchor="middle">{html.escape(well)}</text>')
        for interval in payload.source_by_well[well].intervals:
            if interval.base < payload.depth_min or interval.top > payload.depth_max:
                continue
            clipped = InterpretationInterval(
                id=interval.id, label=interval.label, top=max(interval.top, payload.depth_min),
                base=min(interval.base, payload.depth_max), color=interval.color,
                comment=interval.comment, interval_type=interval.interval_type,
                source=interval.source, created_at=interval.created_at, updated_at=interval.updated_at,
            )
            parts.append(_interval_svg(clipped, x, scale_y, payload.depth_min, normalized.interval_opacity, normalized.show_interval_labels))
    for tie in payload.visible_ties:
        if tie.left.well_id not in x_by_well or tie.right.well_id not in x_by_well:
            continue
        x0, x1 = x_by_well[tie.left.well_id], x_by_well[tie.right.well_id]
        y0 = plot_top + (tie.left.depth - payload.depth_min) * scale_y
        y1 = plot_top + (tie.right.depth - payload.depth_min) * scale_y
        parts.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#1f77b4" stroke-width="{normalized.tie_width:.1f}"/><title>{html.escape(tie.name)}</title>')
        if normalized.show_tie_labels:
            parts.append(f'<text x="{(x0+x1)/2:.1f}" y="{(y0+y1)/2 - 4:.1f}" font-size="10" text-anchor="middle">{html.escape(tie.name)}</text>')
    parts.append(f'<text x="20" y="{plot_top}" font-size="10">{payload.depth_min:g} м</text>')
    parts.append(f'<text x="20" y="{plot_bottom}" font-size="10">{payload.depth_max:g} м</text>')
    parts.append('</svg>')
    return "".join(parts).encode("utf-8")
