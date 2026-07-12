from __future__ import annotations

import pandas as pd

from palettes.config import DEFAULT_PIXLER_ZONES
from palettes.pixler import analyze_pixler_interval, build_pixler_palette


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "depth": [1000.0, 1000.2, 1000.4, 1000.6],
            "c1_c2": [8.0, 9.0, 10.0, 11.0],
            "c1_c3": [12.0, 14.0, 16.0, 18.0],
            "c1_c4": [25.0, 30.0, 35.0, 40.0],
            "c1_c5": [50.0, 60.0, 70.0, 80.0],
        }
    )


def test_pixler_interval_summary_uses_all_measurements() -> None:
    frame = _frame()
    summary = analyze_pixler_interval(frame, frame.iloc[1], zones=DEFAULT_PIXLER_ZONES)

    assert summary.total_measurements == 4
    assert summary.valid_measurements == 4
    assert summary.median_values[0] == 9.5
    assert summary.selected_values[0] == 9.0
    assert summary.dominant_zone in {"Oil", "Gas"}
    assert "Pixler" in summary.conclusion


def test_pixler_figure_contains_cloud_median_selected_depth_and_zones() -> None:
    frame = _frame()
    figure = build_pixler_palette(
        frame.iloc[1],
        interval_frame=frame,
        interval_label="1000–1000.6 м · нефть · 84%",
        selected_depth=1000.2,
    )

    trace_names = {str(trace.name) for trace in figure.data}
    assert any(name.startswith("Измерения") for name in trace_names)
    assert any(name.startswith("Медиана") for name in trace_names)
    assert "Глубина 1000.2 м" in trace_names
    assert len(figure.layout.shapes) == len(DEFAULT_PIXLER_ZONES)
    assert "1000–1000.6" in str(figure.layout.title.text)


def test_pixler_empty_interval_is_safe() -> None:
    frame = pd.DataFrame({"c1_c2": [None], "c1_c3": [None]})
    summary = analyze_pixler_interval(frame, {}, zones=DEFAULT_PIXLER_ZONES)
    figure = build_pixler_palette({}, interval_frame=frame)

    assert summary.valid_measurements == 0
    assert summary.dominant_zone == "Недостаточно данных"
    assert figure is not None
