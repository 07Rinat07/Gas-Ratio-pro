from __future__ import annotations

import pandas as pd

from app.visualization_v3.composite_v4 import build_composite_log_v4


def test_v4_renders_all_supported_tracks_and_vector_output() -> None:
    frame = pd.DataFrame({
        "depth": [1000.0, 1001.0, 1002.0],
        "tgas": [1.0, 2.0, 3.0], "c1": [0.1, 0.2, 0.3], "c2": [0.01, 0.02, 0.03],
        "c3": [0.005, 0.006, 0.007], "ic4": [0.001, 0.002, 0.003], "nc4": [0.002, 0.003, 0.004],
        "ic5": [0.001, 0.0015, 0.002], "nc5": [0.0005, 0.001, 0.0015],
        "wh": [10, 20, 30], "bh": [100, 200, 300], "ch": [0.8, 1.0, 1.2],
        "c1_c2": [10, 10, 10], "c1_c3": [20, 30, 40], "c1_c4": [33, 40, 43],
        "c1_c5": [66, 80, 85], "inverse_oil_indicator": [2, 3, 4],
    })
    result = build_composite_log_v4(frame, target_width=2200)
    assert result.svg.startswith("<svg")
    assert "Engineering Composite Log v4" in result.svg
    assert len(result.rendered_tracks) >= 15
    assert "Oil Index" in result.svg
    assert result.width >= 1700


def test_v4_keeps_shared_depth_grid_and_independent_scales() -> None:
    frame = pd.DataFrame({"depth": [1000, 1010, 1020], "c1": [0.1, 1.0, 2.0], "bh": [5, 500, 1000]})
    result = build_composite_log_v4(frame)
    assert "Depth" in result.svg
    assert "C1" in result.svg and "Bh" in result.svg
    assert result.svg.count("<line") > 10
