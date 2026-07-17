from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from palettes.plot_engine import DEPTH_AXIS_TITLE, THEME, apply_depth_axis, apply_engineering_layout, engineering_hover, normalize_trace_style

from core.hydrocarbon_intervals import HydrocarbonInterval, MARKER_STYLE_BY_FLUID


DEFAULT_TRACK_COLUMNS: tuple[str, ...] = (
    "c1",
    "c2",
    "c3",
    "wh",
    "bh",
    "ch",
    "c1_c2",
    "c1_c3",
    "inverse_oil_indicator",
)

FLUID_PLOT_LABELS: Mapping[str, str] = {
    "gas": "Газ",
    "oil": "Нефть",
    "condensate": "Газоконденсат",
    "gas_oil": "Газ–нефть",
    "oil_gas": "Нефть–газ",
    "mixed": "Смешанный",
    "transition": "Переходный",
    "water": "Вода",
    "uncertain": "Неопределённый",
}

CURVE_PRINT_SPECS: Mapping[str, Mapping[str, str]] = {
    "c1": {"label": "C1", "description": "Метан", "color": "#ef4444"},
    "c2": {"label": "C2", "description": "Этан", "color": "#10b981"},
    "c3": {"label": "C3", "description": "Пропан", "color": "#8b5cf6"},
    "ic4": {"label": "iC4", "description": "Изобутан", "color": "#f97316"},
    "nc4": {"label": "nC4", "description": "Н-бутан", "color": "#06b6d4"},
    "ic5": {"label": "iC5", "description": "Изопентан", "color": "#ec4899"},
    "nc5": {"label": "nC5", "description": "Н-пентан", "color": "#eab308"},
    "wh": {"label": "Wh", "description": "Влажность газа (Wetness)", "color": "#92400e"},
    "bh": {"label": "Bh", "description": "Баланс компонентов (Balance)", "color": "#0ea5e9"},
    "ch": {"label": "Ch", "description": "Характер газа (Character)", "color": "#f43f5e"},
    "c1_c2": {"label": "C1/C2", "description": "Отношение метана к этану", "color": "#84cc16"},
    "c1_c3": {"label": "C1/C3", "description": "Отношение метана к пропану", "color": "#d946ef"},
    "inverse_oil_indicator": {"label": "Oil Inv.", "description": "Расчётный индикатор нефтяного отклика", "color": "#f59e0b"},
}

FLUID_PRINT_SPECS: Mapping[str, Mapping[str, str]] = {
    "oil": {"label": "Нефть", "color": "#16a34a", "description": "Вероятный нефтенасыщенный интервал"},
    "gas": {"label": "Газ", "color": "#dc2626", "description": "Вероятный газонасыщенный интервал"},
    "condensate": {"label": "Газоконденсат", "color": "#f97316", "description": "Вероятный газоконденсатный интервал"},
    "water": {"label": "Вода", "color": "#0284c7", "description": "Вероятный водонасыщенный интервал"},
    "mixed": {"label": "Смешанный", "color": "#7c3aed", "description": "Смешанный или неоднозначный отклик"},
    "transition": {"label": "Переходный", "color": "#ca8a04", "description": "Переходная зона, требуется проверка"},
    "uncertain": {"label": "Неопределённый", "color": "#64748b", "description": "Недостаточно данных для уверенной классификации"},
}


@dataclass(frozen=True)
class WellLogPlotConfig:
    """Configuration for the professional printable well-log tablet.

    The renderer is report-oriented: it keeps the common depth axis, reduces
    excessive point count before plotting and overlays interpreted intervals as
    explicit engineering zones. It intentionally does not run interpretation
    logic; intervals must come from the frozen Hydrocarbon Interpretation Engine.
    """

    depth_column: str = "depth"
    track_columns: tuple[str, ...] = DEFAULT_TRACK_COLUMNS
    max_points_per_track: int = 2500
    height: int = 850
    title: str = "Профессиональный планшет интерпретации"
    show_interval_track: bool = True
    auto_crop_to_active_data: bool = True
    max_interval_overlays: int = 12
    crop_top: float | None = None
    crop_base: float | None = None
    crop_padding_m: float | None = None
    report_kind: str = "overview"
    report_title: str = ""
    report_group_index: int = 0
    layout_profile: str = "print"
    show_curve_legend: bool = False



