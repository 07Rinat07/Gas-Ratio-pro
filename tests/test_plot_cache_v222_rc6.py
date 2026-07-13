from __future__ import annotations

import plotly.graph_objects as go

from palettes.plot_cache import PlotCache
from palettes.well_log_tablet import build_well_log_tablet, ReservoirIntervalOverlay, TabletTrackConfig
import pandas as pd


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
    titles = list(fig.layout.annotations)[:4]
    assert "Тип" in titles[0].text
    assert "Достовер" in titles[1].text
    assert "QC" in titles[2].text
    for annotation in titles[:3]:
        assert annotation.bgcolor == "rgba(11,18,32,0.92)"
        assert annotation.borderwidth == 1
        assert annotation.y >= 1.1
    assert fig.layout.margin.t >= 176
