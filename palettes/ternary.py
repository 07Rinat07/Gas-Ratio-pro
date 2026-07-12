from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

import pandas as pd
import plotly.graph_objects as go

from palettes.config import TernaryRegion


TERNARY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("c2_sumc", "C2/ΣC"),
    ("c3_sumc", "C3/ΣC"),
    ("nc4_sumc", "nC4/ΣC"),
)


@dataclass(frozen=True, slots=True)
class TernaryIntervalSummary:
    valid_measurements: int
    total_measurements: int
    completeness_percent: float
    median_point: tuple[float | None, float | None, float | None]
    selected_point: tuple[float | None, float | None, float | None]
    dominant_region: str
    region_support_percent: float
    conclusion: str


def _finite_or_none(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _normalize_triplet(values: list[float | None] | tuple[float | None, ...]) -> tuple[float | None, float | None, float | None]:
    if len(values) != 3 or any(value is None for value in values):
        return (None, None, None)
    total = float(sum(float(value) for value in values if value is not None))
    if total <= 0:
        return (None, None, None)
    normalized = tuple(float(value) / total for value in values if value is not None)
    return normalized[0], normalized[1], normalized[2]


def _ternary_values(row: pd.Series | Mapping[str, object]) -> tuple[float | None, float | None, float | None]:
    return _normalize_triplet([_finite_or_none(row.get(column)) for column, _ in TERNARY_COLUMNS])


def _normalized_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    result = pd.DataFrame(columns=[column for column, _ in TERNARY_COLUMNS])
    if frame is None or frame.empty:
        return result

    numeric = pd.DataFrame(index=frame.index)
    for column, _ in TERNARY_COLUMNS:
        if column in frame.columns:
            numeric[column] = pd.to_numeric(frame[column], errors="coerce")
        else:
            numeric[column] = math.nan
    numeric = numeric.where(numeric >= 0)
    totals = numeric.sum(axis=1, min_count=3)
    valid = numeric.notna().all(axis=1) & totals.gt(0)
    normalized = numeric.loc[valid].div(totals.loc[valid], axis=0)
    return normalized


def _project(point: tuple[float, float, float]) -> tuple[float, float]:
    a, b, _ = point
    return b + 0.5 * a, (math.sqrt(3.0) / 2.0) * a


def _point_in_polygon(point: tuple[float, float, float], region: TernaryRegion) -> bool:
    polygon = [_project((float(a), float(b), float(c))) for a, b, c in zip(region.a, region.b, region.c)]
    x, y = _project(point)
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _region_for_point(point: tuple[float, float, float], regions: tuple[TernaryRegion, ...]) -> str | None:
    for region in regions:
        if _point_in_polygon(point, region):
            return region.name
    return None


def analyze_ternary_interval(
    frame: pd.DataFrame | None,
    selected_row: pd.Series | Mapping[str, object] | None,
    *,
    regions: tuple[TernaryRegion, ...] = (),
) -> TernaryIntervalSummary:
    numeric = _normalized_frame(frame)
    total_measurements = 0 if frame is None else int(len(frame))
    valid_measurements = int(len(numeric))
    completeness = (valid_measurements / total_measurements * 100.0) if total_measurements else 0.0

    if numeric.empty:
        median_point: tuple[float | None, float | None, float | None] = (None, None, None)
    else:
        medians = numeric.median(axis=0)
        median_point = _normalize_triplet([float(medians[column]) for column, _ in TERNARY_COLUMNS])

    selected_point = _ternary_values({} if selected_row is None else selected_row)
    region_votes: list[str] = []
    if regions:
        for values in numeric.itertuples(index=False, name=None):
            vote = _region_for_point((float(values[0]), float(values[1]), float(values[2])), regions)
            if vote:
                region_votes.append(vote)

    if region_votes:
        counts = pd.Series(region_votes).value_counts()
        dominant_region = str(counts.index[0])
        support = float(counts.iloc[0] / len(numeric) * 100.0) if len(numeric) else 0.0
    elif valid_measurements:
        dominant_region = "Вне настроенных областей"
        support = 0.0
    else:
        dominant_region = "Недостаточно данных"
        support = 0.0

    if valid_measurements == 0:
        conclusion = "Ternary: нет строк с одновременно валидными C2, C3 и nC4 для интервальной оценки."
    elif completeness < 25:
        conclusion = (
            f"Ternary доступен только для {completeness:.0f}% измерений интервала. "
            "Вывод имеет низкую устойчивость; проверьте полноту C2, C3 и nC4."
        )
    elif support >= 60:
        conclusion = (
            f"Ternary преимущественно поддерживает область «{dominant_region}» "
            f"({support:.0f}% всех валидных точек). Результат следует сопоставить с Pixler, Haworth и ГИС."
        )
    else:
        conclusion = (
            f"Ternary показывает рассеянное или пограничное распределение; ведущая область «{dominant_region}» "
            f"поддержана на {support:.0f}%. Требуется комплексная проверка."
        )

    return TernaryIntervalSummary(
        valid_measurements=valid_measurements,
        total_measurements=total_measurements,
        completeness_percent=round(completeness, 1),
        median_point=median_point,
        selected_point=selected_point,
        dominant_region=dominant_region,
        region_support_percent=round(support, 1),
        conclusion=conclusion,
    )


def _add_regions(fig: go.Figure, regions: tuple[TernaryRegion, ...]) -> None:
    for region in regions:
        fig.add_trace(
            go.Scatterternary(
                a=list(region.a) + [region.a[0]],
                b=list(region.b) + [region.b[0]],
                c=list(region.c) + [region.c[0]],
                mode="lines",
                fill="toself",
                fillcolor=region.color,
                line={"color": "rgba(80, 80, 80, 0.45)", "width": 1.2},
                name=region.name,
                hovertemplate=region.name + "<extra>Методическая область</extra>",
            )
        )


def build_ternary_palette(
    row: pd.Series | Mapping[str, object],
    regions: tuple[TernaryRegion, ...] = (),
    *,
    interval_frame: pd.DataFrame | None = None,
    interval_label: str = "Выбранный интервал",
    selected_depth: float | None = None,
):
    summary = analyze_ternary_interval(interval_frame, row, regions=regions)
    numeric = _normalized_frame(interval_frame)

    fig = go.Figure()
    _add_regions(fig, regions)

    if not numeric.empty:
        depth_values = None
        if interval_frame is not None and "depth" in interval_frame.columns:
            depth_values = pd.to_numeric(interval_frame.loc[numeric.index, "depth"], errors="coerce")
        customdata = [
            ["—" if depth_values is None or pd.isna(depth_values.loc[index]) else f"{float(depth_values.loc[index]):g} м"]
            for index in numeric.index
        ]
        fig.add_trace(
            go.Scatterternary(
                a=numeric[TERNARY_COLUMNS[0][0]],
                b=numeric[TERNARY_COLUMNS[1][0]],
                c=numeric[TERNARY_COLUMNS[2][0]],
                mode="markers",
                marker={"size": 7, "opacity": 0.32},
                customdata=customdata,
                hovertemplate=(
                    "Глубина: %{customdata[0]}<br>"
                    "C2/ΣC: %{a:.3f}<br>C3/ΣC: %{b:.3f}<br>nC4/ΣC: %{c:.3f}"
                    "<extra>Измерение интервала</extra>"
                ),
                name=f"Измерения ({summary.valid_measurements})",
            )
        )

    if all(value is not None for value in summary.median_point):
        fig.add_trace(
            go.Scatterternary(
                a=[summary.median_point[0]],
                b=[summary.median_point[1]],
                c=[summary.median_point[2]],
                mode="markers+text",
                marker={"size": 16, "symbol": "diamond", "line": {"width": 2}},
                text=["Медиана"],
                textposition="top center",
                hovertemplate=(
                    "C2/ΣC: %{a:.3f}<br>C3/ΣC: %{b:.3f}<br>nC4/ΣC: %{c:.3f}"
                    "<extra>Центр интервала</extra>"
                ),
                name="Медианный центр",
            )
        )

    if all(value is not None for value in summary.selected_point):
        selected_name = "Выбранная глубина" if selected_depth is None else f"Глубина {selected_depth:g} м"
        fig.add_trace(
            go.Scatterternary(
                a=[summary.selected_point[0]],
                b=[summary.selected_point[1]],
                c=[summary.selected_point[2]],
                mode="markers+text",
                marker={"size": 15, "symbol": "x", "line": {"width": 3}},
                text=[selected_name],
                textposition="bottom center",
                hovertemplate=(
                    "C2/ΣC: %{a:.3f}<br>C3/ΣC: %{b:.3f}<br>nC4/ΣC: %{c:.3f}"
                    "<extra>" + selected_name + "</extra>"
                ),
                name=selected_name,
            )
        )

    fig.update_layout(
        title={
            "text": (
                f"Ternary — {interval_label}<br>"
                f"<sup>валидных точек: {summary.valid_measurements}/{summary.total_measurements}; "
                f"ведущая область: {summary.dominant_region} ({summary.region_support_percent:.0f}%)</sup>"
            ),
            "x": 0.02,
            "xanchor": "left",
        },
        height=500,
        margin={"l": 20, "r": 20, "t": 85, "b": 60},
        ternary={
            "sum": 1,
            "aaxis": {"title": "C2/ΣC", "min": 0.0, "ticksuffix": ""},
            "baxis": {"title": "C3/ΣC", "min": 0.0, "ticksuffix": ""},
            "caxis": {"title": "nC4/ΣC", "min": 0.0, "ticksuffix": ""},
        },
        showlegend=True,
        legend={"orientation": "h", "y": -0.13, "x": 0.0},
        annotations=(
            ([{
                "text": "Недостаточно совместно валидных C2, C3 и nC4",
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 13},
            }] if summary.valid_measurements == 0 else [])
            + [{
                "text": summary.conclusion,
                "xref": "paper",
                "yref": "paper",
                "x": 0.0,
                "y": -0.27,
                "xanchor": "left",
                "showarrow": False,
                "align": "left",
                "font": {"size": 11},
            }]
        ),
    )
    return fig