TRACK_WIDTH_WEIGHTS: Mapping[str, float] = {
    "c1": 1.25,
    "c2": 0.95,
    "c3": 0.95,
    "ic4": 0.85,
    "nc4": 0.85,
    "ic5": 0.85,
    "nc5": 0.85,
    "wh": 1.05,
    "bh": 1.05,
    "ch": 1.05,
    "c1_c2": 1.10,
    "c1_c3": 1.10,
    "c1_c4": 1.10,
    "c1_c5": 1.10,
    "inverse_oil_indicator": 1.30,
}


def track_layout_widths(
    columns: Sequence[str],
    *,
    show_interval_track: bool = True,
    profile: str = "print",
) -> tuple[float, ...]:
    """Return semantic track widths instead of equal-width columns.

    Important analytical tracks receive more room while compact component
    tracks stay narrow.  The values are relative weights accepted by Plotly.
    """
    normalized = str(profile or "print").strip().lower()
    interval_weight = 1.55 if normalized == "print" else 1.35
    weights = [interval_weight] if show_interval_track else []
    for column in columns:
        weight = float(TRACK_WIDTH_WEIGHTS.get(str(column), 1.0))
        if normalized == "screen":
            # Screen mode favours a compact tablet; print keeps more space for
            # long labels and interval annotations.
            weight = max(0.78, weight * 0.92)
        weights.append(weight)
    return tuple(weights)


def track_title_font_size(track_count: int, *, profile: str = "print") -> int:
    """Choose a readable title size without allowing title collisions."""
    count = max(1, int(track_count))
    normalized = str(profile or "print").strip().lower()
    if normalized == "screen":
        return 14 if count <= 8 else 12 if count <= 12 else 11
    return 28 if count <= 8 else 24 if count <= 12 else 21


@dataclass(frozen=True)
class ReportIntervalGroup:
    """Depth-clustered interval group used for detailed report pages."""

    index: int
    intervals: tuple[HydrocarbonInterval, ...]
    top: float
    base: float
    score: float


def _interval_score(interval: HydrocarbonInterval) -> float:
    confidence = float(getattr(interval, "confidence_score", 0) or 0)
    thickness = abs(float(interval.base) - float(interval.top))
    fluid_weight = {"oil": 10.0, "gas": 9.0, "condensate": 8.0, "gas_oil": 7.0, "oil_gas": 7.0}.get(str(interval.fluid_type), 3.0)
    return confidence + min(thickness, 50.0) * 0.5 + fluid_weight


def group_intervals_for_report(
    intervals: Sequence[HydrocarbonInterval],
    *,
    max_groups: int = 15,
    merge_gap_m: float = 12.0,
    max_group_span_m: float = 120.0,
) -> tuple[ReportIntervalGroup, ...]:
    """Cluster nearby productive intervals into printable detail pages.

    The selection is deterministic.  Nearby intervals share one page, while
    distant intervals get their own enlarged tablet.  When the report contains
    more groups than allowed, the most significant groups are retained and then
    restored to depth order.
    """
    productive = [i for i in intervals if abs(float(i.base) - float(i.top)) > 0]
    productive.sort(key=lambda i: min(float(i.top), float(i.base)))
    raw: list[list[HydrocarbonInterval]] = []
    for interval in productive:
        top = min(float(interval.top), float(interval.base))
        base = max(float(interval.top), float(interval.base))
        if not raw:
            raw.append([interval]); continue
        prev_top = min(min(float(i.top), float(i.base)) for i in raw[-1])
        prev_base = max(max(float(i.top), float(i.base)) for i in raw[-1])
        if top - prev_base <= merge_gap_m and max(base, prev_base) - prev_top <= max_group_span_m:
            raw[-1].append(interval)
        else:
            raw.append([interval])
    groups=[]
    for idx, items in enumerate(raw, start=1):
        top=min(min(float(i.top), float(i.base)) for i in items)
        base=max(max(float(i.top), float(i.base)) for i in items)
        groups.append(ReportIntervalGroup(idx, tuple(items), top, base, sum(_interval_score(i) for i in items)))
    if len(groups) > max_groups:
        groups=sorted(groups, key=lambda g: g.score, reverse=True)[:max_groups]
        groups=sorted(groups, key=lambda g: g.top)
    return tuple(ReportIntervalGroup(idx, g.intervals, g.top, g.base, g.score) for idx, g in enumerate(groups, start=1))


