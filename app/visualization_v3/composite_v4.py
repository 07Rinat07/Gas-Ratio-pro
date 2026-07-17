from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

import pandas as pd

from .composite_engine import CompositeLogEngine, CompositeLogResult
from .models import CompositeLogSpec, CurveTrackSpec, IntervalBand, DepthTrackSpec

# Calm, stable engineering palette. Each curve keeps the same identity on screen and in print.
TRACK_LIBRARY: tuple[tuple[str, str, str, str, str], ...] = (
    ("tgas", "TGAS", "%", "#d73027", "linear"),
    ("c1", "C1", "%", "#00897b", "linear"),
    ("c2", "C2", "%", "#2878b5", "linear"),
    ("c3", "C3", "%", "#7b61a8", "linear"),
    ("ic4", "iC4", "%", "#e69100", "linear"),
    ("nc4", "nC4", "%", "#00a6b2", "linear"),
    ("ic5", "iC5", "%", "#d45087", "linear"),
    ("nc5", "nC5", "%", "#c47f6a", "linear"),
    ("wh", "Wh", "", "#2e8b57", "linear"),
    ("bh", "Bh", "", "#1874a8", "linear"),
    ("ch", "Ch", "", "#c83e4d", "linear"),
    ("c1_c2", "C1/C2", "", "#7cb342", "linear"),
    ("c1_c3", "C1/C3", "", "#c653c6", "linear"),
    ("c1_c4", "C1/C4", "", "#e39b22", "linear"),
    ("c1_c5", "C1/C5", "", "#22a7d6", "linear"),
    ("inverse_oil_indicator", "Oil Index", "", "#d98e04", "linear"),
    ("bar2", "Bar-2", "", "#6e9b35", "linear"),
)

TRACK_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "ru": {
        "tgas": "Суммарный газ", "c1": "Метан", "c2": "Этан", "c3": "Пропан",
        "ic4": "Изобутан", "nc4": "Н-бутан", "ic5": "Изопентан", "nc5": "Н-пентан",
        "wh": "Влажность газа", "bh": "Баланс компонентов", "ch": "Характер газа",
        "c1_c2": "Метан / этан", "c1_c3": "Метан / пропан",
        "c1_c4": "Метан / бутаны", "c1_c5": "Метан / пентаны",
        "inverse_oil_indicator": "Нефтяной индекс", "bar2": "Коэффициент Bar-2",
    },
    "kk": {
        "tgas": "Жалпы газ", "c1": "Метан", "c2": "Этан", "c3": "Пропан",
        "ic4": "Изобутан", "nc4": "Н-бутан", "ic5": "Изопентан", "nc5": "Н-пентан",
        "wh": "Газ ылғалдылығы", "bh": "Компоненттер теңгерімі", "ch": "Газ сипаты",
        "c1_c2": "Метан / этан", "c1_c3": "Метан / пропан",
        "c1_c4": "Метан / бутандар", "c1_c5": "Метан / пентандар",
        "inverse_oil_indicator": "Мұнай индексі", "bar2": "Bar-2 коэффициенті",
    },
    "en": {
        "tgas": "Total gas", "c1": "Methane", "c2": "Ethane", "c3": "Propane",
        "ic4": "Isobutane", "nc4": "n-Butane", "ic5": "Isopentane", "nc5": "n-Pentane",
        "wh": "Gas wetness", "bh": "Component balance", "ch": "Gas character",
        "c1_c2": "Methane / ethane", "c1_c3": "Methane / propane",
        "c1_c4": "Methane / butanes", "c1_c5": "Methane / pentanes",
        "inverse_oil_indicator": "Oil index", "bar2": "Bar-2 ratio",
    },
}

