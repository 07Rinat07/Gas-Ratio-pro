from __future__ import annotations

import pandas as pd

from app.streamlit_app import _tablet_informative_depth_range, _visible_interval_overlays
from palettes.depth_tracks import build_depth_gas_tracks
from palettes.well_log_tablet import ReservoirIntervalOverlay


def _overlay(index: int, top: float, bottom: float, *, selected: bool = False):
    return ReservoirIntervalOverlay(
        interval_id="HC-SELECTED" if selected else f"HC-{index:03d}",
        top_depth=top,
        bottom_depth=bottom,
        fluid_type="oil" if index % 2 else "gas",
        confidence_score=95 if selected else 50 + index % 40,
        thickness=bottom - top,
    )


def test_selected_interval_controls_focus_instead_of_all_well_intervals():
    overlays = tuple(_overlay(i, 1300 + i * 5, 1303 + i * 5) for i in range(100)) + (
        _overlay(999, 2002.8, 2016.2, selected=True),
    )

    top, bottom = _tablet_informative_depth_range(
        overlays,
        (47.0, 2016.2),
        selected_depth=2009.5,
        selected_interval_id="HC-SELECTED",
    )

    assert top >= 1990.0
    assert bottom == 2016.2
    assert bottom - top < 40.0


def test_visible_overlays_are_bounded_and_keep_selected_interval():
    overlays = tuple(_overlay(i, 1300 + i * 2, 1301 + i * 2) for i in range(80)) + (
        _overlay(999, 1400.0, 1410.0, selected=True),
    )

    visible = _visible_interval_overlays(
        overlays,
        (1290.0, 1500.0),
        selected_interval_id="HC-SELECTED",
        limit=24,
    )

    assert len(visible) == 24
    assert any(item.interval_id == "HC-SELECTED" for item in visible)


def test_depth_chart_uses_lightweight_shapes_for_many_intervals():
    df = pd.DataFrame(
        {
            "depth": [1390.0, 1400.0, 1410.0, 1420.0],
            "c1": [0.1, 0.2, 0.15, 0.3],
        }
    )
    overlays = tuple(_overlay(i, 1390 + i, 1390.5 + i) for i in range(20))

    fig = build_depth_gas_tracks(
        df,
        depth_range=(1388.0, 1422.0),
        reservoir_intervals=overlays,
    )

    # One rectangle per ordinary interval; top/base lines are not duplicated.
    assert len(fig.layout.shapes) == len(overlays)
    assert fig.data[0].type == "scattergl"
