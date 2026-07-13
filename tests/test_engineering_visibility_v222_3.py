from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from palettes.plot_engine import THEME, enhance_screen_visibility
from palettes.well_log_tablet import (
    InterpretationZone,
    ReservoirIntervalOverlay,
    TabletTrackConfig,
    build_well_log_tablet,
)


def test_visibility_profile_strengthens_lines_markers_and_hover() -> None:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2], y=[2, 3], mode="lines", line={"width": 0.8}))
    fig.add_trace(go.Scatter(x=[1], y=[2], mode="markers", marker={"size": 4}))

    enhance_screen_visibility(fig)

    assert fig.data[0].line.width >= THEME.line_width
    assert fig.data[0].opacity >= 0.88
    assert fig.data[1].marker.size >= THEME.marker_size
    assert fig.data[1].marker.line.width >= 1.2
    assert fig.layout.uirevision == "gas-ratio-pro-engineering-view"
    assert fig.layout.hoverlabel.bgcolor == "#111827"


def test_tablet_zones_stay_below_curves_and_labels_are_dark() -> None:
    frame = pd.DataFrame({"depth": [1000.0, 1001.0, 1002.0], "c1": [10.0, 12.0, 11.0]})
    fig = build_well_log_tablet(
        frame,
        [TabletTrackConfig(column="c1", label="C1", color="#38bdf8")],
        zones=[InterpretationZone("Зона УВ", 1000.2, 1001.8, "#fbbf24")],
        reservoir_intervals=[
            ReservoirIntervalOverlay(
                interval_id="HC-001",
                top_depth=1000.4,
                bottom_depth=1001.6,
                fluid_type="oil",
                confidence_score=88,
                thickness=1.2,
            )
        ],
        selected_depth=1001.0,
        height=760,
    )

    paper_zones = [shape for shape in fig.layout.shapes if shape.xref == "paper" and shape.layer == "below"]
    assert paper_zones
    assert max(float(shape.opacity or 0) for shape in paper_zones) <= 0.27

    zone_labels = [annotation for annotation in fig.layout.annotations if "Зона УВ" in str(annotation.text)]
    assert zone_labels
    assert zone_labels[0].bgcolor == "rgba(15,23,42,0.88)"
    assert zone_labels[0].font.color == THEME.text_color
