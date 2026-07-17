import pandas as pd
import plotly.graph_objects as go

from reports.well_log_plot import WellLogPlotConfig, build_professional_well_log_plot


def test_print_plot_keeps_depth_grid_and_multiple_collision_aware_markers():
    frame = pd.DataFrame({
        "depth": [1000.0, 1001.0, 1002.0, 1003.0],
        "c1": [0.1, 0.2, 0.4, 0.3],
        "wh": [10.0, 20.0, 30.0, 40.0],
        "bh": [1.0, 2.0, 3.0, 4.0],
        "ch": [0.8, 0.9, 1.0, 1.1],
    })
    frame.attrs["report_plot_selection"] = [
        {"depth": 1001.0, "x": 0.2, "curve_name": "C1", "fluid_label": "Газовая залежь", "fluid_percent": 92},
        {"depth": 1001.2, "x": 20.0, "curve_name": "Wh", "fluid_label": "Газовая залежь", "fluid_percent": 92},
        {"depth": 1001.4, "x": 2.0, "curve_name": "Bh", "fluid_label": "Газовая залежь", "fluid_percent": 92},
    ]
    result = build_professional_well_log_plot(
        frame, (), config=WellLogPlotConfig(track_columns=("c1", "wh", "bh", "ch"), layout_profile="print")
    )
    fig = result.figure
    texts = [str(a.text) for a in fig.layout.annotations if getattr(a, "text", None)]
    assert any("C1" in text and "92%" in text for text in texts)
    assert any("Wh" in text for text in texts)
    assert len({float(a.x) for a in fig.layout.annotations if getattr(a, "showarrow", False)}) >= 2
    assert fig.layout.yaxis.showgrid is True
    assert fig.layout.yaxis.dtick is not None
    assert fig.layout.yaxis.minor.showgrid is True
