from __future__ import annotations

import pandas as pd

from projects.statistics_center import (
    build_boxplot_summary,
    build_crossplot_points,
    build_histogram_bins,
    build_histogram_table,
    build_statistics_reports_table,
    build_statistics_summary_table,
    calculate_correlation_matrix,
    calculate_descriptive_statistics,
    filter_statistics_depth_range,
    list_numeric_columns,
    list_statistics_reports,
    save_statistics_report,
    summarize_statistics_center,
)


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "DEPT": [1000, 1001, 1002, 1003, 1004, 1005],
            "GR": [80, 82, 84, 86, 88, 120],
            "RHOB": [2.45, 2.46, 2.47, 2.48, 2.49, 2.50],
            "ZONE": ["A", "A", "A", "B", "B", "B"],
        }
    )


def test_statistics_center_descriptive_histogram_and_boxplot() -> None:
    frame = _sample_frame()

    filtered = filter_statistics_depth_range(frame, depth_column="DEPT", min_depth=1001, max_depth=1004)
    assert list(filtered["DEPT"]) == [1001, 1002, 1003, 1004]
    assert list_numeric_columns(frame, exclude_depth=True, depth_column="DEPT") == ("GR", "RHOB")

    summaries = calculate_descriptive_statistics(frame, columns=["GR", "RHOB"], depth_column="DEPT", min_depth=1001, max_depth=1004)
    rows = build_statistics_summary_table(summaries)
    assert rows[0]["Кривая"] == "GR"
    assert rows[0]["Count"] == 4
    assert rows[0]["Min"] == 82.0
    assert rows[0]["Max"] == 88.0

    histogram = build_histogram_bins(frame, "GR", bins=3)
    assert len(histogram) == 3
    assert sum(item.count for item in histogram) == 6
    assert build_histogram_table(histogram)[0]["Кривая"] == "GR"

    box = build_boxplot_summary(frame, "GR")
    assert box.column == "GR"
    assert box.iqr is not None
    assert box.outliers >= 0


def test_statistics_center_crossplot_and_correlation() -> None:
    frame = _sample_frame()

    points = build_crossplot_points(frame, "GR", "RHOB", depth_column="DEPT", label_column="ZONE", limit=3)
    assert len(points) == 3
    assert points[0].x == 80.0
    assert points[0].depth == 1000.0
    assert points[0].label == "A"

    corr = calculate_correlation_matrix(frame, columns=["GR", "RHOB"], method="pearson")
    assert list(corr.columns) == ["GR", "RHOB"]
    assert round(float(corr.loc["RHOB", "RHOB"]), 6) == 1.0


def test_statistics_center_report_persistence(tmp_path) -> None:
    frame = _sample_frame()

    report = save_statistics_report(
        tmp_path,
        "demo",
        "GR quality overview",
        source_type="las",
        source_id="demo.las",
        data_frame=frame,
        depth_column="DEPT",
        min_depth=1000,
        max_depth=1004,
        correlation_method="spearman",
        well_id="Well A",
    )

    reports = list_statistics_reports(tmp_path, "demo")
    assert reports[0].id == report.id
    assert reports[0].rows == 5
    assert reports[0].columns == ("GR", "RHOB")
    assert summarize_statistics_center(tmp_path, "demo").reports == 1
    table = build_statistics_reports_table(reports)
    assert table[0]["Источник"] == "las"
    assert table[0]["Скважина"] == "well-a"