COMPOSITE_TEXT: dict[str, dict[str, str]] = {
    "ru": {
        "depth": "Глубина", "metre": "м",
        "working_range": "Рабочий диапазон: {top:g}–{base:g} м · автоматически по значимым газовым данным и УВ-интервалам",
        "gas": "Газ", "condensate": "Газоконденсат", "oil": "Нефть", "other": "Переходная/прочее",
    },
    "kk": {
        "depth": "Тереңдік", "metre": "м",
        "working_range": "Жұмыс аралығы: {top:g}–{base:g} м · маңызды газ деректері мен КС аралықтары бойынша автоматты түрде",
        "gas": "Газ", "condensate": "Газконденсат", "oil": "Мұнай", "other": "Өтпелі/басқа",
    },
    "en": {
        "depth": "Depth", "metre": "m",
        "working_range": "Working range: {top:g}–{base:g} m · automatically derived from significant gas data and HC intervals",
        "gas": "Gas", "condensate": "Gas condensate", "oil": "Oil", "other": "Transition/other",
    },
}

def _locale(value: str) -> str:
    normalized = str(value or "ru").strip().lower()
    if normalized.startswith("kk") or normalized in {"kz", "қаз"}:
        return "kk"
    if normalized.startswith("en"):
        return "en"
    return "ru"

ALIASES: dict[str, tuple[str, ...]] = {
    "depth": ("depth", "dept", "md"),
    "tgas": ("tgas", "total_gas", "gas_total"),
    "c1_c2": ("c1_c2", "c1/c2", "c1c2"),
    "c1_c3": ("c1_c3", "c1/c3", "c1c3"),
    "c1_c4": ("c1_c4", "c1/c4", "c1c4"),
    "c1_c5": ("c1_c5", "c1/c5", "c1c5"),
    "inverse_oil_indicator": ("inverse_oil_indicator", "oil_index", "oil_inv"),
}


def _column_map(dataframe: pd.DataFrame) -> dict[str, str]:
    return {str(column).strip().lower(): str(column) for column in dataframe.columns}


def _resolve(mapping: dict[str, str], key: str) -> str | None:
    for candidate in ALIASES.get(key, (key,)):
        found = mapping.get(candidate.lower())
        if found:
            return found
    return None


def _bands(intervals: Iterable[Any]) -> tuple[IntervalBand, ...]:
    result: list[IntervalBand] = []
    for index, interval in enumerate(intervals, start=1):
        top = getattr(interval, "top", None)
        bottom = getattr(interval, "base", getattr(interval, "bottom", None))
        if top is None or bottom is None:
            continue
        fluid = str(getattr(interval, "fluid", "") or getattr(interval, "fluid_type", "") or getattr(interval, "classification", ""))
        confidence = getattr(interval, "confidence", None)
        try:
            confidence_value = float(confidence)
            if confidence_value <= 1:
                confidence_value *= 100
        except (TypeError, ValueError):
            confidence_value = None
        identity = str(getattr(interval, "id", "") or f"HC-{index:03d}")
        result.append(IntervalBand(float(top), float(bottom), identity, fluid, confidence_value))
    return tuple(result)


def _meaningful_overview_depth_range(
    dataframe: pd.DataFrame,
    *,
    depth_column: str,
    selected_columns: Iterable[str],
    intervals: tuple[IntervalBand, ...],
) -> tuple[float, float]:
    """Return an engineering-useful overview range instead of the raw LAS range.

    Long leading/trailing sections containing only zeros or recorder noise make
    the productive interval unreadable.  The crop is driven by robust gas-curve
    activity and by interpreted interval bounds, with a conservative context
    margin.
    """
    depth = pd.to_numeric(dataframe[depth_column], errors="coerce")
    valid_depth = depth.dropna()
    if valid_depth.empty:
        raise ValueError("No numeric depth values available")
    raw_min, raw_max = float(valid_depth.min()), float(valid_depth.max())

    activity = pd.Series(0.0, index=dataframe.index, dtype="float64")
    component_names = {"tgas", "c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5"}
    for column in selected_columns:
        normalized = str(column).strip().lower()
        if normalized not in component_names and not any(normalized == alias for key in component_names for alias in ALIASES.get(key, ())):
            continue
        values = pd.to_numeric(dataframe[column], errors="coerce").abs().fillna(0.0)
        activity = activity.add(values, fill_value=0.0)

    positive = activity[activity > 0]
    active_depths = pd.Series(dtype="float64")
    if not positive.empty:
        q95 = float(positive.quantile(0.95))
        threshold = max(1e-8, q95 * 0.0025)
        active_depths = depth[(activity >= threshold) & depth.notna()]

    candidates: list[float] = []
    if not active_depths.empty:
        candidates.extend((float(active_depths.min()), float(active_depths.max())))
    if intervals:
        candidates.extend(float(item.top) for item in intervals)
        candidates.extend(float(item.bottom) for item in intervals)

    if len(candidates) < 2:
        return raw_min, raw_max

    active_min, active_max = min(candidates), max(candidates)
    active_span = max(1.0, active_max - active_min)
    context = max(20.0, min(80.0, active_span * 0.045))
    crop_min = max(raw_min, active_min - context)
    crop_max = min(raw_max, active_max + context)

    # Do not crop when the gain is negligible; this avoids surprising zooms on
    # already compact datasets.
    raw_span = max(1.0, raw_max - raw_min)
    if (crop_max - crop_min) >= raw_span * 0.88:
        return raw_min, raw_max
    return crop_min, crop_max


