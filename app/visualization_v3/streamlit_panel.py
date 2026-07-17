from __future__ import annotations

from typing import Any, Iterable

import pandas as pd
import streamlit as st

from .composite_engine import CompositeLogEngine
from .models import CompositeLogSpec, CurveTrackSpec, IntervalBand


def _interval_bands(intervals: Iterable[Any]) -> tuple[IntervalBand, ...]:
    result: list[IntervalBand] = []
    for index, interval in enumerate(intervals, start=1):
        top = getattr(interval, "top", None)
        bottom = getattr(interval, "base", getattr(interval, "bottom", None))
        if top is None or bottom is None:
            continue
        fluid = str(
            getattr(interval, "fluid", "")
            or getattr(interval, "fluid_type", "")
            or getattr(interval, "classification", "")
        )
        confidence = getattr(interval, "confidence", None)
        try:
            confidence_value = float(confidence) * 100 if confidence is not None and float(confidence) <= 1 else float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence_value = None
        result.append(
            IntervalBand(
                top=float(top),
                bottom=float(bottom),
                label=str(getattr(interval, "id", "") or f"HC-{index:03d}"),
                fluid=fluid,
                confidence=confidence_value,
            )
        )
    return tuple(result)


def render_composite_log_v3(
    dataframe: pd.DataFrame,
    *,
    intervals: Iterable[Any] = (),
    height: int = 900,
) -> None:
    available = {str(column).strip().lower(): str(column) for column in dataframe.columns}
    track_candidates = (
        ("c1", "C1", "", 155, "#0f766e"),
        ("c2", "C2", "", 135, "#2563eb"),
        ("c3", "C3", "", 135, "#7c3aed"),
        ("wh", "Wh", "", 145, "#15803d"),
        ("bh", "Bh", "", 155, "#0369a1"),
        ("ch", "Ch", "", 145, "#b91c1c"),
    )
    tracks = tuple(
        CurveTrackSpec(key=available[key], title=title, unit=unit, width=width, stroke=stroke)
        for key, title, unit, width, stroke in track_candidates
        if key in available
    )
    if not tracks:
        st.info("Для нового планшета v3 не найдены C1/C2/C3/Wh/Bh/Ch.")
        return
    depth_key = available.get("depth") or available.get("dept")
    if not depth_key:
        st.warning("Для нового планшета v3 не найдена колонка глубины.")
        return
    spec = CompositeLogSpec(
        depth_key=depth_key,
        title="Engineering Composite Log v3",
        tracks=tracks,
        intervals=_interval_bands(intervals),
        height=height,
    )
    result = CompositeLogEngine().render(dataframe, spec)
    st.components.v1.html(result.svg, height=result.height + 8, scrolling=True)
    if result.issues:
        st.caption("v3 diagnostics: " + ", ".join(result.issues))
