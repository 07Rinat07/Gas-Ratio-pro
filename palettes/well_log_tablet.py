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


FLUID_INTERVAL_STYLES: Mapping[str, tuple[str, str]] = {
    "oil": ("#2ca02c", "Нефть"),
    "gas": ("#d62728", "Газ"),
    "condensate": ("#ff9f1c", "Газоконденсат"),
    "gas_oil": ("#bcbd22", "Газ–нефть"),
    "oil_gas": ("#bcbd22", "Нефть–газ"),
    "mixed": ("#9467bd", "Смешанный"),
    "transition": ("#f2c94c", "Переходный"),
    "water": ("#1f77b4", "Вода"),
    "dry_gas": ("#7b2cbf", "Сухой газ"),
    "uncertain": ("#7f8c8d", "Требует проверки"),
}


MUD_GAS_LITERATURE_TRACK_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("GR/lithology", ("gr", "gamma", "gamma_ray", "lithology")),
    ("Total gas", ("total_gas", "tgas", "gas_total", "totalgas", "gas")),
    ("C1 methane", ("c1", "methane")),
    ("C2 ethane", ("c2", "ethane")),
    ("C3 propane", ("c3", "propane")),
    ("iC4", ("ic4", "i_c4", "iso_c4", "isobutane")),
    ("nC4", ("nc4", "n_c4", "normal_c4", "n-butane", "nbutane")),
    ("iC5", ("ic5", "i_c5", "iso_c5", "isopentane")),
    ("nC5", ("nc5", "n_c5", "normal_c5", "n-pentane", "npentane")),
    ("Wh", ("wh", "wetness")),
    ("Bh", ("bh", "balance")),
    ("Ch", ("ch", "character")),
    ("C1/C2", ("c1_c2", "c1/c2", "c1c2")),
    ("C1/C3", ("c1_c3", "c1/c3", "c1c3")),
    ("C1/C4", ("c1_c4", "c1/sumc4", "c1_sumc4", "c1c4")),
    ("C1/C5", ("c1_c5", "c1/sumc5", "c1_sumc5", "c1c5")),
    ("Inverse oil indicator", ("inverse_oil_indicator", "ioi", "c1_heavy", "c1_over_heavy")),
    ("Deep resistivity", ("rdeep", "rt", "lld", "resdeep", "deep_resistivity")),
    ("Shallow resistivity", ("rshallow", "rs", "lls", "resshallow", "shallow_resistivity")),
    ("Density", ("rhob", "density", "den")),
    ("Neutron porosity", ("nphi", "neutron", "neutron_porosity")),
)

MUD_GAS_MARKER_COLUMN_ALIASES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("TG", ("total_gas", "tgas", "gas_total", "totalgas", "gas"), "Максимум total gas: проверить hydrocarbon-bearing interval по ГИС и буровому контексту."),
    ("Wh", ("wh", "wetness"), "Максимум Wh/wetness: проверить возможное обогащение тяжелыми компонентами."),
    ("C1/C2", ("c1_c2", "c1/c2", "c1c2"), "Минимум C1/C2: по Pixler может быть связан с более тяжелым флюидом; требуется сверка."),
    ("IOI", ("inverse_oil_indicator", "ioi", "c1_heavy", "c1_over_heavy"), "Максимум inverse oil indicator: справочный индикатор, не использовать без проверки."),
)
TABLET_FILL_MODES = {"none", "to_zero", "to_left", "to_right"}


def _is_column_sequence(value: object) -> bool:
    """Return True for plain column-name containers passed by LAS Editor helpers."""

    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray, pd.DataFrame))


def _column_sequence(value: object) -> tuple[str, ...]:
    """Normalize a DataFrame/Index/list/tuple of columns into display-safe names."""

    if value is None:
        return ()
    if isinstance(value, pd.DataFrame):
        return tuple(str(column) for column in value.columns)
    if hasattr(value, "tolist") and not hasattr(value, "empty"):
        try:
            return tuple(str(column) for column in value.tolist())
        except TypeError:
            return ()
    if _is_column_sequence(value):
        return tuple(str(column) for column in value)
    return ()