def adaptive_detail_padding(top: float, base: float) -> float:
    thickness=max(abs(float(base)-float(top)), 0.1)
    if thickness < 2.0:
        return 2.0
    if thickness < 10.0:
        return 5.0
    if thickness < 35.0:
        return 10.0
    return min(25.0, max(12.0, thickness * 0.25))


@dataclass(frozen=True)
class DownsampleSummary:
    original_points: int
    plotted_points: int
    method: str


@dataclass(frozen=True)
class WellLogPlotResult:
    figure: go.Figure
    plotted_columns: tuple[str, ...]
    downsample: DownsampleSummary
    interval_count: int


def _numeric_depth_frame(df: pd.DataFrame, depth_column: str) -> pd.DataFrame:
    if df is None or df.empty or depth_column not in df.columns:
        return pd.DataFrame()
    frame = df.copy()
    frame[depth_column] = pd.to_numeric(frame[depth_column], errors="coerce")
    frame = frame.dropna(subset=[depth_column])
    if frame.empty:
        return frame
    return frame.sort_values(depth_column).reset_index(drop=True)


def _available_track_columns(df: pd.DataFrame, requested: Sequence[str], depth_column: str) -> tuple[str, ...]:
    columns: list[str] = []
    for column in requested:
        column_name = str(column)
        if column_name == depth_column or column_name not in df.columns:
            continue
        values = pd.to_numeric(df[column_name], errors="coerce")
        if values.notna().any():
            columns.append(column_name)
    return tuple(columns)


