from __future__ import annotations

from typing import Sequence

import pandas as pd
import plotly.graph_objects as go

from palettes.plot_engine import (
    LEGEND_HORIZONTAL, THEME, apply_depth_axis, apply_engineering_layout,
    engineering_hover, normalize_trace_style,
)

ENGINEERING_GRAPH_MARGIN = {"l": 76, "r": 30, "t": 112, "b": 62}
ENGINEERING_LEGEND = {
    **dict(LEGEND_HORIZONTAL),
    "y": 1.13,
    "yanchor": "bottom",
    "x": 0.0,
    "xanchor": "left",
    "bgcolor": "rgba(11,18,32,0.96)",
    "font": {"size": 11},
}

CURVE_LABELS = {
    "c1": "C1", "c2": "C2", "c3": "C3", "ic4": "iC4", "nc4": "nC4",
    "ic5": "iC5", "nc5": "nC5", "wh": "Wh", "bh": "Bh", "ch": "Ch",
    "bar2": "Bar-2", "c1_c2": "C1/C2", "c1_c3": "C1/C3",
    "c1_c4": "C1/C4", "c1_c5": "C1/C5",
}
CURVE_COLORS = {
    "c1": "#ff5a47", "c2": "#10c997", "c3": "#9b5cff", "ic4": "#ff9f43",
    "nc4": "#16c7e8", "ic5": "#ff5c93", "nc5": "#f4c430", "wh": "#f3a58f",
    "bh": "#26c6da", "ch": "#ff5c93", "bar2": "#b8e986", "c1_c2": "#9ee35d",
    "c1_c3": "#f36df0", "c1_c4": "#f5a623", "c1_c5": "#29b6f6",
}
FLUID_STYLES = {
    "oil": ("Нефть", "#22c55e"), "gas": ("Газ", "#ef4444"),
    "condensate": ("Газоконденсат", "#f59e0b"), "gas_condensate": ("Газоконденсат", "#f59e0b"),
    "water": ("Вода", "#38bdf8"), "mixed": ("Смешанный", "#a855f7"),
    "transition": ("Переходный", "#eab308"), "manual": ("Ручной интервал", "#4C78A8"),
    "unknown": ("Неопределённый", "#94a3b8"),
}

INTERPRETATION_COLORS = {
    "Газовая залежь": "#ff9f1c", "Жирный газ / конденсат": "#e76f51",
    "Нефтяная залежь": "#2a9d8f", "Сухой газ / непродуктивно": "#6c757d",
    "Остаточная нефть / непродуктивно": "#8d6e63", "Переходная зона / проверить": "#577590",
    "Недостаточно данных": "#adb5bd",
}


def _depth_axis(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype=float)
    if "depth" in df.columns and not df["depth"].isna().all():
        return pd.to_numeric(df["depth"], errors="coerce")
    if "depth_from" in df.columns and "depth_to" in df.columns:
        a = pd.to_numeric(df["depth_from"], errors="coerce")
        b = pd.to_numeric(df["depth_to"], errors="coerce")
        return ((a + b) / 2).combine_first(a).combine_first(b).rename("interval_mid_depth")
    if "depth_from" in df.columns:
        return pd.to_numeric(df["depth_from"], errors="coerce")
    if "depth_to" in df.columns:
        return pd.to_numeric(df["depth_to"], errors="coerce")
    return pd.Series(range(len(df)), name="technical_depth")


def _prepare_depth_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    result = df.copy()
    result["_plot_depth"] = _depth_axis(result)
    return result.dropna(subset=["_plot_depth"]).sort_values("_plot_depth").reset_index(drop=True)


def _add_curve_legend(fig: go.Figure, columns: Sequence[str]) -> None:
    for column in columns:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines+markers", name=CURVE_LABELS.get(column, column),
            line={"color": CURVE_COLORS.get(column, "#e2e8f0"), "width": 3},
            marker={"color": CURVE_COLORS.get(column, "#e2e8f0"), "size": 8, "symbol": "circle"},
            hoverinfo="skip", showlegend=True,
        ))