MUD_GAS_LITERATURE_TRACK_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("GR/lithology", ("gr", "gamma", "gamma_ray", "lithology")),
    ("Total gas", ("total_gas", "tgas", "gas_total", "totalgas", "gas")),
    ("C1 methane", ("c1", "methane")),
    ("C2 ethane", ("c2", "ethane")),
    ("C3 propane", ("c3", "propane")),
    ("iC4", ("ic4", "i_c4", "iso_c4", "isobutane")),
    ("nC4", ("nc4", "n_c4", "normal_c4", "n-butane", "nbutane")),
    ("iC5", ("ic5", "i_c5", "iso_c5", "isopentane")),
    ("nC5", ("nc5", "n_c5", "normal_c5", "n-pentane", "npentane")),
    ("Wh", ("wh", "wetness")),
    ("Bh", ("bh", "balance")),
    ("Ch", ("ch", "character")),
    ("C1/C2", ("c1_c2", "c1/c2", "c1c2")),
    ("C1/C3", ("c1_c3", "c1/c3", "c1c3")),
    ("C1/C4", ("c1_c4", "c1/sumc4", "c1_sumc4", "c1c4")),
    ("C1/C5", ("c1_c5", "c1/sumc5", "c1_sumc5", "c1c5")),
    ("Inverse oil indicator", ("inverse_oil_indicator", "ioi", "c1_heavy", "c1_over_heavy")),
    ("Deep resistivity", ("rdeep", "rt", "lld", "resdeep", "deep_resistivity")),
    ("Shallow resistivity", ("rshallow", "rs", "lls", "resshallow", "shallow_resistivity")),
    ("Density", ("rhob", "density", "den")),
    ("Neutron porosity", ("nphi", "neutron", "neutron_porosity")),
)

MUD_GAS_MARKER_COLUMN_ALIASES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("TG", ("total_gas", "tgas", "gas_total", "totalgas", "gas"), "Максимум total gas: проверить hydrocarbon-bearing interval по ГИС и буровому контексту."),
    ("Wh", ("wh", "wetness"), "Максимум Wh/wetness: проверить возможное обогащение тяжелыми компонентами."),
    ("C1/C2", ("c1_c2", "c1/c2", "c1c2"), "Минимум C1/C2: по Pixler может быть связан с более тяжелым флюидом; требуется сверка."),
    ("IOI", ("inverse_oil_indicator", "ioi", "c1_heavy", "c1_over_heavy"), "Максимум inverse oil indicator: справочный индикатор, не использовать без проверки."),
)


@dataclass(frozen=True)
class TabletTrackConfig:
    column: str
    label: str | None = None
    unit: str | None = None
    color: str | None = None
    x_range: tuple[float, float] | None = None
    fill: bool = False
    fill_mode: str = "none"


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


@dataclass(frozen=True)
class ReservoirIntervalOverlay:
    interval_id: str
    top_depth: float
    bottom_depth: float
    fluid_type: str
    confidence_score: int = 0
    thickness: float = 0.0
    decision_level: str = ""
    note: str = ""
    recommendation: str = ""


def _interval_recommendation(interval: object) -> str:
    """Return one concise engineer-facing action for an interval overlay."""

    explanation = getattr(interval, "explanation", None)
    recommendations = getattr(explanation, "recommendations", ()) if explanation is not None else ()
    for recommendation in recommendations or ():
        text = str(recommendation or "").strip()
        if text:
            return text

    structured = getattr(explanation, "structured_recommendations", ()) if explanation is not None else ()
    for recommendation in structured or ():
        text = str(getattr(recommendation, "action", "") or "").strip()
        if text:
            return text

    for trace in getattr(interval, "rule_traces", ()) or ():
        text = str(getattr(trace, "recommendation", "") or "").strip()
        if text:
            return text

    decision_level = str(getattr(interval, "decision_level", "") or "").lower()
    confidence = int(getattr(interval, "confidence_score", 0) or 0)
    if decision_level == "high" or confidence >= 80:
        return "Приоритетно сопоставить с ГИС, литологией и результатами испытаний."
    if decision_level == "medium" or confidence >= 60:
        return "Проверить по соседним глубинам, ГИС и качеству исходных газовых данных."
    return "Требуется ручная проверка данных и подтверждение независимыми методами."


