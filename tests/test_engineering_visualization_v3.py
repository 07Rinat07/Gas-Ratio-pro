from __future__ import annotations

import pandas as pd

from app.visualization_v3.composite_engine import CompositeLogEngine
from app.visualization_v3.depth_track import build_depth_ticks, nice_major_step
from app.visualization_v3.models import CompositeLogSpec, CurveTrackSpec, IntervalBand


def test_depth_ticks_have_major_and_minor_grid() -> None:
    ticks = build_depth_ticks(1000.0, 1100.0, major_step=10.0, minor_divisions=5)
    assert any(tick.major for tick in ticks)
    assert any(not tick.major for tick in ticks)
    assert nice_major_step(220.0) in {10.0, 20.0, 25.0}


def test_composite_engine_renders_independent_tracks_and_depth() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0],
            "c1": [0.1, 0.5, 1.0],
            "wh": [5.0, 20.0, 35.0],
            "bh": [10.0, 200.0, 900.0],
        }
    )
    spec = CompositeLogSpec(
        depth_key="depth",
        tracks=(
            CurveTrackSpec("c1", "C1", width=150),
            CurveTrackSpec("wh", "Wh", width=150),
            CurveTrackSpec("bh", "Bh", width=150),
        ),
        intervals=(IntervalBand(1000.5, 1001.5, "HC-001", "Газ", 92.0),),
        height=700,
    )
    result = CompositeLogEngine().render(frame, spec)
    assert result.rendered_tracks == ("c1", "wh", "bh")
    assert "Depth" in result.svg
    assert "HC-001" in result.svg
    assert "min" in result.svg and "avg" in result.svg and "max" in result.svg
    assert result.svg.count("<polyline") == 3
    assert result.width > 500
