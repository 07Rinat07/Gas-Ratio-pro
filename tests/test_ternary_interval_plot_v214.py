from __future__ import annotations

import pandas as pd

from palettes.config import TernaryRegion
from palettes.ternary import analyze_ternary_interval, build_ternary_palette
from tests.visual_rebaseline_helpers import assert_visual_rebaseline


REGIONS = (
    TernaryRegion(
        name="Gas-prone",
        a=(0.55, 0.9, 0.6),
        b=(0.25, 0.05, 0.1),
        c=(0.2, 0.05, 0.3),
        color="rgba(30,115,190,0.12)",
    ),
    TernaryRegion(
        name="Oil-prone",
        a=(0.2, 0.55, 0.35),
        b=(0.55, 0.25, 0.35),
        c=(0.25, 0.2, 0.3),
        color="rgba(45,140,85,0.12)",
    ),
)


def test_ternary_interval_normalizes_cloud_and_builds_median():
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1000.5, 1001.0],
            "c2_sumc": [60.0, 0.60, 0.62],
            "c3_sumc": [20.0, 0.20, 0.18],
            "nc4_sumc": [20.0, 0.20, 0.20],
        }
    )
    summary = analyze_ternary_interval(frame, frame.iloc[1], regions=REGIONS)

    assert summary.valid_measurements == 3
    assert summary.total_measurements == 3
    assert summary.completeness_percent == 100.0
    assert all(value is not None for value in summary.median_point)
    assert abs(sum(value for value in summary.median_point if value is not None) - 1.0) < 1e-9


def test_ternary_reports_incomplete_input_coverage():
    frame = pd.DataFrame(
        {
            "c2_sumc": [0.6, 0.6, 0.6, 0.6, 0.6],
            "c3_sumc": [0.2, None, None, None, None],
            "nc4_sumc": [0.2, None, None, None, None],
        }
    )
    summary = analyze_ternary_interval(frame, frame.iloc[0], regions=REGIONS)

    assert summary.valid_measurements == 1
    assert summary.completeness_percent == 20.0
    assert "низкую устойчивость" in summary.conclusion


def test_ternary_figure_contains_regions_cloud_median_and_selected_depth():
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1000.5],
            "c2_sumc": [0.60, 0.62],
            "c3_sumc": [0.20, 0.18],
            "nc4_sumc": [0.20, 0.20],
        }
    )
    fig = build_ternary_palette(
        frame.iloc[1],
        regions=REGIONS,
        interval_frame=frame,
        interval_label="1000–1000.5 м · gas · 80%",
        selected_depth=1000.5,
    )
    polygons = [trace for trace in fig.data if trace.mode == "lines"]
    labels = [trace for trace in fig.data if trace.mode == "text"]
    names = [str(trace.name) for trace in fig.data]
    assert_visual_rebaseline(
        "tests/test_ternary_interval_plot_v214.py::test_ternary_figure_contains_regions_cloud_median_and_selected_depth",
        {
            "region_polygon_names": [str(trace.name) for trace in polygons],
            "region_label_trace_count": len(labels),
            "measurement_name": next(name for name in names if name.startswith("Измерения")),
            "median_name": "Медианный центр" if "Медианный центр" in names else "",
            "selected_depth_name": "Глубина 1000.5 м" if "Глубина 1000.5 м" in names else "",
            "valid_points": "2/2" if "валидных точек: 2/2" in fig.layout.title.text else "",
            "total_trace_count": len(fig.data),
        },
    )

def test_ternary_handles_no_jointly_valid_rows_without_failure():
    frame = pd.DataFrame({"c2_sumc": [0.5], "c3_sumc": [None], "nc4_sumc": [0.5]})
    fig = build_ternary_palette(frame.iloc[0], regions=REGIONS, interval_frame=frame)

    assert any("Недостаточно" in annotation.text for annotation in fig.layout.annotations)