def reservoir_interval_overlays(intervals: Sequence[object]) -> tuple[ReservoirIntervalOverlay, ...]:
    """Convert HydrocarbonInterval-like objects into UI-safe interval overlays."""

    overlays: list[ReservoirIntervalOverlay] = []
    for index, interval in enumerate(intervals, start=1):
        try:
            top = float(getattr(interval, "top"))
            base = float(getattr(interval, "base"))
        except (TypeError, ValueError, AttributeError):
            continue
        fluid_type = str(getattr(interval, "fluid_type", "uncertain") or "uncertain")
        confidence = int(getattr(interval, "confidence_score", 0) or 0)
        thickness = float(getattr(interval, "thickness", abs(base - top)) or abs(base - top))
        overlays.append(
            ReservoirIntervalOverlay(
                interval_id=f"HC-{index:03d}",
                top_depth=min(top, base),
                bottom_depth=max(top, base),
                fluid_type=fluid_type,
                confidence_score=confidence,
                thickness=thickness,
                decision_level=str(getattr(interval, "decision_level", "") or ""),
                note=str(getattr(interval, "engineering_note", "") or ""),
                recommendation=_interval_recommendation(interval),
            )
        )
    return tuple(overlays)


def numeric_tablet_columns(df: pd.DataFrame | Sequence[object]) -> tuple[str, ...]:
    """Return numeric tablet columns or safe column names from lightweight lists.

    LAS Editor reference builders sometimes call this module with only column
    names instead of a prepared DataFrame. In that case we cannot validate
    numeric values, so we return non-depth column names instead of touching
    DataFrame-only attributes such as ``.empty`` or ``.columns``.
    """

    if df is None:
        return ()
    if isinstance(df, pd.DataFrame):
        if df.empty:
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

    columns = []
    for column_name in _column_sequence(df):
        if column_name in DEPTH_COLUMN_NAMES or column_name.startswith("_"):
            continue
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


def _canonical_column_token(column: object) -> str:
    """Normalize LAS/Excel mnemonic variants for preset matching."""

    return "".join(char for char in str(column).lower() if char.isalnum())


