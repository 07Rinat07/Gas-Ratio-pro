from __future__ import annotations

import pandas as pd

from app.streamlit_app import _tablet_informative_depth_range
from palettes.well_log_tablet import ReservoirIntervalOverlay, TabletTrackConfig, build_well_log_tablet


def _overlay(
    interval_id: str,
    top: float,
    base: float,
    fluid: str,
    confidence: int = 80,
) -> ReservoirIntervalOverlay:
    return ReservoirIntervalOverlay(
        interval_id=interval_id,
        top_depth=top,
        bottom_depth=base,
        fluid_type=fluid,
        confidence_score=confidence,
        thickness=abs(base - top),
    )


def test_tablet_focus_excludes_empty_well_section() -> None:
    overlays = (
        _overlay("HC-001", 1335.8, 1336.6, "condensate"),
        _overlay("HC-002", 1876.6, 1886.4, "gas"),
        _overlay("HC-003", 2002.8, 2016.2, "oil"),
        _overlay("HC-004", 500.0, 700.0, "uncertain"),
    )

    top, base = _tablet_informative_depth_range(overlays, (0.0, 2016.2))

    assert 1300.0 <= top < 1335.8
    assert base == 2016.2
    assert top > 0.0


def test_tablet_focus_keeps_water_and_hydrocarbon_intervals() -> None:
    overlays = (
        _overlay("HC-001", 1200.0, 1210.0, "water"),
        _overlay("HC-002", 1500.0, 1510.0, "gas"),
    )

    top, base = _tablet_informative_depth_range(overlays, (0.0, 2000.0))

    assert top < 1200.0
    assert base > 1510.0
    assert base < 2000.0


def test_tablet_legend_contains_curve_and_fluid_symbols() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0],
            "c1": [1.0, 2.0, 1.5],
            "c2": [0.4, 0.8, 0.6],
        }
    )
    overlays = (
        _overlay("HC-001", 1000.2, 1000.8, "oil", 92),
        _overlay("HC-002", 1001.2, 1001.8, "gas", 80),
    )

    figure = build_well_log_tablet(
        frame,
        [
            TabletTrackConfig(column="c1", label="C1", color="#ff4d3d"),
            TabletTrackConfig(column="c2", label="C2", color="#00c896"),
        ],
        depth_range=(1000.0, 1002.0),
        reservoir_intervals=overlays,
        height=700,
    )

    legend_traces = [trace for trace in figure.data if trace.showlegend]
    names = {trace.name for trace in legend_traces}
    assert {"C1", "C2", "Нефть", "Газ"}.issubset(names)
    assert any(trace.mode == "lines+markers" and trace.name == "C1" for trace in legend_traces)
    assert any(trace.mode == "markers" and trace.name == "Нефть" for trace in legend_traces)


def test_tablet_draws_coloured_top_and_base_markers() -> None:
    frame = pd.DataFrame({"depth": [1000.0, 1001.0, 1002.0], "c1": [1.0, 2.0, 1.5]})
    overlays = (_overlay("HC-001", 1000.2, 1001.8, "oil", 92),)

    figure = build_well_log_tablet(
        frame,
        [TabletTrackConfig(column="c1", label="C1")],
        depth_range=(1000.0, 1002.0),
        reservoir_intervals=overlays,
        height=700,
    )

    boundary_trace = next(trace for trace in figure.data if trace.name == "Границы интервалов")
    assert list(boundary_trace.marker.symbol) == ["triangle-down", "triangle-up"]
    assert len(boundary_trace.marker.color) == 2
