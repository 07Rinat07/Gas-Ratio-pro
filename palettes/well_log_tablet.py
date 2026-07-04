from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from palettes.depth_tracks import _depth_axis, _prepare_depth_frame


DEFAULT_TABLET_COLORS: tuple[str, ...] = (
    "#111111",
    "#d62728",
    "#1f77b4",
    "#2ca02c",
    "#ff7f0e",
    "#9467bd",
    "#17becf",
    "#8c564b",
)
PREFERRED_TABLET_COLUMNS: tuple[str, ...] = (
    "gr",
    "GR",
    "total_gas",
    "TGAS",
    "c1",
    "c2",
    "c3",
    "ic4",
    "nc4",
    "ic5",
    "nc5",
    "wh",
    "bh",
    "ch",
    "c1_c2",
    "c1_c3",
    "c1_c4",
    "c1_c5",
)
DEPTH_COLUMN_NAMES = {"depth", "depth_from", "depth_to", "_plot_depth"}


@dataclass(frozen=True)
class TabletTrackConfig:
    column: str
    label: str | None = None
    unit: str | None = None
    color: str | None = None
    x_range: tuple[float, float] | None = None
    fill: bool = False


@dataclass(frozen=True)
class InterpretationMarker:
    label: str
    depth: float
    note: str = ""


@dataclass(frozen=True)
class InterpretationZone:
    label: str
    top_depth: float
    bottom_depth: float
    color: str = "#ffd966"
    note: str = ""


def numeric_tablet_columns(df: pd.DataFrame) -> tuple[str, ...]:
    if df is None or df.empty:
        return ()

    columns: list[str] = []
    for column in df.columns:
        column_name = str(column)
        if column_name in DEPTH_COLUMN_NAMES or column_name.startswith("_"):
            continue
        values = pd.to_numeric(df[column], errors="coerce")
        if values.notna().any():
            columns.append(column_name)
    return tuple(columns)


def default_tablet_columns(df: pd.DataFrame, *, limit: int = 8) -> tuple[str, ...]:
    available = numeric_tablet_columns(df)
    available_lookup = {column.lower(): column for column in available}
    selected: list[str] = []

    for preferred in PREFERRED_TABLET_COLUMNS:
        match = available_lookup.get(preferred.lower())
        if match is not None and match not in selected:
            selected.append(match)
        if len(selected) >= limit:
            return tuple(selected)

    for column in available:
        if column not in selected:
            selected.append(column)
        if len(selected) >= limit:
            break
    return tuple(selected)


def normalize_track_configs(
    columns: Sequence[str],
    *,
    x_ranges: Mapping[str, tuple[float, float] | None] | None = None,
    units: Mapping[str, str | None] | None = None,
    colors: Mapping[str, str | None] | None = None,
    fill: bool = False,
) -> tuple[TabletTrackConfig, ...]:
    """Build ordered tablet track configs from UI/project settings.

    The order of ``columns`` is preserved, because a printed log tablet is read
    left-to-right exactly as the engineer arranged the tracks in the UI.
    ``units`` and ``colors`` are optional maps keyed by dataframe column name.
    """

    ranges = x_ranges or {}
    unit_map = units or {}
    color_map = colors or {}
    configs: list[TabletTrackConfig] = []
    for index, column in enumerate(columns):
        column_name = str(column)
        configs.append(
            TabletTrackConfig(
                column=column_name,
                label=column_name,
                unit=unit_map.get(column_name),
                color=color_map.get(column_name) or DEFAULT_TABLET_COLORS[index % len(DEFAULT_TABLET_COLORS)],
                x_range=ranges.get(column_name),
                fill=fill,
            )
        )
    return tuple(configs)


def tablet_units_from_dataframe(df: pd.DataFrame) -> dict[str, str]:
    """Return LAS/unit hints stored in ``DataFrame.attrs``.

    The importer and future project loaders can attach units as either
    ``df.attrs["las_units"]`` or ``df.attrs["curve_units"]``. The renderer
    treats this metadata as optional: missing units simply produce unitless track
    titles instead of failing the report.
    """

    if df is None:
        return {}
    raw_units = df.attrs.get("las_units") or df.attrs.get("curve_units") or {}
    if not isinstance(raw_units, Mapping):
        return {}
    return {str(column): str(unit).strip() for column, unit in raw_units.items() if str(column).strip() and str(unit).strip()}


def _track_title(track: TabletTrackConfig, values: pd.Series) -> str:
    label = track.label or track.column
    unit = f", {track.unit}" if track.unit else ""
    if track.x_range is not None:
        scale = f"{track.x_range[0]:g} - {track.x_range[1]:g}"
    else:
        numeric = pd.to_numeric(values, errors="coerce").dropna()
        scale = "auto" if numeric.empty else f"auto {numeric.min():g} - {numeric.max():g}"
    fill_label = "fill" if track.fill else "line"
    return f"{label}{unit}<br>{scale}<br>{fill_label}"


def _empty_tablet_figure(message: str, *, height: int) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        text=message,
        showarrow=False,
    )
    fig.update_layout(height=height, margin={"l": 70, "r": 30, "t": 70, "b": 45})
    return fig


