from __future__ import annotations

import pandas as pd

from reports.well_log_plot import (
    WellLogPlotConfig,
    build_professional_well_log_plot,
    track_layout_widths,
    track_title_font_size,
)


def test_track_layout_assigns_semantic_widths() -> None:
    widths = track_layout_widths(("c1", "c2", "inverse_oil_indicator"), show_interval_track=True)
    assert len(widths) == 4
    assert widths[0] > widths[2]  # interval track wider than a compact component track
    assert widths[1] > widths[2]  # C1 is a primary track
    assert widths[3] > widths[2]  # oil indicator needs room for its label and scale


def test_title_font_reduces_for_dense_tablets() -> None:
    assert track_title_font_size(6, profile="print") > track_title_font_size(15, profile="print")
    assert track_title_font_size(6, profile="screen") < track_title_font_size(6, profile="print")


def test_screen_profile_uses_compact_readable_layout() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0],
            "c1": [1.0, 2.0, 3.0],
            "c2": [2.0, 3.0, 4.0],
            "inverse_oil_indicator": [4.0, 5.0, 6.0],
        }
    )
    result = build_professional_well_log_plot(
        frame,
        config=WellLogPlotConfig(
            track_columns=("c1", "c2", "inverse_oil_indicator"),
            layout_profile="screen",
            auto_crop_to_active_data=False,
            height=640,
        ),
    )
    assert result.figure.layout.height == 640
    titles = [a for a in result.figure.layout.annotations if getattr(a, "text", None)]
    assert any(a.text == "Oil Inv." for a in titles)
    assert all((a.font.size or 0) >= 11 for a in titles[:4])
