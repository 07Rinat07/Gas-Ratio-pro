from __future__ import annotations

import pandas as pd
import pytest

from las_editor.depth_grid import build_depth_grid, diagnose_depths, resample_las_data


def test_build_depth_grid_supports_decimal_comma_and_custom_step():
    grid = build_depth_grid("1,2", "2,0", "0,2")

    assert grid == (1.2, 1.4, 1.6, 1.8, 2.0)


def test_diagnose_depths_reports_duplicates_reverse_steps_and_gaps():
    df = pd.DataFrame({"depth": [1.2, 1.4, 1.4, 2.0, 1.8, None]})

    diagnostics = diagnose_depths(df, expected_step=0.2)

    assert diagnostics.valid_depth_count == 5
    assert diagnostics.null_depth_count == 1
    assert diagnostics.duplicate_depths == (1.4,)
    assert diagnostics.reverse_step_count == 1
    assert diagnostics.gaps[0].start_depth == pytest.approx(1.4)
    assert diagnostics.gaps[0].end_depth == pytest.approx(1.8)
    assert diagnostics.gaps[0].missing_depths == (1.6,)


def test_resample_las_data_adds_missing_depth_rows_without_filling_by_default():
    df = pd.DataFrame({"DEPT": [1.2, 1.6, 2.0], "C1": [80, 100, 120]})

    result = resample_las_data(df, depth_column="DEPT", target_step=0.2)

    assert list(result.data["DEPT"]) == [1.2, 1.4, 1.6, 1.8, 2.0]
    assert result.added_depths == (1.4, 1.8)
    assert pd.isna(result.data.loc[1, "C1"])
    assert pd.isna(result.data.loc[3, "C1"])


def test_resample_las_data_can_fill_added_rows_from_top():
    df = pd.DataFrame({"DEPT": [1.2, 1.6, 2.0], "C1": [80, 100, 120]})

    result = resample_las_data(df, depth_column="DEPT", target_step=0.2, fill_strategy="top")

    assert list(result.data["C1"]) == [80, 80, 100, 100, 120]


def test_resample_las_data_can_fill_added_rows_with_linear_values():
    df = pd.DataFrame({"DEPT": [1.2, 1.6, 2.0], "C1": [80, 100, 120]})

    result = resample_las_data(df, depth_column="DEPT", target_step=0.2, fill_strategy="linear")

    assert list(result.data["C1"]) == pytest.approx([80, 90, 100, 110, 120])


def test_resample_las_data_fixes_descending_depth_order():
    df = pd.DataFrame({"DEPT": [2.0, 1.8, 1.6], "C1": [120, 110, 100]})

    result = resample_las_data(df, depth_column="DEPT", target_step=0.2)

    assert result.depth_order_fixed
    assert list(result.data["DEPT"]) == [1.6, 1.8, 2.0]
    assert list(result.data["C1"]) == [100, 110, 120]
    assert any("Порядок глубины исправлен" in warning for warning in result.warnings)