def _add_interval_overlays(fig: go.Figure, intervals: Sequence[object], selected_interval_id: str = "") -> None:
    """Add lightweight interval context without flooding Plotly with shapes.

    A full well can contain more than one hundred interpreted intervals.  Three
    separate shapes per interval on every chart caused thousands of frontend
    objects and could freeze Streamlit before the first figure was displayed.
    Normal intervals therefore use one rectangle only; explicit top/base lines
    are reserved for the selected interval.
    """

    shown: set[str] = set()
    for interval in intervals or ():
        fluid = str(getattr(interval, "fluid_type", "unknown") or "unknown").lower()
        label, color = FLUID_STYLES.get(fluid, FLUID_STYLES["unknown"])
        custom_color = str(getattr(interval, "color", "") or "").strip()
        if custom_color:
            color = custom_color
        display_label = str(getattr(interval, "display_label", "") or label)
        top = min(float(getattr(interval, "top_depth", 0.0)), float(getattr(interval, "bottom_depth", 0.0)))
        bottom = max(float(getattr(interval, "top_depth", 0.0)), float(getattr(interval, "bottom_depth", 0.0)))
        interval_id = str(getattr(interval, "interval_id", "") or "")
        selected = interval_id == selected_interval_id
        fig.add_hrect(
            y0=top,
            y1=bottom,
            fillcolor=color,
            opacity=0.24 if selected else max(0.055, min(float(getattr(interval, "opacity", 0.0) or 0.055), 0.45)),
            line={"color": color, "width": 2.4 if selected else 0.45},
            layer="below",
        )
        if selected:
            fig.add_hline(y=top, line={"color": color, "width": 2.2, "dash": "solid"})
            fig.add_hline(y=bottom, line={"color": color, "width": 2.2, "dash": "solid"})
        if fluid == "manual" and interval_id:
            thickness = max(0.0, bottom - top)
            note = str(getattr(interval, "note", "") or "")
            fig.add_trace(go.Scatter(
                x=[0.985],
                y=[(top + bottom) / 2.0],
                xaxis="x2",
                mode="markers",
                customdata=[[interval_id, display_label, top, bottom, thickness, note]],
                marker={
                    "size": 12 if selected else 9,
                    "symbol": "diamond" if selected else "square",
                    "color": color,
                    "line": {"width": 2 if selected else 1, "color": "#ffffff"},
                },
                hovertemplate=(
                    "<b>%{customdata[1]}</b><br>"
                    "Верх: %{customdata[2]:.3f} м<br>"
                    "Низ: %{customdata[3]:.3f} м<br>"
                    "Мощность: %{customdata[4]:.3f} м<br>"
                    "Комментарий: %{customdata[5]}"
                    "<extra>Выбрать интервал</extra>"
                ),
                name=f"Выбрать: {display_label}",
                showlegend=False,
            ))
            fig.update_layout(
                xaxis2={
                    "overlaying": "x",
                    "range": [0.0, 1.0],
                    "visible": False,
                    "fixedrange": True,
                }
            )

        legend_key = f"{fluid}:{display_label}" if fluid == "manual" else fluid
        if legend_key not in shown:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=display_label,
                                     marker={"size": 10, "symbol": "square", "color": color,
                                             "line": {"width": 1, "color": "#ffffff"}},
                                     hoverinfo="skip", showlegend=True))
            shown.add(legend_key)