def _column_lookup_by_alias(df: pd.DataFrame | Sequence[object]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for column in numeric_tablet_columns(df):
        token = _canonical_column_token(column)
        if token and token not in lookup:
            lookup[token] = str(column)
    return lookup


def mud_gas_literature_tablet_columns(df: pd.DataFrame | Sequence[object], *, limit: int | None = None) -> tuple[str, ...]:
    """Return available tablet tracks in the order recommended by mud-gas literature.

    The preset follows ``docs/mud_gas_analysis_literature.md``: GR/lithology,
    total gas, chromatograph components, Haworth ratios, Pixler ratios, inverse
    oil indicator and common supporting GIS curves. Missing columns are skipped
    rather than synthesized, because the renderer must not hide absent data from
    the engineer.
    """

    if df is None:
        return ()

    lookup = _column_lookup_by_alias(df)
    if not lookup:
        return ()
    selected: list[str] = []
    for _label, aliases in MUD_GAS_LITERATURE_TRACK_ALIASES:
        for alias in aliases:
            match = lookup.get(_canonical_column_token(alias))
            if match is not None and match not in selected:
                selected.append(match)
                break
        if limit is not None and len(selected) >= limit:
            break
    return tuple(selected)


def _nearest_depth_for_extreme(df: pd.DataFrame, column: str, *, mode: str) -> float | None:
    plot_df = df.copy()
    plot_df["_plot_depth"] = _depth_axis(plot_df)
    values = pd.to_numeric(plot_df[column], errors="coerce")
    candidates = plot_df.loc[values.notna() & plot_df["_plot_depth"].notna()].copy()
    if candidates.empty:
        return None
    candidate_values = pd.to_numeric(candidates[column], errors="coerce")
    index = candidate_values.idxmin() if mode == "min" else candidate_values.idxmax()
    return float(candidates.loc[index, "_plot_depth"])


def mud_gas_literature_markers(df: pd.DataFrame, *, max_markers: int = 4) -> tuple[InterpretationMarker, ...]:
    """Suggest safe literature-based depth markers for the tablet.

    Markers are deliberately descriptive, not deterministic interpretation. They
    point the engineer to total-gas peaks, wetness peaks and Pixler/oil-indicator
    anomalies that should be checked together with logs, lithology and drilling
    context.
    """

    if df is None or df.empty or max_markers <= 0:
        return ()

    lookup = _column_lookup_by_alias(df)
    markers: list[InterpretationMarker] = []
    used_depths: list[float] = []
    for label, aliases, note in MUD_GAS_MARKER_COLUMN_ALIASES:
        column = None
        for alias in aliases:
            column = lookup.get(_canonical_column_token(alias))
            if column is not None:
                break
        if column is None:
            continue
        mode = "min" if label == "C1/C2" else "max"
        depth = _nearest_depth_for_extreme(df, column, mode=mode)
        if depth is None:
            continue
        if any(abs(depth - existing) < 1e-9 for existing in used_depths):
            continue
        markers.append(InterpretationMarker(label=label, depth=depth, note=note))
        used_depths.append(depth)
        if len(markers) >= max_markers:
            break
    return tuple(markers)


def _canonical_column_token(column: object) -> str:
    """Normalize LAS/Excel mnemonic variants for preset matching."""

    return "".join(char for char in str(column).lower() if char.isalnum())


def _column_lookup_by_alias(df: pd.DataFrame | Sequence[object]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for column in numeric_tablet_columns(df):
        token = _canonical_column_token(column)
        if token and token not in lookup:
            lookup[token] = str(column)
    return lookup


def mud_gas_literature_tablet_columns(df: pd.DataFrame | Sequence[object], *, limit: int | None = None) -> tuple[str, ...]:
    """Return available tablet tracks in the order recommended by mud-gas literature.

    The preset follows ``docs/mud_gas_analysis_literature.md``: GR/lithology,
    total gas, chromatograph components, Haworth ratios, Pixler ratios, inverse
    oil indicator and common supporting GIS curves. Missing columns are skipped
    rather than synthesized, because the renderer must not hide absent data from
    the engineer.
    """

    if df is None:
        return ()

    lookup = _column_lookup_by_alias(df)
    if not lookup:
        return ()
    selected: list[str] = []
    for _label, aliases in MUD_GAS_LITERATURE_TRACK_ALIASES:
        for alias in aliases:
            match = lookup.get(_canonical_column_token(alias))
            if match is not None and match not in selected:
                selected.append(match)
                break
        if limit is not None and len(selected) >= limit:
            break
    return tuple(selected)


def _nearest_depth_for_extreme(df: pd.DataFrame, column: str, *, mode: str) -> float | None:
    plot_df = df.copy()
    plot_df["_plot_depth"] = _depth_axis(plot_df)
    values = pd.to_numeric(plot_df[column], errors="coerce")
    candidates = plot_df.loc[values.notna() & plot_df["_plot_depth"].notna()].copy()
    if candidates.empty:
        return None
    candidate_values = pd.to_numeric(candidates[column], errors="coerce")
    index = candidate_values.idxmin() if mode == "min" else candidate_values.idxmax()
    return float(candidates.loc[index, "_plot_depth"])


def mud_gas_literature_markers(df: pd.DataFrame, *, max_markers: int = 4) -> tuple[InterpretationMarker, ...]:
    """Suggest safe literature-based depth markers for the tablet.

    Markers are deliberately descriptive, not deterministic interpretation. They
    point the engineer to total-gas peaks, wetness peaks and Pixler/oil-indicator
    anomalies that should be checked together with logs, lithology and drilling
    context.
    """

    if df is None or df.empty or max_markers <= 0:
        return ()

    lookup = _column_lookup_by_alias(df)
    markers: list[InterpretationMarker] = []
    used_depths: list[float] = []
    for label, aliases, note in MUD_GAS_MARKER_COLUMN_ALIASES:
        column = None
        for alias in aliases:
            column = lookup.get(_canonical_column_token(alias))
            if column is not None:
                break
        if column is None:
            continue
        mode = "min" if label == "C1/C2" else "max"
        depth = _nearest_depth_for_extreme(df, column, mode=mode)
        if depth is None:
            continue
        if any(abs(depth - existing) < 1e-9 for existing in used_depths):
            continue
        markers.append(InterpretationMarker(label=label, depth=depth, note=note))
        used_depths.append(depth)
        if len(markers) >= max_markers:
            break
    return tuple(markers)


def normalize_track_configs(
    columns: Sequence[str],
    *,
    x_ranges: Mapping[str, tuple[float, float] | None] | None = None,
    units: Mapping[str, str | None] | None = None,
    colors: Mapping[str, str | None] | None = None,
    fill: bool = False,
    fill_modes: Mapping[str, str | None] | None = None,
) -> tuple[TabletTrackConfig, ...]:
    """Build ordered tablet track configs from UI/project settings.

    The order of ``columns`` is preserved, because a printed log tablet is read
    left-to-right exactly as the engineer arranged the tracks in the UI.
    ``units`` and ``colors`` are optional maps keyed by dataframe column name.
    """

    ranges = x_ranges or {}
    unit_map = units or {}
    color_map = colors or {}
    fill_mode_map = fill_modes or {}
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
                fill_mode=normalize_tablet_fill_mode(fill_mode_map.get(column_name), legacy_fill=fill),
            )
        )
    return tuple(configs)


