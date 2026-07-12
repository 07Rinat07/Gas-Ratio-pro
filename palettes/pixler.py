from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

import pandas as pd
import plotly.graph_objects as go

from palettes.config import DEFAULT_PIXLER_ZONES, PixlerZone


PIXLER_RATIOS: tuple[tuple[str, str], ...] = (
    ("c1_c2", "C1/C2"),
    ("c1_c3", "C1/C3"),
    ("c1_c4", "C1/ΣC4"),
    ("c1_c5", "C1/ΣC5"),
)


@dataclass(frozen=True, slots=True)
class PixlerIntervalSummary:
    valid_measurements: int
    total_measurements: int
    median_values: tuple[float | None, ...]
    selected_values: tuple[float | None, ...]
    dominant_zone: str
    zone_support_percent: float
    conclusion: str


def _positive_or_none(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def _zone_for_value(value: float | None, zones: tuple[PixlerZone, ...]) -> str | None:
    if value is None:
        return None
    for zone in zones:
        if zone.y_min <= value < zone.y_max:
            return zone.name
    return None


def _normalized_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=[column for column, _ in PIXLER_RATIOS])
    available = [column for column, _ in PIXLER_RATIOS if column in frame.columns]
    result = pd.DataFrame(index=frame.index)
    for column, _ in PIXLER_RATIOS:
        if column in available:
            result[column] = pd.to_numeric(frame[column], errors="coerce")
        else:
            result[column] = math.nan
    return result.where(result > 0)


def analyze_pixler_interval(
    frame: pd.DataFrame | None,
    selected_row: pd.Series | Mapping[str, object] | None,
    *,
    zones: tuple[PixlerZone, ...] = DEFAULT_PIXLER_ZONES,
) -> PixlerIntervalSummary:
    numeric = _normalized_frame(frame)
    if selected_row is None:
        selected_row = {}
    selected_values = tuple(_positive_or_none(selected_row.get(column)) for column, _ in PIXLER_RATIOS)
    median_values = tuple(
        _positive_or_none(numeric[column].dropna().median()) if not numeric[column].dropna().empty else None
        for column, _ in PIXLER_RATIOS
    )
    valid_measurements = int(numeric.notna().any(axis=1).sum())
    total_measurements = int(len(numeric))

    zone_votes = [
        _zone_for_value(value, zones)
        for value in numeric.to_numpy().ravel().tolist()
        if _positive_or_none(value) is not None
    ]
    zone_votes = [vote for vote in zone_votes if vote]
    if zone_votes:
        counts = pd.Series(zone_votes).value_counts()
        dominant_zone = str(counts.index[0])
        support = float(counts.iloc[0] / counts.sum() * 100.0)
    else:
        dominant_zone = "Недостаточно данных"
        support = 0.0

    if valid_measurements == 0:
        conclusion = "Pixler: нет положительных отношений для инженерной оценки интервала."
    elif support >= 70:
        conclusion = (
            f"Pixler преимущественно поддерживает область «{dominant_zone}» "
            f"({support:.0f}% валидных отношений). Вывод требует подтверждения Haworth, ГИС и контекстом скважины."
        )
    else:
        conclusion = (
            f"Pixler показывает неоднородное распределение; ведущая область «{dominant_zone}» "
            f"поддержана только на {support:.0f}%. Требуется проверка по соседним глубинам и другим методикам."
        )

    return PixlerIntervalSummary(
        valid_measurements=valid_measurements,
        total_measurements=total_measurements,
        median_values=median_values,
        selected_values=selected_values,
        dominant_zone=dominant_zone,
        zone_support_percent=round(support, 1),
        conclusion=conclusion,
    )


def build_pixler_palette(
    row: pd.Series | Mapping[str, object],
    zones: tuple[PixlerZone, ...] = DEFAULT_PIXLER_ZONES,
    *,
    interval_frame: pd.DataFrame | None = None,
    interval_label: str = "Выбранный интервал",
    selected_depth: float | None = None,
):
    labels = [label for _, label in PIXLER_RATIOS]
    summary = analyze_pixler_interval(interval_frame, row, zones=zones)
    numeric = _normalized_frame(interval_frame)

    fig = go.Figure()
    for zone in zones:
        fig.add_shape(
            type="rect", xref="paper", yref="y", x0=0, x1=1,
            y0=zone.y_min, y1=zone.y_max,
            fillcolor=zone.color, line_width=0, layer="below",
        )
        fig.add_annotation(
            x=0.01, xref="paper", y=math.sqrt(zone.y_min * zone.y_max),
            text=zone.name, showarrow=False, font={"size": 13}, align="left",
        )

    # Облако всех измерений интервала: одна полупрозрачная серия на каждое отношение.
    if not numeric.empty:
        for column, label in PIXLER_RATIOS:
            values = numeric[column].dropna()
            if values.empty:
                continue
            fig.add_trace(go.Scatter(
                x=[label] * len(values), y=values,
                mode="markers",
                marker={"size": 6, "opacity": 0.24},
                customdata=[[str(index)] for index in values.index],
                hovertemplate=f"{label}: %{{y:.3g}}<br>Запись: %{{customdata[0]}}<extra></extra>",
                name=f"Измерения {label}",
                legendgroup="measurements",
                showlegend=(label == labels[0]),
            ))

    if any(value is not None for value in summary.median_values):
        fig.add_trace(go.Scatter(
            x=labels, y=list(summary.median_values),
            mode="lines+markers+text",
            line={"width": 3}, marker={"size": 10, "symbol": "diamond"},
            text=[f"{value:.2f}" if value is not None else "" for value in summary.median_values],
            textposition="top center",
            name=f"Медиана: {interval_label}",
            hovertemplate="%{x}: %{y:.3g}<extra>Медиана интервала</extra>",
        ))

    selected_name = "Выбранная глубина" if selected_depth is None else f"Глубина {selected_depth:g} м"
    if any(value is not None for value in summary.selected_values):
        fig.add_trace(go.Scatter(
            x=labels, y=list(summary.selected_values),
            mode="markers",
            marker={"size": 13, "symbol": "x", "line": {"width": 2}},
            name=selected_name,
            hovertemplate="%{x}: %{y:.3g}<extra>" + selected_name + "</extra>",
        ))

    fig.update_layout(
        title={"text": f"Pixler — {interval_label}<br><sup>{summary.conclusion}</sup>", "x": 0.01},
        margin={"l": 65, "r": 20, "t": 88, "b": 55},
        showlegend=True,
        legend={"orientation": "h", "y": -0.16, "x": 0},
        height=500,
        hovermode="closest",
    )
    fig.update_yaxes(title="Отношение компонентов (логарифмическая шкала)", type="log", gridcolor="rgba(120,120,120,0.20)", zeroline=False)
    fig.update_xaxes(title="Pixler ratios", tickfont={"size": 13})

    if summary.valid_measurements == 0 and all(value is None for value in summary.selected_values):
        fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", text="Нет положительных Pixler ratios", showarrow=False)

    return fig
