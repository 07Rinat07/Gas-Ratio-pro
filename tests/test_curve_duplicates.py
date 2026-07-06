from __future__ import annotations

import pandas as pd

from las_editor.curve_duplicates import (
    curve_duplicate_summary_rows,
    curve_duplicate_table_rows,
    detect_curve_duplicates,
)


def test_detect_curve_duplicates_finds_exact_numeric_copy():
    df = pd.DataFrame({"DEPT": [1.0, 2.0, 3.0], "TGAS": [10.0, 11.0, 12.0], "TGAS_COPY": [10.0, 11.0, 12.0]})
    result = detect_curve_duplicates(df)
    pair = next(candidate for candidate in result.candidates if candidate.primary_curve == "TGAS" and candidate.duplicate_curve == "TGAS_COPY")
    assert pair.severity == "exact"
    assert pair.value_match_ratio == 1.0
    assert result.summary["total"] >= 1
    assert result.references["curve_duplicate_summary"]["total"] == result.summary["total"]


def test_detect_curve_duplicates_finds_alias_duplicate_without_equal_values():
    df = pd.DataFrame({"TGAS_A": [1.0, 2.0, 3.0], "TGAS_B": [4.0, 5.0, 7.0]})
    result = detect_curve_duplicates(df, aliases={"TGAS_A": "total_gas", "TGAS_B": "total_gas"})
    candidate = result.candidates[0]
    assert candidate.severity == "name"
    assert "canonical key" in candidate.reason


def test_detect_curve_duplicates_finds_high_correlation_candidate():
    df = pd.DataFrame({"C1": [1.0, 2.0, 3.0, 4.0], "C2": [2.0, 4.0, 6.0, 8.0], "OTHER": [5.0, 1.0, 9.0, 2.0]})
    result = detect_curve_duplicates(df)
    assert any({candidate.primary_curve, candidate.duplicate_curve} == {"C1", "C2"} and candidate.severity == "high" for candidate in result.candidates)


def test_curve_duplicate_rows_format_metrics_and_summary():
    df = pd.DataFrame({"TGAS": [10.0, 11.0], "TGAS_COPY": [10.0, 11.0]})
    result = detect_curve_duplicates(df)
    rows = curve_duplicate_table_rows(result.candidates)
    assert rows[0]["severity_label"] == "Exact duplicate"
    assert rows[0]["value_match_ratio"] == "1.000"
    summary_rows = curve_duplicate_summary_rows(result.summary)
    assert next(row for row in summary_rows if row["severity"] == "total")["candidate_count"] == str(result.summary["total"])


def test_detect_curve_duplicates_returns_empty_result_for_distinct_curves():
    df = pd.DataFrame({"A": [1.0, 2.0, 10.0], "B": [4.0, 1.0, 7.0]})
    result = detect_curve_duplicates(df)
    assert result.candidates == ()
    assert result.summary["total"] == 0