def normalize_tablet_fill_mode(value: str | None, *, legacy_fill: bool = False) -> str:
    """Normalize per-track tablet fill mode.

    ``legacy_fill`` keeps old saved projects compatible: if a project only has
    the former boolean fill flag, tracks still render as fill-to-zero. New
    projects can store an explicit mode per parameter.
    """

    normalized = str(value or "").strip().lower()
    aliases = {
        "": "to_zero" if legacy_fill else "none",
        "false": "none",
        "no": "none",
        "none": "none",
        "line": "none",
        "true": "to_zero",
        "zero": "to_zero",
        "to_zero": "to_zero",
        "tozerox": "to_zero",
        "left": "to_left",
        "to_left": "to_left",
        "right": "to_right",
        "to_right": "to_right",
    }
    mode = aliases.get(normalized, normalized)
    return mode if mode in TABLET_FILL_MODES else ("to_zero" if legacy_fill else "none")


def tablet_fill_mode_label(mode: str | None) -> str:
    labels = {
        "none": "line",
        "to_zero": "fill to zero",
        "to_left": "fill to left scale",
        "to_right": "fill to right scale",
    }
    return labels.get(normalize_tablet_fill_mode(mode), "line")


def _hex_to_rgba(color: str, opacity: float) -> str:
    text = str(color or "#111111").strip()
    if text.startswith("#") and len(text) == 7:
        try:
            red = int(text[1:3], 16)
            green = int(text[3:5], 16)
            blue = int(text[5:7], 16)
            return f"rgba({red},{green},{blue},{max(0.0, min(1.0, opacity))})"
        except ValueError:
            pass
    return f"rgba(17,17,17,{max(0.0, min(1.0, opacity))})"


def _fill_baseline(values: pd.Series, track: TabletTrackConfig, mode: str) -> float | None:
    if mode == "none":
        return None
    if mode == "to_zero":
        return 0.0
    if track.x_range is not None:
        return float(track.x_range[0] if mode == "to_left" else track.x_range[1])
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    return float(numeric.min() if mode == "to_left" else numeric.max())


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
    fill_label = tablet_fill_mode_label(track.fill_mode if track.fill_mode else ("to_zero" if track.fill else "none"))
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




def _visible_depth_bounds(
    depth: pd.Series,
    depth_range: tuple[float, float] | None,
) -> tuple[float, float]:
    """Return normalized visible top/base depth for collision calculations."""

    if depth_range is not None:
        top, base = (float(depth_range[0]), float(depth_range[1]))
    else:
        numeric = pd.to_numeric(depth, errors="coerce").dropna()
        if numeric.empty:
            return 0.0, 1.0
        top, base = float(numeric.min()), float(numeric.max())
    if top > base:
        top, base = base, top
    if top == base:
        base = top + 1.0
    return top, base


def _interval_pixel_height(
    top_depth: float,
    bottom_depth: float,
    *,
    visible_top: float,
    visible_bottom: float,
    plot_height: int,
) -> float:
    """Estimate interval height in screen pixels for label suppression."""

    span = max(float(visible_bottom) - float(visible_top), 1e-9)
    usable_height = max(int(plot_height) - 185, 220)
    clipped_top = max(float(visible_top), min(float(top_depth), float(bottom_depth)))
    clipped_bottom = min(float(visible_bottom), max(float(top_depth), float(bottom_depth)))
    visible_thickness = max(0.0, clipped_bottom - clipped_top)
    return visible_thickness / span * usable_height


