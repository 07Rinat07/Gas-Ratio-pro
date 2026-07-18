from __future__ import annotations

import plotly.graph_objects as go

from palettes.plot_cache import PlotCache
from palettes.well_log_tablet import build_well_log_tablet, ReservoirIntervalOverlay, TabletTrackConfig
import pandas as pd

from tests.visual_rebaseline_helpers import assert_visual_rebaseline


def test_plot_cache_is_bounded_and_lru() -> None:
    cache = PlotCache(max_entries=2)
    cache.put(("a",), [go.Figure()])
    cache.put(("b",), [go.Figure()])
    assert cache.get(("a",)) is not None
    cache.put(("c",), [go.Figure()])
    assert cache.get(("b",)) is None
    assert cache.get(("a",)) is not None
    assert cache.get(("c",)) is not None
    assert len(cache) == 2


def test_tablet_engineering_headers_have_separate_boxes() -> None:
    frame = pd.DataFrame({"depth": [1000.0, 1001.0, 1002.0], "c1": [1.0, 2.0, 1.5]})
    fig = build_well_log_tablet(
        frame,
        [TabletTrackConfig(column="c1", label="C1")],
        reservoir_intervals=[
            ReservoirIntervalOverlay(
                interval_id="HC-001",
                top_depth=1000.2,
                bottom_depth=1001.8,
                fluid_type="oil",
                confidence_score=85,
                thickness=1.6,
            )
        ],
        height=760,
    )
    headers = list(fig.layout.annotations)[:3]
    assert_visual_rebaseline(
        "tests/test_plot_cache_v222_rc6.py::test_tablet_engineering_headers_have_separate_boxes",
        {
            "header_texts": [str(item.text) for item in headers],
            "header_y": float(headers[0].y),
            "background": str(headers[0].bgcolor),
            "border_width": int(headers[0].borderwidth),
            "top_margin": int(fig.layout.margin.t),
        },
    )
    assert len({float(item.x) for item in headers}) == 3
    assert all(item.bgcolor == headers[0].bgcolor and item.borderwidth == 1 for item in headers)