def _build_depth_tracks(df, columns, title, x_title, *, depth_range=None, x_range=None,
                        height=520, reservoir_intervals=(), selected_interval_id=""):
    fig = go.Figure()
    plot_df = _prepare_depth_frame(df)
    if plot_df.empty:
        fig.add_annotation(x=.5, y=.5, xref="paper", yref="paper", text="Нет данных для графика", showarrow=False)
        return fig
    depth = plot_df["_plot_depth"]
    active_columns = []
    for column in columns:
        if column not in plot_df.columns or plot_df[column].isna().all():
            continue
        active_columns.append(column)
        fig.add_trace(go.Scattergl(
            x=pd.to_numeric(plot_df[column], errors="coerce"), y=depth, mode="lines", showlegend=False,
            name=CURVE_LABELS.get(column, column),
            line={"width": 2.6, "color": CURVE_COLORS.get(column)}, connectgaps=False,
            hovertemplate=engineering_hover(CURVE_LABELS.get(column, column)),
        ))
    _add_interval_overlays(fig, reservoir_intervals, selected_interval_id)
    _add_curve_legend(fig, active_columns)
    apply_engineering_layout(fig, title=title, height=height, margin=ENGINEERING_GRAPH_MARGIN,
                             legend=ENGINEERING_LEGEND, hovermode="y unified")
    fig.update_xaxes(title=x_title, zeroline=False)
    if x_range is not None:
        fig.update_xaxes(range=list(x_range))
    top_depth, bottom_depth = (float(depth.min()), float(depth.max())) if depth_range is None else depth_range
    apply_depth_axis(fig, top_depth, bottom_depth)
    normalize_trace_style(fig)
    return fig


def build_depth_gas_tracks(df, *, depth_range=None, x_range=None, height=520, reservoir_intervals=(), selected_interval_id=""):
    return _build_depth_tracks(df, ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5"),
        "Компоненты газа по глубине", "Содержание компонента", depth_range=depth_range,
        x_range=x_range, height=height, reservoir_intervals=reservoir_intervals,
        selected_interval_id=selected_interval_id)


def build_depth_ratio_tracks(df, *, depth_range=None, x_range=None, height=520, reservoir_intervals=(), selected_interval_id=""):
    return _build_depth_tracks(df, ("wh", "bh", "ch", "bar2"), "Газовые коэффициенты по глубине",
        "Значение коэффициента", depth_range=depth_range, x_range=x_range, height=height,
        reservoir_intervals=reservoir_intervals, selected_interval_id=selected_interval_id)


def build_depth_pixler_tracks(df, *, depth_range=None, x_range=None, height=520, reservoir_intervals=(), selected_interval_id=""):
    return _build_depth_tracks(df, ("c1_c2", "c1_c3", "c1_c4", "c1_c5"), "Коэффициенты Pixler по глубине",
        "Значение коэффициента Pixler", depth_range=depth_range, x_range=x_range, height=height,
        reservoir_intervals=reservoir_intervals, selected_interval_id=selected_interval_id)


def build_depth_interpretation_track(df, *, depth_range=None, height=520, reservoir_intervals=(), selected_interval_id=""):
    fig = go.Figure()
    plot_df = _prepare_depth_frame(df)
    if plot_df.empty or "interpretation" not in plot_df.columns:
        fig.add_annotation(x=.5, y=.5, xref="paper", yref="paper", text="Нет интерпретации для графика", showarrow=False)
        return fig
    interpretations = plot_df["interpretation"].fillna("Недостаточно данных").astype(str)
    categories = list(dict.fromkeys(interpretations.tolist()))
    category_index = {name: index for index, name in enumerate(categories)}
    colors = [INTERPRETATION_COLORS.get(name, "#4ea1ff") for name in interpretations]
    fig.add_trace(go.Scatter(x=[category_index[name] for name in interpretations], y=plot_df["_plot_depth"],
        mode="markers", marker={"size": 11, "color": colors, "line": {"width": .8, "color": "#fff"}},
        text=interpretations, hovertemplate="Глубина: %{y:.2f} м<br>%{text}<extra></extra>", name="Интерпретация"))
    _add_interval_overlays(fig, reservoir_intervals, selected_interval_id)
    apply_engineering_layout(fig, title="Индикаторы флюидов по глубине", height=height,
                             margin=ENGINEERING_GRAPH_MARGIN, legend=ENGINEERING_LEGEND)
    fig.update_xaxes(title="Интерпретация", tickmode="array", tickvals=list(category_index.values()), ticktext=categories)
    top_depth, bottom_depth = (float(plot_df["_plot_depth"].min()), float(plot_df["_plot_depth"].max())) if depth_range is None else depth_range
    apply_depth_axis(fig, top_depth, bottom_depth)
    normalize_trace_style(fig)
    return fig