def _select_non_overlapping_intervals(
    intervals: Sequence[ReservoirIntervalOverlay],
    *,
    visible_top: float,
    visible_bottom: float,
    plot_height: int,
    selected_depth: float | None,
    minimum_label_pixels: float = 24.0,
    minimum_spacing_pixels: float = 18.0,
) -> tuple[set[str], set[str], str | None]:
    """Choose labels/markers that remain readable at the current depth scale.

    Plotly does not perform annotation collision detection. This helper keeps
    selected and sufficiently thick intervals, then greedily suppresses labels
    whose midpoints would collide on screen.
    """

    span = max(float(visible_bottom) - float(visible_top), 1e-9)
    usable_height = max(int(plot_height) - 185, 220)
    selected_id: str | None = None
    if selected_depth is not None:
        for interval in intervals:
            top = min(float(interval.top_depth), float(interval.bottom_depth))
            base = max(float(interval.top_depth), float(interval.bottom_depth))
            if top <= float(selected_depth) <= base:
                selected_id = interval.interval_id
                break

    candidates: list[tuple[float, float, ReservoirIntervalOverlay]] = []
    marker_candidates: list[tuple[float, ReservoirIntervalOverlay]] = []
    for interval in intervals:
        top = min(float(interval.top_depth), float(interval.bottom_depth))
        base = max(float(interval.top_depth), float(interval.bottom_depth))
        if base < visible_top or top > visible_bottom:
            continue
        midpoint = (top + base) / 2.0
        px_height = _interval_pixel_height(
            top,
            base,
            visible_top=visible_top,
            visible_bottom=visible_bottom,
            plot_height=plot_height,
        )
        marker_candidates.append((midpoint, interval))
        if px_height >= minimum_label_pixels or interval.interval_id == selected_id:
            candidates.append((midpoint, px_height, interval))

    def midpoint_to_px(midpoint: float) -> float:
        return (float(midpoint) - visible_top) / span * usable_height

    label_ids: set[str] = set()
    last_px: float | None = None
    for midpoint, _height, interval in sorted(candidates, key=lambda item: item[0]):
        current_px = midpoint_to_px(midpoint)
        force = interval.interval_id == selected_id
        if force or last_px is None or abs(current_px - last_px) >= minimum_spacing_pixels:
            label_ids.add(interval.interval_id)
            last_px = current_px

    # Recommendation/QC markers can be denser than text, but still need spacing.
    marker_ids: set[str] = set()
    last_marker_px: float | None = None
    for midpoint, interval in sorted(marker_candidates, key=lambda item: item[0]):
        current_px = midpoint_to_px(midpoint)
        force = interval.interval_id == selected_id
        if force or last_marker_px is None or abs(current_px - last_marker_px) >= 10.0:
            marker_ids.add(interval.interval_id)
            last_marker_px = current_px

    return label_ids, marker_ids, selected_id

