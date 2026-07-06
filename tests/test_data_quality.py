from pathlib import Path

import pandas as pd

from projects.data_quality import (
    analyze_curve_quality,
    analyze_las_quality,
    build_curve_quality_table,
    build_data_quality_report,
    build_quality_issue_table,
    build_quality_report_table,
    export_quality_report_html,
    export_quality_report_json,
    list_data_quality_reports,
    save_data_quality_report,
    summarize_data_quality_reports,
    validate_geological_intervals,
    validate_petrophysical_results,
)


def _qc_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 999.5, 999.0, 999.0, None],
            "GR": [80.0, 85.0, 90.0, 999.0, 82.0],
            "RHOB": [2.45, 2.45, 2.45, 2.45, 2.45],
            "VSH": [0.2, 0.4, 1.2, -0.1, 0.3],
            "EMPTY": [None, None, None, None, None],
        }
    )


def test_las_quality_detects_depth_and_empty_curve_issues() -> None:
    issues = analyze_las_quality(_qc_frame(), depth_column="DEPT")
    codes = {issue.code for issue in issues}

    assert "DEPTH_DECREASING" in codes
    assert "DEPTH_DUPLICATES" in codes
    assert "DEPTH_MISSING" in codes
    assert "EMPTY_CURVE" in codes
    assert build_quality_issue_table(issues)[0]["Severity"] in {"error", "warning", "critical", "info"}


def test_curve_quality_and_petrophysical_validation() -> None:
    frame = _qc_frame()
    summaries = analyze_curve_quality(frame, depth_column="DEPT")
    table = build_curve_quality_table(summaries)
    petro = validate_petrophysical_results(frame)

    rhob = next(item for item in summaries if item.curve == "RHOB")
    assert rhob.constant is True
    assert any(row["Кривая"] == "GR" for row in table)
    assert any(issue.object_name == "VSH" for issue in petro)


def test_geological_interval_validation_detects_overlap_and_gap() -> None:
    issues = validate_geological_intervals(
        [
            {"name": "A", "well_id": "W1", "top_md_m": 1000, "base_md_m": 1100},
            {"name": "B", "well_id": "W1", "top_md_m": 1090, "base_md_m": 1200},
            {"name": "C", "well_id": "W1", "top_md_m": 1210, "base_md_m": 1300},
            {"name": "Bad", "well_id": "W2", "top_md_m": 1500, "base_md_m": 1400},
        ]
    )
    codes = {issue.code for issue in issues}

    assert "ZONE_OVERLAP" in codes
    assert "ZONE_GAP" in codes
    assert "ZONE_ORDER_INVALID" in codes


def test_data_quality_report_persistence_and_exports(tmp_path: Path) -> None:
    report = build_data_quality_report(_qc_frame(), name="LAS QC", source_id="well.las")
    save_data_quality_report(tmp_path, "demo", report)
    reports = list_data_quality_reports(tmp_path, "demo")
    summary = summarize_data_quality_reports(reports)

    assert reports[0].name == "LAS QC"
    assert summary.reports == 1
    assert summary.errors >= 1
    assert build_quality_report_table(reports)[0]["Проблем"] == reports[0].issue_count
    assert "well.las" in export_quality_report_json(report)
    assert "Качество кривых" in export_quality_report_html(report)
