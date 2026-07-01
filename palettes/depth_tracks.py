from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


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


def _build_depth_tracks(df: pd.DataFrame, columns: tuple[str, ...], title: str, x_title: str):
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

    depth = _depth_axis(df)
    for column in columns:
        if column not in df.columns or df[column].isna().all():
            continue
        fig.add_trace(
            go.Scatter(
                x=df[column],
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
        height=520,
        margin={"l": 70, "r": 25, "t": 55, "b": 45},
        legend={"orientation": "h", "y": -0.18},
    )
    fig.update_xaxes(title=x_title, zeroline=False)
    fig.update_yaxes(title="Depth", autorange="reversed")
    return fig


def build_depth_gas_tracks(df: pd.DataFrame):
    return _build_depth_tracks(
        df,
        ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5"),
        "Gas components by depth",
        "Component value",
    )


def build_depth_ratio_tracks(df: pd.DataFrame):
    return _build_depth_tracks(
        df,
        ("wh", "bh", "ch", "bar2"),
        "Gas ratios by depth",
        "Ratio",
    )


def build_depth_pixler_tracks(df: pd.DataFrame):
    return _build_depth_tracks(
        df,
        ("c1_c2", "c1_c3", "c1_c4", "c1_c5"),
        "Pixler ratios by depth",
        "Pixler ratio",
    )
