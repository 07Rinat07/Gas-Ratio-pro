from __future__ import annotations

import pandas as pd

from las_editor.curve_quality import (
    curve_quality_flag_rows,
    curve_quality_summary_rows,
    detect_curve_quality_flags,
)


def test_detect_curve_quality_flags_missing_values():
    df = pd.DataFrame({"TGAS": [1.0, None, None, 4.0]})
    result = detect_curve_quality_flags(df, missing_ratio_threshold=0.25)
    missing = next(flag for flag in result.flags if flag.flag_type == "missing")
    assert missing.curve_name == "TGAS"
    assert missing.affected_count == 2
    assert result.summary["missing"] == 1
    assert result.references["curve_quality_summary"]["total"] == result.summary["total"]


def test_detect_curve_quality_flags_flat_interval():
    df = pd.DataFrame({"GR": [80.0, 80.0, 80.0, 80.0, 83.0, 85.0]})
    result = detect_curve_quality_flags(df, flat_run_min_length=4)
    flat = next(flag for flag in result.flags if flag.flag_type == "flat")
    assert flat.affected_count == 4
    assert flat.category in {"petrophysics", "uncategorized"}


def test_detect_curve_quality_flags_spike_candidate():
    df = pd.DataFrame({"C1": [1.0, 1.1, 0.9, 1.0, 40.0, 1.2, 0.8, 1.0]})
    result = detect_curve_quality_flags(df, spike_zscore_threshold=4.0)
    assert any(flag.flag_type == "spike" for flag in result.flags)


def test_detect_curve_quality_flags_non_numeric_curve():
    df = pd.DataFrame({"COMMENT": ["ok", "bad", "review"]})
    result = detect_curve_quality_flags(df)
    flag = result.flags[0]
    assert flag.flag_type == "non_numeric"
    assert flag.severity == "review"


def test_curve_quality_rows_format_summary():
    df = pd.DataFrame({"TGAS": [1.0, None, None, 4.0]})
    result = detect_curve_quality_flags(df, missing_ratio_threshold=0.25)
    rows = curve_quality_flag_rows(result.flags)
    assert rows[0]["flag_label"] == "Missing values"
    assert rows[0]["affected_ratio"] == "0.500"
    summary_rows = curve_quality_summary_rows(result.summary)
    assert next(row for row in summary_rows if row["flag_type"] == "total")["flag_count"] == str(result.summary["total"])