def build_well_log_tablet(
    df: pd.DataFrame,
    tracks: Sequence[TabletTrackConfig],
    *,
    depth_range: tuple[float, float] | None = None,
    markers: Sequence[InterpretationMarker] = (),
    zones: Sequence[InterpretationZone] = (),
    height: int = 760,
) -> go.Figure:
    if df is None or df.empty:
        return _empty_tablet_figure("Нет данных для планшета", height=height)

    selected_tracks = tuple(track for track in tracks if track.column in df.columns)
    if not selected_tracks:
        return _empty_tablet_figure("Выберите числовые параметры для планшета", height=height)

    plot_df = _prepare_depth_frame(df)
    if plot_df.empty:
        return _empty_tablet_figure("Нет числовой глубины для планшета", height=height)

    depth = plot_df["_plot_depth"]
    titles = [_track_title(track, plot_df[track.column]) for track in selected_tracks]
    fig = make_subplots(
        rows=1,
        cols=len(selected_tracks),
        shared_yaxes=True,
        horizontal_spacing=0.012,
        subplot_titles=titles,
    )

    visible_track_count = 0
    for index, track in enumerate(selected_tracks, start=1):
        values = pd.to_numeric(plot_df[track.column], errors="coerce")
        if values.isna().all():
            continue

        fig.add_trace(
            go.Scatter(
                x=values,
                y=depth,
                mode="lines",
                name=track.label or track.column,
                line={"color": track.color or DEFAULT_TABLET_COLORS[(index - 1) % len(DEFAULT_TABLET_COLORS)], "width": 1.6},
                fill="tozerox" if track.fill else None,
                hovertemplate=f"{track.column}=%{{x}}<br>Depth=%{{y}}<extra></extra>",
            ),
            row=1,
            col=index,
        )
        visible_track_count += 1
        fig.update_xaxes(title_text=track.column, zeroline=False, row=1, col=index)
        if track.x_range is not None:
            fig.update_xaxes(range=list(track.x_range), row=1, col=index)

    if visible_track_count == 0:
        return _empty_tablet_figure("В выбранных параметрах нет числовых значений", height=height)

    yaxis_options = {"title": "Depth", "autorange": "reversed"}
    if depth_range is not None:
        top_depth, bottom_depth = depth_range
        yaxis_options["range"] = [bottom_depth, top_depth]
        yaxis_options["autorange"] = False
    fig.update_yaxes(**yaxis_options)

    shapes = []
    annotations = []
    for zone in zones:
        top_depth = min(float(zone.top_depth), float(zone.bottom_depth))
        bottom_depth = max(float(zone.top_depth), float(zone.bottom_depth))
        shapes.append(
            {
                "type": "rect",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": top_depth,
                "y1": bottom_depth,
                "fillcolor": zone.color or "#ffd966",
                "opacity": 0.18,
                "line": {"width": 0},
                "layer": "below",
            }
        )
        annotations.append(
            {
                "xref": "paper",
                "x": 0.01,
                "yref": "y",
                "y": top_depth,
                "text": str(zone.label),
                "showarrow": False,
                "font": {"color": "#172033", "size": 12},
                "bgcolor": "rgba(255,255,255,0.75)",
            }
        )

    for marker in markers:
        shapes.append(
            {
                "type": "line",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": float(marker.depth),
                "y1": float(marker.depth),
                "line": {"color": "#e31a1c", "width": 1.4},
            }
        )
        annotations.append(
            {
                "xref": "paper",
                "x": 1.01,
                "yref": "y",
                "y": float(marker.depth),
                "text": f"({marker.label})",
                "showarrow": True,
                "arrowhead": 2,
                "ax": 42,
                "ay": 0,
                "font": {"color": "#e31a1c", "size": 13},
            }
        )

    fig.update_layout(
        title="Well-log tablet",
        height=height,
        margin={"l": 70, "r": 80, "t": 115, "b": 50},
        showlegend=False,
        shapes=shapes,
        annotations=list(fig.layout.annotations) + annotations,
    )
    return fig


def build_marker_interpretation_table(
    df: pd.DataFrame,
    markers: Sequence[InterpretationMarker],
    *,
    columns: Sequence[str],
) -> pd.DataFrame:
    if df is None or df.empty or not markers:
        return pd.DataFrame()

    plot_df = df.copy()
    plot_df["_plot_depth"] = _depth_axis(plot_df)
    plot_df = plot_df.dropna(subset=["_plot_depth"])
    if plot_df.empty:
        return pd.DataFrame()

    selected_columns = [column for column in columns if column in plot_df.columns]
    rows: list[dict[str, object]] = []
    for marker in markers:
        distance = (plot_df["_plot_depth"] - float(marker.depth)).abs()
        nearest_index = distance.idxmin()
        nearest_row = plot_df.loc[nearest_index]
        row: dict[str, object] = {
            "Метка": marker.label,
            "Глубина маркера": float(marker.depth),
            "Ближайшая глубина": float(nearest_row["_plot_depth"]),
        }
        for column in selected_columns:
            row[column] = nearest_row[column]
        if "interpretation" in nearest_row.index:
            row["Интерпретация"] = nearest_row["interpretation"]
        if marker.note:
            row["Комментарий"] = marker.note
        rows.append(row)

    return pd.DataFrame(rows)


def build_interpretation_zone_table(zones: Sequence[InterpretationZone]) -> pd.DataFrame:
    if not zones:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for zone in zones:
        top_depth = min(float(zone.top_depth), float(zone.bottom_depth))
        bottom_depth = max(float(zone.top_depth), float(zone.bottom_depth))
        rows.append(
            {
                "Зона": zone.label,
                "Верх": top_depth,
                "Низ": bottom_depth,
                "Мощность": bottom_depth - top_depth,
                "Цвет": zone.color,
                "Комментарий": zone.note,
            }
        )
    return pd.DataFrame(rows)
