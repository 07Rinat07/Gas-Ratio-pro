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
) -> CompositeLogResult:
    """Build the single canonical composite used by UI, PDF, DOCX and SVG export."""
    mapping = _column_map(dataframe)
    depth_key = _resolve(mapping, "depth")
    if not depth_key:
        raise ValueError("Depth column not found")

    allow = {str(item).lower() for item in include_keys} if include_keys else None
    selected: list[tuple[str, str, str, str, str]] = []
    for item in TRACK_LIBRARY:
        key = item[0]
        if allow is not None and key not in allow:
            continue
        column = _resolve(mapping, key)
        if column:
            selected.append((column, item[1], item[2], item[3], item[4]))

    if not selected:
        raise ValueError("No supported engineering curves found")

    depth_width = 320
    available_width = max(900, int(target_width) - depth_width - 28)
    # Adaptive widths: preserve readable tracks and allow a wide vector canvas when many curves exist.
    base_width = max(250, min(340, available_width // len(selected)))
    actual_target = depth_width + base_width * len(selected) + 28
    tracks = tuple(
        CurveTrackSpec(
            key=column,
            title=title_text,
            unit=unit,
            width=base_width,
            scale=scale,
            stroke=stroke,
            stroke_width=4.2,
        )
        for column, title_text, unit, stroke, scale in selected
    )
    spec = CompositeLogSpec(
        depth_key=depth_key,
        title=title,
        depth_track=DepthTrackSpec(title="Глубина", unit="м", width=depth_width, minor_divisions=5),
        tracks=tracks,
        intervals=_bands(intervals),
        height=max(980, int(height)),
        header_height=380,
        footer_height=300,
        left_padding=14,
        right_padding=14,
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
