from __future__ import annotations

import pandas as pd

from palettes.well_log_tablet import (
    MAX_SCREEN_INTERVAL_OVERLAYS,
    ReservoirIntervalOverlay,
    TabletTrackConfig,
    _prioritized_visible_intervals,
    build_well_log_tablet,
)


def _interval(index: int, confidence: int) -> ReservoirIntervalOverlay:
    top = 1000.0 + index
    return ReservoirIntervalOverlay(
        interval_id=f"HC-{index:03d}",
        top_depth=top,
        bottom_depth=top + 0.8,
        fluid_type="oil",
        confidence_score=confidence,
        thickness=0.8,
    )


def test_screen_interval_overlays_are_bounded_and_keep_selected() -> None:
    intervals = tuple(_interval(i, 20 + (i % 70)) for i in range(1, 90))
    selected_depth = 1088.2
    result = _prioritized_visible_intervals(
        intervals,
        visible_top=1000.0,
        visible_bottom=1100.0,
        selected_depth=selected_depth,
    )
    assert len(result) == MAX_SCREEN_INTERVAL_OVERLAYS
    assert any(item.interval_id == "HC-088" for item in result)


def test_tablet_uses_unified_canvas_and_minor_depth_grid() -> None:
    df = pd.DataFrame({"depth": [1000.0, 1001.0, 1002.0], "c1": [1.0, 2.0, 1.5]})
    fig = build_well_log_tablet(df, [TabletTrackConfig(column="c1")], height=500)
    assert fig.layout.hovermode == "y unified"
    assert fig.layout.plot_bgcolor == "#0b1220"
    assert fig.layout.yaxis.minor.showgrid is True
