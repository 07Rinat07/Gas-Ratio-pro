from __future__ import annotations

import pandas as pd
import pytest

from las_editor.curve_merge import (
    CurveMergeHistoryEntry,
    merge_curves,
    normalize_merge_strategy,
    normalize_source_names,
    undo_last_merge,
)


def test_successful_merge_coalesce_first():
    df = pd.DataFrame({"DEPTH": [1, 2, 3], "C1_A": [1.0, None, 3.0], "C1_B": [10.0, 20.0, None]})

    result = merge_curves(df, ["C1_A", "C1_B"], " C1 merged ", timestamp="2026-01-01T00:00:00+00:00")

    assert list(result.data["C1_merged"]) == [1.0, 20.0, 3.0]
    assert "C1_A" in result.data.columns
    assert result.history[-1].source_names == ("C1_A", "C1_B")
    assert result.history[-1].target_name == "C1_merged"
    assert result.history[-1].timestamp == "2026-01-01T00:00:00+00:00"
    assert result.merged


def test_merge_missing_curve_reports_error():
    df = pd.DataFrame({"DEPTH": [1], "C1_A": [1.0]})

    with pytest.raises(ValueError, match="Не найдены"):
        merge_curves(df, ["C1_A", "C1_B"], "C1")


def test_merge_requires_two_source_curves():
    df = pd.DataFrame({"DEPTH": [1], "C1_A": [1.0]})

    with pytest.raises(ValueError, match="минимум две"):
        merge_curves(df, ["C1_A"], "C1")


def test_merge_to_empty_name_reports_error():
    df = pd.DataFrame({"DEPTH": [1], "C1_A": [1.0], "C1_B": [2.0]})

    with pytest.raises(ValueError, match="не может быть пустым"):
        merge_curves(df, ["C1_A", "C1_B"], "   ")


def test_merge_to_existing_name_reports_error():
    df = pd.DataFrame({"DEPTH": [1], "C1_A": [1.0], "C1_B": [2.0]})

    with pytest.raises(ValueError, match="уже существует"):
        merge_curves(df, ["C1_A", "C1_B"], "DEPTH")


def test_merge_mean_requires_numeric_sources():
    df = pd.DataFrame({"DEPTH": [1], "A": [1.0], "B": ["bad"]})

    with pytest.raises(ValueError, match="числовыми"):
        merge_curves(df, ["A", "B"], "AB", strategy="mean")


def test_merge_mean_and_sum_strategies():
    df = pd.DataFrame({"A": [1.0, None], "B": [3.0, 5.0]})

    mean_result = merge_curves(df, ["A", "B"], "AB_mean", strategy="mean")
    sum_result = merge_curves(df, ["A", "B"], "AB_sum", strategy="sum")

    assert list(mean_result.data["AB_mean"]) == [2.0, 5.0]
    assert list(sum_result.data["AB_sum"]) == [4.0, 5.0]


def test_merge_history_reason_source_and_keep_sources():
    df = pd.DataFrame({"A": [1.0], "B": [2.0]})
    history = (CurveMergeHistoryEntry(("OLD_A", "OLD_B"), "OLD", "sum", "2025-01-01T00:00:00+00:00"),)

    result = merge_curves(df, ["A", "B"], "AB", strategy="sum", history=history, reason="qc", source="test", keep_sources=False)

    assert len(result.history) == 2
    assert result.history[-1].reason == "qc"
    assert result.history[-1].source == "test"
    assert not result.history[-1].keep_sources
    assert "A" not in result.data.columns
    assert "B" not in result.data.columns
    assert "AB" in result.data.columns
    assert result.warnings


def test_undo_last_merge_removes_target_curve():
    df = pd.DataFrame({"A": [1.0], "B": [2.0]})
    merged = merge_curves(df, ["A", "B"], "AB")

    undone = undo_last_merge(merged.data, history=merged.history, references=merged.references)

    assert "AB" not in undone.data.columns
    assert undone.history == ()


def test_undo_last_merge_checks_history_and_target():
    df = pd.DataFrame({"A": [1.0], "B": [2.0]})

    with pytest.raises(ValueError, match="пуста"):
        undo_last_merge(df, history=())

    history = (CurveMergeHistoryEntry(("A", "B"), "AB", "coalesce_first", "2026-01-01T00:00:00+00:00"),)
    with pytest.raises(ValueError, match="не найдена"):
        undo_last_merge(df, history=history)


def test_merge_reference_update_adds_manifest_and_export_column():
    df = pd.DataFrame({"A": [1.0], "B": [2.0]})
    references = {"manifest": {"A": {"unit": "ppm"}, "B": {"unit": "ppm"}}, "exports": {"columns": ["A", "B"]}}

    result = merge_curves(df, ["A", "B"], "AB", strategy="sum", references=references)

    assert result.references["manifest"]["AB"]["source_curves"] == ["A", "B"]
    assert result.references["manifest"]["AB"]["strategy"] == "sum"
    assert result.references["exports"]["columns"] == ["A", "B", "AB"]


def test_merge_helpers():
    assert normalize_merge_strategy("Coalesce First") == "coalesce_first"
    assert normalize_source_names([" A ", "A", "B C"]) == ("A", "B_C")
