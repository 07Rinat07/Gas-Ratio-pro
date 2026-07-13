from __future__ import annotations

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval
from reports.well_log_plot import WellLogPlotConfig, build_professional_well_log_plot, downsample_depth_frame


def test_downsample_depth_frame_limits_points_and_keeps_last_depth() -> None:
    frame = pd.DataFrame({"depth": [float(i) for i in range(10000)], "c1": [i % 17 for i in range(10000)]})

    sampled, summary = downsample_depth_frame(frame, max_points=1000)

    assert len(sampled) <= 1001
    assert sampled["depth"].iloc[-1] == 9999.0
    assert summary.original_points == 10000
    assert summary.plotted_points == len(sampled)
    assert summary.method.startswith("stride:")


def test_professional_well_log_plot_adds_interval_track_and_zones() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0, 1003.0, 1004.0],
            "c1": [0.1, 0.2, 0.4, 0.3, 0.2],
            "wh": [10, 12, 14, 13, 11],
        }
    )
    interval = HydrocarbonInterval(
        top=1001.0,
        base=1003.0,
        sample_count=3,
        fluid_type="gas",
        confidence="high",
        confidence_score=92,
        interpretation="Вероятный газонасыщенный интервал",
    )

    result = build_professional_well_log_plot(
        frame,
        (interval,),
        config=WellLogPlotConfig(track_columns=("c1", "wh"), max_points_per_track=100),
    )

    assert result.plotted_columns == ("c1", "wh")
    assert result.interval_count == 1
    assert len(result.figure.data) == 3  # interval placeholder + two curves
    assert len(result.figure.layout.shapes) == 2  # analytical zone + categorical interval stripe
    annotation_text = " ".join(str(item.text) for item in result.figure.layout.annotations if getattr(item, "text", None))
    assert "HC-001" in annotation_text
    assert "Газ" in annotation_text
    assert "92%" in annotation_text


def test_professional_well_log_plot_ignores_missing_or_non_numeric_tracks() -> None:
    frame = pd.DataFrame({"depth": [1, 2, 3], "c1": [1.0, 2.0, 3.0], "bad": ["x", "y", "z"]})

    result = build_professional_well_log_plot(frame, config=WellLogPlotConfig(track_columns=("c1", "missing", "bad")))

    assert result.plotted_columns == ("c1",)
    assert len(result.figure.data) == 2  # interval placeholder + c1
