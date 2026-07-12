from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


INTERPRETATION_COLORS: dict[str, str] = {
    "Газовая залежь": "#ff9f1c",
    "Жирный газ / конденсат": "#e76f51",
    "Нефтяная залежь": "#2a9d8f",
    "Сухой газ / непродуктивно": "#6c757d",
    "Остаточная нефть / непродуктивно": "#8d6e63",
    "Переходная зона / проверить": "#577590",
    "Недостаточно данных": "#adb5bd",
}


def _depth_axis(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype=float)
    if "depth" in df.columns and not df["depth"].isna().all():
        return pd.to_numeric(df["depth"], errors="coerce")
    if "depth_from" in df.columns and "depth_to" in df.columns:
        depth_from = pd.to_numeric(df["depth_from"], errors="coerce")
        depth_to = pd.to_numeric(df["depth_to"], errors="coerce")
        midpoint = ((depth_from + depth_to) / 2).combine_first(depth_from).combine_first(depth_to)
        if not midpoint.isna().all():
            return midpoint.rename("interval_mid_depth")
    if "depth_from" in df.columns and not df["depth_from"].isna().all():
        return pd.to_numeric(df["depth_from"], errors="coerce").rename("depth_from")
    if "depth_to" in df.columns and not df["depth_to"].isna().all():
        return pd.to_numeric(df["depth_to"], errors="coerce").rename("depth_to")
    return pd.Series(range(len(df)), name="technical_depth")


def _prepare_depth_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()
    result["_plot_depth"] = _depth_axis(result)
    result = result.dropna(subset=["_plot_depth"])
    if result.empty:
        return result
    return result.sort_values("_plot_depth").reset_index(drop=True)


def _build_depth_tracks(
    df: pd.DataFrame,
    columns: tuple[str, ...],
    title: str,
    x_title: str,
    *,
    depth_range: tuple[float, float] | None = None,
    x_range: tuple[float, float] | None = None,
    height: int = 520,
):
    fig = go.Figure()

    if df is None or df.empty:
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Нет данных для графика",
            showarrow=False,
        )
        return fig

    plot_df = _prepare_depth_frame(df)
    if plot_df.empty:
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Нет числовой глубины для графика",
            showarrow=False,
        )
        return fig

    depth = plot_df["_plot_depth"]
    for column in columns:
        if column not in plot_df.columns or plot_df[column].isna().all():
            continue
        fig.add_trace(
            go.Scatter(
                x=plot_df[column],
                y=depth,
                mode="lines",
                name=column,
            )
        )

    if not fig.data:
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Нет доступных кривых для графика",
            showarrow=False,
        )

    fig.update_layout(
        title=title,
        height=height,
        margin={"l": 70, "r": 25, "t": 55, "b": 45},
        legend={"orientation": "h", "y": -0.18},
    )
    fig.update_xaxes(title=x_title, zeroline=False)
    if x_range is not None:
        fig.update_xaxes(range=list(x_range))

    # Always use the factual LAS depth extent. Plotly's automatic padding can
    # otherwise round a 47 m top to 0 m and create a large empty area.
    if depth_range is None:
        top_depth = float(depth.min())
        bottom_depth = float(depth.max())
    else:
        top_depth, bottom_depth = depth_range
    yaxis_options = {
        "title": "Глубина, м",
        "range": [float(bottom_depth), float(top_depth)],
        "autorange": False,
    }
    fig.update_yaxes(**yaxis_options)
    return fig


def build_depth_gas_tracks(
    df: pd.DataFrame,
    *,
    depth_range: tuple[float, float] | None = None,
    x_range: tuple[float, float] | None = None,
    height: int = 520,
):
    return _build_depth_tracks(
        df,
        ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5"),
        "Gas components by depth",
        "Component value",
        depth_range=depth_range,
        x_range=x_range,
        height=height,
    )


def build_depth_ratio_tracks(
    df: pd.DataFrame,
    *,
    depth_range: tuple[float, float] | None = None,
    x_range: tuple[float, float] | None = None,
    height: int = 520,
):
    return _build_depth_tracks(
        df,
        ("wh", "bh", "ch", "bar2"),
        "Gas ratios by depth",
        "Ratio",
        depth_range=depth_range,
        x_range=x_range,
        height=height,
    )


def build_depth_pixler_tracks(
    df: pd.DataFrame,
    *,
    depth_range: tuple[float, float] | None = None,
    x_range: tuple[float, float] | None = None,
    height: int = 520,
):
    return _build_depth_tracks(
        df,
        ("c1_c2", "c1_c3", "c1_c4", "c1_c5"),
        "Pixler ratios by depth",
        "Pixler ratio",
        depth_range=depth_range,
        x_range=x_range,
        height=height,
    )


def build_depth_interpretation_track(
    df: pd.DataFrame,
    *,
    depth_range: tuple[float, float] | None = None,
    height: int = 520,
):
    fig = go.Figure()
    plot_df = _prepare_depth_frame(df)
    if plot_df.empty or "interpretation" not in plot_df.columns:
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Нет интерпретации для графика",
            showarrow=False,
        )
        return fig

    interpretations = plot_df["interpretation"].fillna("Недостаточно данных").astype(str)
    categories = list(dict.fromkeys(interpretations.tolist()))
    category_index = {name: index for index, name in enumerate(categories)}
    colors = [INTERPRETATION_COLORS.get(name, "#4ea1ff") for name in interpretations]

    fig.add_trace(
        go.Scatter(
            x=[category_index[name] for name in interpretations],
            y=plot_df["_plot_depth"],
            mode="markers",
            marker={"size": 11, "color": colors},
            text=interpretations,
            hovertemplate="Depth=%{y}<br>%{text}<extra></extra>",
            name="interpretation",
        )
    )
    fig.update_layout(
        title="Interpretation markers by depth",
        height=height,
        margin={"l": 70, "r": 25, "t": 55, "b": 85},
        showlegend=False,
    )
    fig.update_xaxes(
        title="Interpretation",
        tickmode="array",
        tickvals=list(category_index.values()),
        ticktext=list(category_index.keys()),
    )
    # Always use the factual LAS depth extent. Plotly's automatic padding can
    # otherwise round the first measured depth to 0 m.
    if depth_range is None:
        top_depth = float(plot_df["_plot_depth"].min())
        bottom_depth = float(plot_df["_plot_depth"].max())
    else:
        top_depth, bottom_depth = depth_range
    fig.update_yaxes(
        title="Глубина, м",
        range=[float(bottom_depth), float(top_depth)],
        autorange=False,
    )
    return fig