def downsample_depth_frame(
    df: pd.DataFrame,
    *,
    depth_column: str = "depth",
    track_columns: Sequence[str] = (),
    max_points: int = 2500,
) -> tuple[pd.DataFrame, DownsampleSummary]:
    """Return a depth-sorted frame with bounded point count for readable plots.

    Large LAS files can contain tens or hundreds of thousands of rows. Plotting
    every row makes browser-based reports look like vertical fences and slows
    printing. This function uses deterministic stride downsampling and always
    keeps the last row, which preserves the displayed depth interval boundaries
    without adding random or non-reproducible behavior.
    """

    frame = _numeric_depth_frame(df, depth_column)
    original_points = len(frame)
    if frame.empty:
        return frame, DownsampleSummary(original_points=0, plotted_points=0, method="empty")

    safe_max_points = max(2, int(max_points or 2500))
    if original_points <= safe_max_points:
        return frame, DownsampleSummary(original_points=original_points, plotted_points=original_points, method="none")

    stride = max(1, original_points // safe_max_points)
    sampled = frame.iloc[::stride].copy()
    last_index = frame.index[-1]
    if sampled.index[-1] != last_index:
        sampled = pd.concat([sampled, frame.iloc[[-1]]], ignore_index=False)
    sampled = sampled.drop_duplicates(subset=[depth_column], keep="last").reset_index(drop=True)
    return sampled, DownsampleSummary(original_points=original_points, plotted_points=len(sampled), method=f"stride:{stride}")


def _interval_label(interval: HydrocarbonInterval, index: int) -> str:
    fluid = FLUID_PLOT_LABELS.get(interval.fluid_type, str(interval.fluid_type or "HC").upper())
    confidence = f"{interval.confidence_score}%" if interval.confidence_score else str(interval.confidence or "")
    return f"HC-{index:03d}<br>{float(interval.top):g}–{float(interval.base):g} м<br>{fluid} · {confidence}"


def _interval_style(fluid_type: str) -> Mapping[str, str]:
    return MARKER_STYLE_BY_FLUID.get(fluid_type, {"color": "#7f7f7f", "fill": "rgba(127,127,127,0.14)", "label": "HC"})


def _curve_range(values: pd.Series) -> tuple[float, float] | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    low = float(numeric.quantile(0.02))
    high = float(numeric.quantile(0.98))
    if low == high:
        low = float(numeric.min())
        high = float(numeric.max())
    if low == high:
        pad = abs(low) * 0.05 or 1.0
        return low - pad, high + pad
    pad = (high - low) * 0.05
    return low - pad, high + pad


def _track_statistics(frame: pd.DataFrame, columns: Sequence[str]) -> list[dict[str, object]]:
    """Return print-safe statistics for visible engineering curves."""
    rows: list[dict[str, object]] = []
    for column in columns:
        values = pd.to_numeric(frame.get(column), errors="coerce").dropna()
        if values.empty:
            continue
        rows.append({
            "key": column,
            "label": CURVE_PRINT_SPECS.get(column, {}).get("label", column),
            "minimum": float(values.min()),
            "maximum": float(values.max()),
            "mean": float(values.mean()),
            "sum": float(values.sum()),
            "count": int(values.count()),
        })
    gas_columns = [name for name in ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5") if name in frame.columns]
    if gas_columns:
        gas_values = frame[gas_columns].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1).dropna()
        if not gas_values.empty:
            rows.append({
                "key": "c1_c5_total", "label": "Σ C1–C5",
                "minimum": float(gas_values.min()), "maximum": float(gas_values.max()),
                "mean": float(gas_values.mean()), "sum": float(gas_values.sum()),
                "count": int(gas_values.count()),
            })
    return rows


def build_professional_well_log_plot(
    df: pd.DataFrame,
    intervals: Sequence[HydrocarbonInterval] = (),
    *,
    config: WellLogPlotConfig | None = None,
) -> WellLogPlotResult:
    """Build the first professional report tablet for interpreted intervals.

    The plot is designed for reports: one common reversed depth axis, one
    optional interval column, bounded curve point count, interval background
    zones across all tracks and readable labels inside the interval track.
    """

    cfg = config or WellLogPlotConfig()
    raw_selected_plot_points = getattr(df, "attrs", {}).get("report_plot_selection", ()) or ()
    if isinstance(raw_selected_plot_points, dict):
        selected_plot_points = [dict(raw_selected_plot_points)]
    else:
        selected_plot_points = [dict(item) for item in raw_selected_plot_points if isinstance(item, dict)]
    prepared = _numeric_depth_frame(df, cfg.depth_column)
    if prepared.empty:
        fig = go.Figure()
        fig.update_layout(title=cfg.title, height=cfg.height, annotations=[{"text": "Нет данных глубины для планшета", "showarrow": False}])
        return WellLogPlotResult(fig, (), DownsampleSummary(0, 0, "empty"), len(intervals))

    plotted_columns = _available_track_columns(prepared, cfg.track_columns, cfg.depth_column)

    # Printable tablets should focus on the interpreted interval envelope first.
    # Curve-only detection can be fooled by tiny non-zero noise near the top of a
    # LAS file, leaving most of the page empty.  Positive-thickness interpreted
    # intervals are the authoritative print range; active curves are the fallback.
    if cfg.crop_top is not None and cfg.crop_base is not None:
        crop_top = min(float(cfg.crop_top), float(cfg.crop_base))
        crop_bottom = max(float(cfg.crop_top), float(cfg.crop_base))
        pad = float(cfg.crop_padding_m if cfg.crop_padding_m is not None else adaptive_detail_padding(crop_top, crop_bottom))
        cropped = prepared.loc[prepared[cfg.depth_column].between(crop_top - pad, crop_bottom + pad)].copy()
        if not cropped.empty:
            prepared = cropped.reset_index(drop=True)
    elif cfg.auto_crop_to_active_data:
        positive_intervals = [
            interval for interval in intervals
            if abs(float(interval.base) - float(interval.top)) > 0
        ]
        crop_top = crop_bottom = None
        if positive_intervals:
            crop_top = min(min(float(i.top), float(i.base)) for i in positive_intervals)
            crop_bottom = max(max(float(i.top), float(i.base)) for i in positive_intervals)
        elif plotted_columns:
            numeric_tracks = prepared[list(plotted_columns)].apply(pd.to_numeric, errors="coerce")
            active_mask = numeric_tracks.notna().any(axis=1) & numeric_tracks.abs().fillna(0).gt(1e-12).any(axis=1)
            if active_mask.any():
                active_depths = prepared.loc[active_mask, cfg.depth_column]
                crop_top = float(active_depths.min())
                crop_bottom = float(active_depths.max())
        if crop_top is not None and crop_bottom is not None:
            active_span = max(crop_bottom - crop_top, 1.0)
            pad = max(active_span * 0.025, 2.0)
            cropped = prepared.loc[
                prepared[cfg.depth_column].between(crop_top - pad, crop_bottom + pad)
            ].copy()
            if len(cropped) >= 10:
                prepared = cropped.reset_index(drop=True)

    sampled, summary = downsample_depth_frame(
        prepared,
        depth_column=cfg.depth_column,
        track_columns=plotted_columns,
        max_points=cfg.max_points_per_track,
    )

    statistics_rows = _track_statistics(prepared, plotted_columns)
    statistics_by_key = {str(item.get("key")): item for item in statistics_rows}
    profile = str(cfg.layout_profile or "print").strip().lower()
    is_screen = profile == "screen"

    curve_titles: list[str] = []
    for column in plotted_columns:
        label = CURVE_PRINT_SPECS.get(column, {}).get("label", column)
        if is_screen:
            curve_titles.append(str(label))
            continue
        stats = statistics_by_key.get(column, {})
        if stats:
            curve_titles.append(
                f"<b>{label}</b><br>"
                f"<span style='font-size:26px'>"
                f"min {float(stats.get('minimum', 0)):.3g} · "
                f"avg {float(stats.get('mean', 0)):.3g} · "
                f"max {float(stats.get('maximum', 0)):.3g}</span>"
            )
        else:
            curve_titles.append(str(label))
    column_titles = (["Интервалы"] if cfg.show_interval_track else []) + curve_titles
    if not column_titles:
        fig = go.Figure()
        fig.update_layout(title=cfg.title, height=cfg.height, annotations=[{"text": "Нет числовых треков для планшета", "showarrow": False}])
        return WellLogPlotResult(fig, plotted_columns, summary, len(intervals))

    widths = list(track_layout_widths(
        plotted_columns,
        show_interval_track=cfg.show_interval_track,
        profile=cfg.layout_profile,
    ))
    fig = make_subplots(
        rows=1,
        cols=len(column_titles),
        shared_yaxes=True,
        horizontal_spacing=0.0025,
        column_widths=widths,
        subplot_titles=column_titles,
    )

    depth = sampled[cfg.depth_column]
    first_curve_col = 2 if cfg.show_interval_track else 1

    if cfg.show_interval_track:
        fig.add_trace(
            go.Scatter(
                x=[0] * len(depth),
                y=depth,
                mode="lines",
                line={"color": "rgba(0,0,0,0)", "width": 0},
                hoverinfo="skip",
                showlegend=False,
            ),
            row=1,
            col=1,
        )
        fig.update_xaxes(visible=False, range=[0, 1], row=1, col=1)

    for offset, column in enumerate(plotted_columns, start=0):
        col_index = first_curve_col + offset
        values = pd.to_numeric(sampled[column], errors="coerce")
        fig.add_trace(
            go.Scatter(
                x=values,
                y=depth,
                mode="lines",
                name=(f"{CURVE_PRINT_SPECS.get(column, {}).get('label', column)} — {CURVE_PRINT_SPECS.get(column, {}).get('description', 'Расчётная кривая')}"),
                line={"width": max(float(THEME.line_width), 2.8), "color": CURVE_PRINT_SPECS.get(column, {}).get("color", "#334155")},
                connectgaps=False,
                hovertemplate=engineering_hover(column),
                showlegend=True,
            ),
            row=1,
            col=col_index,
        )
        curve_range = _curve_range(values)
        track_label = CURVE_PRINT_SPECS.get(column, {}).get("label", column)
        fig.update_xaxes(title_text=track_label, zeroline=False, showgrid=True, row=1, col=col_index)
        if curve_range is not None:
            fig.update_xaxes(range=list(curve_range), row=1, col=col_index)

    top_depth = float(prepared[cfg.depth_column].min())
    bottom_depth = float(prepared[cfg.depth_column].max())
    apply_depth_axis(fig, top_depth, bottom_depth, title=DEPTH_AXIS_TITLE, showgrid=True)

    shapes: list[dict[str, object]] = []
    annotations = list(fig.layout.annotations or ())
    visible_intervals = [
        interval for interval in intervals
        if max(float(interval.top), float(interval.base)) >= top_depth
        and min(float(interval.top), float(interval.base)) <= bottom_depth
        and abs(float(interval.base) - float(interval.top)) > 0
    ]
    visible_intervals = sorted(
        visible_intervals,
        key=lambda interval: (float(getattr(interval, "confidence_score", 0) or 0), abs(float(interval.base) - float(interval.top))),
        reverse=True,
    )[: max(1, int(cfg.max_interval_overlays))]
    priority_interval = max(
        visible_intervals,
        key=lambda interval: (float(getattr(interval, "confidence_score", 0) or 0), abs(float(interval.base) - float(interval.top))),
        default=None,
    )
    visible_intervals = sorted(visible_intervals, key=lambda interval: min(float(interval.top), float(interval.base)))
    for index, interval in enumerate(visible_intervals, start=1):
        interval_top = min(float(interval.top), float(interval.base))
        interval_base = max(float(interval.top), float(interval.base))
        style = _interval_style(interval.fluid_type)
        fill = str(style.get("fill", "rgba(127,127,127,0.14)"))
        color = str(style.get("color", "#7f7f7f"))
        is_priority = interval is priority_interval
        interval_span = max(interval_base - interval_top, 0.0)
        plotted_span = max(bottom_depth - top_depth, 1e-9)
        covers_most_of_plot = interval_span / plotted_span >= 0.70
        # A full-depth selected interval previously washed the entire printed
        # tablet in pale green, hiding curves and making the fluid type unclear.
        # Keep the categorical colour in the dedicated interval track and use
        # only boundary lines across analytical tracks for very large intervals.
        if not covers_most_of_plot:
            shapes.append(
                {
                    "type": "rect", "xref": "paper", "x0": 0, "x1": 1,
                    "yref": "y", "y0": interval_top, "y1": interval_base,
                    "fillcolor": fill,
                    "line": {"color": "#f6c344" if is_priority else color, "width": 2.4 if is_priority else 0.8},
                    "layer": "below",
                }
            )
        else:
            for boundary in (interval_top, interval_base):
                shapes.append({
                    "type": "line", "xref": "paper", "x0": 0, "x1": 1,
                    "yref": "y", "y0": boundary, "y1": boundary,
                    "line": {"color": "#f6c344" if is_priority else color, "width": 2.4},
                    "layer": "above",
                })
        if cfg.show_interval_track:
            # Strong categorical stripe makes OIL/GAS/COND immediately visible
            # in PDF/PNG even when the interval occupies the whole depth range.
            shapes.append({
                "type": "rect", "xref": "x", "x0": 0.05, "x1": 0.95,
                "yref": "y", "y0": interval_top, "y1": interval_base,
                "fillcolor": color,
                "opacity": 0.32,
                "line": {"color": "#f6c344" if is_priority else color, "width": 2.0},
                "layer": "below",
            })
        if cfg.show_interval_track:
            annotations.append(
                {
                    "xref": "x",
                    "yref": "y",
                    "x": 0.5,
                    "y": (interval_top + interval_base) / 2,
                    "text": _interval_label(interval, index),
                    "showarrow": False,
                    "font": {"size": 42 if not is_screen else 16, "color": "#101827"},
                    "bgcolor": "rgba(255,255,255,0.98)",
                    "bordercolor": color,
                    "borderwidth": 1.5,
                    "borderpad": 7,
                }
            )

    printable_points=[]
    for item in selected_plot_points[-8:]:
        try:
            selected_depth=float(item.get("depth")); selected_value=float(item.get("x"))
        except (TypeError, ValueError):
            continue
        if top_depth <= selected_depth <= bottom_depth:
            printable_points.append((selected_depth, selected_value, item))
    printable_points.sort(key=lambda row: row[0])
    for marker_index, (selected_depth, selected_value, item) in enumerate(printable_points):
        shapes.append({
            "type": "line", "xref": "paper", "x0": 0, "x1": 1,
            "yref": "y", "y0": selected_depth, "y1": selected_depth,
            "line": {"color": "#0891b2", "width": 2.4, "dash": "dot"},
            "layer": "above",
        })
        curve_name=str(item.get("curve_name") or "Параметр")
        fluid_label=str(item.get("fluid_label") or "").strip()
        confidence=item.get("fluid_percent")
        text=f"<b>{curve_name}</b><br>{selected_depth:.2f} м · {selected_value:.5g}"
        if fluid_label:
            text += f"<br>{fluid_label}"
            try:
                if confidence not in (None, ""): text += f" · {float(confidence):.0f}%"
            except (TypeError, ValueError):
                pass
        lane=marker_index % 3
        annotations.append({
            "xref": "paper", "x": (0.995, 0.73, 0.47)[lane], "xanchor": "right",
            "yref": "y", "y": selected_depth, "yshift": ((marker_index // 3) % 3 - 1) * 42,
            "text": text, "showarrow": True, "arrowhead": 2, "arrowcolor": "#0891b2",
            "ax": -26, "ay": 0, "font": {"size": 22 if not is_screen else 13, "color": "#0e7490"},
            "bgcolor": "rgba(236,254,255,0.97)", "bordercolor": "#0891b2",
            "borderwidth": 1.5, "borderpad": 6, "align": "left",
        })

    visible_curve_specs = [
        {
            "key": column,
            "label": CURVE_PRINT_SPECS.get(column, {}).get("label", column),
            "description": CURVE_PRINT_SPECS.get(column, {}).get("description", "Расчётная кривая"),
            "color": CURVE_PRINT_SPECS.get(column, {}).get("color", "#334155"),
        }
        for column in plotted_columns
    ]
    visible_fluid_types = []
    for interval in visible_intervals:
        fluid_type = str(interval.fluid_type or "uncertain")
        if fluid_type not in visible_fluid_types:
            visible_fluid_types.append(fluid_type)
    visible_fluid_specs = [
        {
            "key": fluid_type,
            "label": FLUID_PRINT_SPECS.get(fluid_type, {}).get("label", FLUID_PLOT_LABELS.get(fluid_type, fluid_type)),
            "description": FLUID_PRINT_SPECS.get(fluid_type, {}).get("description", "Интерпретированный интервал"),
            "color": FLUID_PRINT_SPECS.get(fluid_type, {}).get("color", str(_interval_style(fluid_type).get("color", "#64748b"))),
        }
        for fluid_type in visible_fluid_types
    ]
    report_meta = {
        "schema": "gas-ratio-pro/report-plot-legend/v1",
        "curves": visible_curve_specs,
        "fluids": visible_fluid_specs,
        "markers": [
            {"symbol": "T", "label": "Кровля", "description": "Верхняя граница интервала"},
            {"symbol": "B", "label": "Подошва", "description": "Нижняя граница интервала"},
            {"symbol": "*", "label": "Приоритет", "description": "Наиболее перспективный интервал"},
        ],
        "depth_range": {"top": top_depth, "base": bottom_depth},
        "statistics": statistics_rows,
        "report_kind": cfg.report_kind,
        "report_title": cfg.report_title or cfg.title,
        "group_index": int(cfg.report_group_index or 0),
        "intervals": [
            {
                "id": f"HC-{idx:03d}",
                "top": min(float(interval.top), float(interval.base)),
                "base": max(float(interval.top), float(interval.base)),
                "thickness": abs(float(interval.base) - float(interval.top)),
                "fluid": FLUID_PLOT_LABELS.get(str(interval.fluid_type), str(interval.fluid_type)),
                "confidence": float(getattr(interval, "confidence_score", 0) or 0),
                "color": FLUID_PRINT_SPECS.get(str(interval.fluid_type), {}).get("color", str(_interval_style(str(interval.fluid_type)).get("color", "#64748b"))),
            }
            for idx, interval in enumerate(visible_intervals, start=1)
        ],
    }

    title_size = track_title_font_size(len(column_titles), profile=profile)
    if not is_screen:
        title_size = max(title_size, 34)
    apply_engineering_layout(
        fig, title={"text": cfg.title, "x": 0.0, "xanchor": "left", "font": {"size": 18 if is_screen else 36}}, height=max(cfg.height, 620 if is_screen else 1800),
        margin={"l": 76 if is_screen else 118, "r": 24 if is_screen else 48, "t": 104 if is_screen else 250, "b": 72 if is_screen else 150}, showlegend=bool(cfg.show_curve_legend),
    )
    fig.update_layout(
        shapes=shapes,
        annotations=annotations,
        meta={"gas_ratio_report_legend": report_meta},
        legend={
            "orientation": "h", "yanchor": "bottom", "y": 1.02,
            "xanchor": "left", "x": 0.02, "font": {"size": 20, "color": "#0f172a"},
            "bgcolor": "rgba(255,255,255,1)", "bordercolor": "#cbd5e1", "borderwidth": 1,
            "itemsizing": "constant", "itemwidth": 42,
        },
        font={"size": 24, "color": "#0f172a"},
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        hovermode="y unified",
    )
    # Subplot titles are the first annotations created by make_subplots.
    # Apply a collision-aware size only to those titles; interval annotations
    # retain their dedicated size and background.
    layout_annotations = list(fig.layout.annotations or ())
    for annotation in layout_annotations[: len(column_titles)]:
        annotation.update(font={"size": title_size, "color": "#0f172a"}, yshift=8 if not is_screen else 4)
    # A professional well-log uses one common depth scale, not a repeated
    # "Глубина, м" title inside every track.
    for subplot_col in range(1, len(column_titles) + 1):
        fig.update_yaxes(title_text="", row=1, col=subplot_col)
    fig.update_yaxes(title_text=DEPTH_AXIS_TITLE, row=1, col=1)
    axis_tick_size = 12 if is_screen else 34
    axis_title_size = 15 if is_screen else 38
    depth_span=max(bottom_depth-top_depth, 1.0)
    major_step = 5.0 if depth_span <= 80 else 10.0 if depth_span <= 180 else 20.0
    fig.update_yaxes(showgrid=True, gridcolor="rgba(51,65,85,0.30)", gridwidth=1.1, dtick=major_step, tick0=float(top_depth), ticks="outside", ticklen=8, tickwidth=1.4, tickcolor="#334155", tickfont={"size": axis_tick_size}, title_font={"size": axis_title_size}, automargin=True, minor={"showgrid": True, "dtick": major_step/5.0, "gridcolor": "rgba(100,116,139,0.16)", "griddash": "dot"})
    fig.update_xaxes(showgrid=True, gridcolor="rgba(100,116,139,0.18)", gridwidth=1, showline=True, linewidth=1.2, linecolor="#475569", mirror=True, tickfont={"size": axis_tick_size}, title_font={"size": axis_title_size}, automargin=True, tickangle=0)
    normalize_trace_style(fig)
    return WellLogPlotResult(fig, plotted_columns, summary, len(visible_intervals))