def build_well_log_tablet(
    df: pd.DataFrame,
    tracks: Sequence[TabletTrackConfig],
    *,
    depth_range: tuple[float, float] | None = None,
    markers: Sequence[InterpretationMarker] = (),
    zones: Sequence[InterpretationZone] = (),
    reservoir_intervals: Sequence[ReservoirIntervalOverlay] = (),
    selected_depth: float | None = None,
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
    visible_top, visible_bottom = _visible_depth_bounds(depth, depth_range)
    label_interval_ids, marker_interval_ids, selected_interval_id = _select_non_overlapping_intervals(
        reservoir_intervals,
        visible_top=visible_top,
        visible_bottom=visible_bottom,
        plot_height=height,
        selected_depth=selected_depth,
    )
    engineering_tracks_enabled = bool(reservoir_intervals)
    engineering_titles = ["Тип пласта", "Достоверность", "Рекомендации"] if engineering_tracks_enabled else []
    titles = engineering_titles + [_track_title(track, plot_df[track.column]) for track in selected_tracks]
    # Engineering columns need enough width for a compact identity, a confidence bar
    # and a QC marker. Long recommendations are intentionally moved to hover text.
    widths = ([0.54, 0.38, 0.28] if engineering_tracks_enabled else []) + [1.0] * len(selected_tracks)
    fig = make_subplots(
        rows=1,
        cols=len(titles),
        shared_yaxes=True,
        horizontal_spacing=0.012,
        subplot_titles=titles,
        column_widths=widths,
    )

    track_offset = 3 if engineering_tracks_enabled else 0
    if engineering_tracks_enabled:
        for engineering_col in range(1, 4):
            fig.add_trace(
                go.Scatter(
                    x=[0.5, 0.5],
                    y=[float(depth.min()), float(depth.max())],
                    mode="lines",
                    line={"color": "rgba(0,0,0,0)", "width": 0},
                    hoverinfo="skip",
                    showlegend=False,
                ),
                row=1,
                col=engineering_col,
            )
            fig.update_xaxes(range=[0, 1], showticklabels=False, zeroline=False, row=1, col=engineering_col)

    visible_track_count = 0
    for index, track in enumerate(selected_tracks, start=1):
        subplot_col = index + track_offset
        values = pd.to_numeric(plot_df[track.column], errors="coerce")
        if values.isna().all():
            continue

        color = track.color or DEFAULT_TABLET_COLORS[(index - 1) % len(DEFAULT_TABLET_COLORS)]
        fill_mode = normalize_tablet_fill_mode(track.fill_mode, legacy_fill=track.fill)
        baseline = _fill_baseline(values, track, fill_mode)
        fill = None
        if baseline is not None:
            fig.add_trace(
                go.Scatter(
                    x=[baseline] * len(depth),
                    y=depth,
                    mode="lines",
                    line={"color": "rgba(0,0,0,0)", "width": 0},
                    hoverinfo="skip",
                    showlegend=False,
                ),
                row=1,
                col=subplot_col,
            )
            fill = "tonextx"

        fig.add_trace(
            go.Scatter(
                x=values,
                y=depth,
                mode="lines",
                name=track.label or track.column,
                line={"color": color, "width": 1.6},
                fill=fill,
                fillcolor=_hex_to_rgba(color, 0.18),
                hovertemplate=f"{track.column}=%{{x}}<br>Depth=%{{y}}<extra></extra>",
            ),
            row=1,
            col=subplot_col,
        )
        visible_track_count += 1
        fig.update_xaxes(title_text=track.column, zeroline=False, row=1, col=subplot_col)
        if track.x_range is not None:
            fig.update_xaxes(range=list(track.x_range), row=1, col=subplot_col)

    if visible_track_count == 0:
        return _empty_tablet_figure("В выбранных параметрах нет числовых значений", height=height)

    yaxis_options = {"title": "Depth", "autorange": "reversed"}
    if depth_range is not None:
        top_depth, bottom_depth = depth_range
        yaxis_options["range"] = [bottom_depth, top_depth]
        yaxis_options["autorange"] = False
    fig.update_yaxes(**yaxis_options)
    # Shared y-axes otherwise repeat the word "Depth" inside every track.
    for subplot_col in range(1, len(titles) + 1):
        fig.update_yaxes(title_text="", row=1, col=subplot_col)
    fig.update_yaxes(title_text="Глубина, м", row=1, col=1)

    shapes = []
    annotations = []
    recommendation_points: list[dict[str, object]] = []
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

    for interval in reservoir_intervals:
        top_depth = min(float(interval.top_depth), float(interval.bottom_depth))
        bottom_depth = max(float(interval.top_depth), float(interval.bottom_depth))
        if bottom_depth < visible_top or top_depth > visible_bottom:
            continue
        color, fluid_label = FLUID_INTERVAL_STYLES.get(
            str(interval.fluid_type).lower(), FLUID_INTERVAL_STYLES["uncertain"]
        )
        is_selected = interval.interval_id == selected_interval_id
        show_label = interval.interval_id in label_interval_ids
        show_marker = interval.interval_id in marker_interval_ids
        midpoint = (top_depth + bottom_depth) / 2.0

        # Keep all intervals discoverable as subtle bands, but reserve strong
        # borders and text for the selected/readable intervals. This prevents
        # hundreds of top/base lines from turning the panel into dotted noise.
        shapes.append(
            {
                "type": "rect",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": top_depth,
                "y1": bottom_depth,
                "fillcolor": color,
                "opacity": 0.16 if is_selected else 0.045,
                "line": {"color": color, "width": 1.8 if is_selected else 0},
                "layer": "below",
            }
        )

        if engineering_tracks_enabled:
            # Reservoir type track. Thin intervals retain their color block and
            # hover identity, while permanent text is collision-suppressed.
            shapes.append(
                {
                    "type": "rect",
                    "xref": "x",
                    "x0": 0.06,
                    "x1": 0.94,
                    "yref": "y",
                    "y0": top_depth,
                    "y1": bottom_depth,
                    "fillcolor": color,
                    "opacity": 0.95 if is_selected else 0.72,
                    "line": {"color": "#ffffff" if is_selected else color, "width": 1.8 if is_selected else 0.5},
                    "layer": "above",
                }
            )
            if show_label:
                annotations.append(
                    {
                        "xref": "x",
                        "x": 0.5,
                        "yref": "y",
                        "y": midpoint,
                        "text": f"<b>{interval.interval_id}</b><br>{fluid_label}<br>{interval.thickness:g} м",
                        "showarrow": False,
                        "align": "center",
                        "font": {"color": "#ffffff", "size": 10 if is_selected else 9},
                    }
                )

            # Confidence track: bar remains visible for all intervals, text only
            # where there is enough vertical room.
            confidence_fraction = max(0.0, min(float(interval.confidence_score) / 100.0, 1.0))
            confidence_color = (
                "#2ca02c" if interval.confidence_score >= 80
                else ("#f2c94c" if interval.confidence_score >= 60 else "#e63946")
            )
            shapes.append(
                {
                    "type": "rect",
                    "xref": "x2",
                    "x0": 0.08,
                    "x1": 0.92,
                    "yref": "y",
                    "y0": top_depth,
                    "y1": bottom_depth,
                    "fillcolor": "#344054",
                    "opacity": 0.45,
                    "line": {"width": 0},
                    "layer": "above",
                }
            )
            shapes.append(
                {
                    "type": "rect",
                    "xref": "x2",
                    "x0": 0.08,
                    "x1": 0.08 + 0.84 * confidence_fraction,
                    "yref": "y",
                    "y0": top_depth,
                    "y1": bottom_depth,
                    "fillcolor": confidence_color,
                    "opacity": 0.92,
                    "line": {"width": 0},
                    "layer": "above",
                }
            )
            if show_label:
                annotations.append(
                    {
                        "xref": "x2",
                        "x": 0.5,
                        "yref": "y",
                        "y": midpoint,
                        "text": f"<b>{interval.confidence_score}%</b>",
                        "showarrow": False,
                        "align": "center",
                        "font": {"color": "#ffffff", "size": 10},
                    }
                )

            # Recommendations are represented by compact QC markers. The full
            # engineer-facing action remains available in hover text.
            if show_marker:
                recommendation = str(
                    interval.recommendation or interval.note or "Требуется инженерная проверка."
                ).strip()
                if interval.confidence_score >= 80:
                    symbol, marker_color, status = "circle", "#2ca02c", "Сопоставить и подтвердить"
                elif interval.confidence_score >= 60:
                    symbol, marker_color, status = "diamond", "#f2c94c", "Проверить дополнительно"
                else:
                    symbol, marker_color, status = "x", "#e63946", "Требует проверки"
                recommendation_points.append(
                    {
                        "depth": midpoint,
                        "symbol": symbol,
                        "color": marker_color,
                        "status": status,
                        "hover": (
                            f"<b>{interval.interval_id}</b><br>{fluid_label}<br>"
                            f"{top_depth:g}–{bottom_depth:g} м · {interval.thickness:g} м<br>"
                            f"Достоверность: {interval.confidence_score}%<br>{recommendation}"
                        ),
                    }
                )

        # Draw top/base boundaries only for the selected interval and intervals
        # that are large enough to carry a permanent label.
        if is_selected or show_label:
            for boundary in (top_depth, bottom_depth):
                shapes.append(
                    {
                        "type": "line",
                        "xref": "paper",
                        "x0": 0,
                        "x1": 1,
                        "yref": "y",
                        "y0": boundary,
                        "y1": boundary,
                        "line": {
                            "color": "#ffffff" if is_selected else color,
                            "width": 1.5 if is_selected else 0.8,
                            "dash": "dash" if is_selected else "dot",
                        },
                    }
                )

    if engineering_tracks_enabled and recommendation_points:
        fig.add_trace(
            go.Scatter(
                x=[0.5] * len(recommendation_points),
                y=[point["depth"] for point in recommendation_points],
                mode="markers",
                marker={
                    "size": 9,
                    "symbol": [point["symbol"] for point in recommendation_points],
                    "color": [point["color"] for point in recommendation_points],
                    "line": {"color": "#ffffff", "width": 0.8},
                },
                customdata=[point["hover"] for point in recommendation_points],
                hovertemplate="%{customdata}<extra></extra>",
                showlegend=False,
                name="QC",
            ),
            row=1,
            col=3,
        )
    if selected_depth is not None:
        shapes.append(
            {
                "type": "line",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": float(selected_depth),
                "y1": float(selected_depth),
                "line": {"color": "#00d4ff", "width": 2.0},
            }
        )
        annotations.append(
            {
                "xref": "paper",
                "x": 1.01,
                "yref": "y",
                "y": float(selected_depth),
                "text": f"Выбрано: {float(selected_depth):g} м",
                "showarrow": True,
                "arrowhead": 2,
                "ax": 58,
                "ay": 0,
                "font": {"color": "#00d4ff", "size": 11},
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
        title="Depth Panel 2.0 — интервалы, достоверность, QC и кривые",
        height=height,
        margin={"l": 82, "r": 86, "t": 122, "b": 54},
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
