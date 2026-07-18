from pathlib import Path

import pandas as pd

from palettes.depth_tracks import build_depth_gas_tracks
from tests.visual_rebaseline_helpers import assert_visual_rebaseline


def test_depth_legend_is_below_plot_and_title_has_own_row():
    frame = pd.DataFrame({"depth": [1000, 1001], "c1": [1.0, 2.0], "c2": [0.1, 0.2]})
    figure = build_depth_gas_tracks(frame)
    legend_y = float(figure.layout.legend.y)
    title_y = float(figure.layout.title.y)
    assert_visual_rebaseline(
        "tests/test_plot_header_separation_v222_63.py::test_depth_legend_is_below_plot_and_title_has_own_row",
        {
            "legend_position": "above" if legend_y > 1.0 else "below",
            "legend_y": legend_y,
            "title_y": title_y,
            "top_margin": int(figure.layout.margin.t),
            "bottom_margin": int(figure.layout.margin.b),
            "separated": legend_y > title_y,
        },
    )

def test_export_signature_includes_build_version():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "build={BUILD_VERSION}" in source