def build_composite_log_v4(
    dataframe: pd.DataFrame,
    *,
    intervals: Iterable[Any] = (),
    title: str = "Engineering Composite Log v4",
    height: int = 1560,
    target_width: int = 2860,
    include_keys: Iterable[str] | None = None,
    report_kind: str = "overview",
    report_title: str | None = None,
    locale: str = "ru",
) -> CompositeLogResult:
    """Build the single canonical composite used by UI, PDF, DOCX and SVG export."""
    mapping = _column_map(dataframe)
    depth_key = _resolve(mapping, "depth")
    if not depth_key:
        raise ValueError("Depth column not found")

    allow = {str(item).lower() for item in include_keys} if include_keys else None
    selected: list[tuple[str, str, str, str, str, str]] = []
    for item in TRACK_LIBRARY:
        key = item[0]
        if allow is not None and key not in allow:
            continue
        column = _resolve(mapping, key)
        if column:
            selected.append((column, key, item[1], item[2], item[3], item[4]))

    if not selected:
        raise ValueError("No supported engineering curves found")

    depth_width = 420
    available_width = max(900, int(target_width) - depth_width - 28)
    # Adaptive widths: preserve readable tracks and allow a wide vector canvas when many curves exist.
    base_width = max(310, min(420, available_width // len(selected)))
    actual_target = depth_width + base_width * len(selected) + 28
    tracks = tuple(
        CurveTrackSpec(
            key=column,
            title=title_text,
            description=TRACK_DESCRIPTIONS[_locale(locale)].get(canonical_key, ""),
            unit=unit,
            width=base_width,
            scale=scale,
            stroke=stroke,
            stroke_width=5.0,
        )
        for column, canonical_key, title_text, unit, stroke, scale in selected
    )
    interval_bands = _bands(intervals)
    depth_min = depth_max = None
    if str(report_kind).lower() == "overview":
        depth_min, depth_max = _meaningful_overview_depth_range(
            dataframe,
            depth_column=depth_key,
            selected_columns=(column for column, *_ in selected),
            intervals=interval_bands,
        )

    locale_key = _locale(locale)
    text = COMPOSITE_TEXT[locale_key]
    spec = CompositeLogSpec(
        depth_key=depth_key,
        title=title,
        depth_track=DepthTrackSpec(title=text["depth"], unit=text["metre"], width=depth_width, minor_divisions=5),
        tracks=tracks,
        intervals=interval_bands,
        height=max(980, int(height)),
        header_height=420,
        footer_height=360,
        left_padding=14,
        right_padding=14,
        depth_min=depth_min,
        depth_max=depth_max,
        report_kind=report_kind,
        locale=locale_key,
    )
    rendered = CompositeLogEngine().render(dataframe, spec)
    interval_rows = tuple({
        "id": band.label, "top": band.top, "base": band.bottom,
        "thickness": band.bottom - band.top, "fluid": band.fluid,
        "confidence": band.confidence or 0,
    } for band in spec.intervals)
    return replace(
        rendered,
        report_title=report_title or title,
        report_kind=report_kind,
        report_intervals=interval_rows,
    )
