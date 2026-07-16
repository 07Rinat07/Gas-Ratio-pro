from pathlib import Path

import pandas as pd

from palettes.depth_tracks import build_depth_gas_tracks


def test_depth_legend_is_below_plot_and_title_has_own_row():
    frame = pd.DataFrame({"depth": [1000, 1001], "c1": [1.0, 2.0], "c2": [0.1, 0.2]})
    figure = build_depth_gas_tracks(frame)
    assert float(figure.layout.legend.y) < 0
    assert float(figure.layout.title.y) > 0.9
    assert int(figure.layout.margin.b) >= 100


def test_export_signature_includes_build_version():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "build={BUILD_VERSION}" in source
