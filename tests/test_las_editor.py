from __future__ import annotations

import pandas as pd
import pytest

from las_editor.depth_grid import (
    apply_las_bulk_operations,
    build_las_edit_audit_log,
    build_las_edit_preview,
    build_las_editor_hints,
    build_depth_grid,
    insert_manual_depth_rows,
    build_depth_step_report,
    diagnose_depths,
    resample_las_data,
)


def test_build_depth_grid_supports_decimal_comma_and_custom_step():
    grid = build_depth_grid("1,2", "2,0", "0,2")

    assert grid == (1.2, 1.4, 1.6, 1.8, 2.0)


def test_depth_step_report_finds_min_max_common_step_and_outliers():
    depths = pd.Series([1000.0, 1000.2, 1000.4, 1001.0, 1001.2])

    report = build_depth_step_report(depths, expected_step=0.2)

    assert report.step_count == 4
    assert report.min_step == pytest.approx(0.2)
    assert report.max_step == pytest.approx(0.6)
    assert report.most_common_step == pytest.approx(0.2)
    assert len(report.outliers) == 1
    assert report.outliers[0].from_depth == pytest.approx(1000.4)
    assert report.outliers[0].to_depth == pytest.approx(1001.0)
    assert report.outliers[0].step == pytest.approx(0.6)


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
    assert diagnostics.step_report.min_step == pytest.approx(0.2)
    assert diagnostics.step_report.max_step == pytest.approx(0.4)
    assert diagnostics.step_report.outliers


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



def test_apply_las_bulk_operations_removes_duplicates_and_sorts_depths():
    df = pd.DataFrame({"DEPT": [1000.4, 1000.0, 1000.0, 1000.2], "C1": [30, 10, 99, -999.25]})

    result = apply_las_bulk_operations(
        df,
        depth_column="DEPT",
        remove_duplicate_depths=True,
        replace_null_value=-999.25,
        sort_depth=True,
    )

    assert list(result.data["DEPT"]) == [1000.0, 1000.2, 1000.4]
    assert list(result.data["C1"].isna()) == [False, True, False]
    assert result.monotonic
    assert any("Duplicate depth rows removed: 1" in item for item in result.operation_log)
    assert any("Depth monotonicity check passed" in item for item in result.operation_log)


def test_apply_las_bulk_operations_trims_interval_and_reports_non_monotonic_depth():
    df = pd.DataFrame({"DEPT": [1000.0, 1000.6, 1000.2, 1001.0], "C1": [10, 60, 20, 100]})

    result = apply_las_bulk_operations(df, depth_column="DEPT", trim_start=1000.1, trim_end=1000.7)

    assert list(result.data["DEPT"]) == [1000.6, 1000.2]
    assert not result.monotonic
    assert any("Trimmed rows above 1000.1" in item for item in result.operation_log)
    assert any("Trimmed rows below 1000.7" in item for item in result.operation_log)
    assert any("не монотонна" in warning for warning in result.warnings)


def test_las_edit_preview_reports_manual_changes():
    before = pd.DataFrame({"DEPT": [1000.0, 1000.2], "C1": [80, 90]})
    after = pd.DataFrame({"DEPT": [1000.0, 1000.2, 1000.4], "C1": [81, 90, 95]})

    preview = build_las_edit_preview(before, after)

    assert preview.before_rows == 2
    assert preview.after_rows == 3
    assert preview.added_rows == 1
    assert preview.removed_rows == 0
    assert preview.changed_cells == 1
    assert preview.changed_columns == ("C1",)


def test_las_edit_audit_log_includes_bulk_resample_and_manual_preview():
    preview = build_las_edit_preview(
        pd.DataFrame({"DEPT": [1.0], "C1": [10]}),
        pd.DataFrame({"DEPT": [1.0, 1.2], "C1": [11, 12]}),
    )

    log = build_las_edit_audit_log(
        depth_column="DEPT",
        target_step=0.2,
        fill_strategy="linear",
        bulk_operation_log=("Rows sorted by depth in ascending order.",),
        added_depths=(1.2,),
        manual_preview=preview,
    )

    assert [entry.stage for entry in log].count("configuration") == 3
    assert any(entry.stage == "bulk" for entry in log)
    assert any(entry.stage == "resample" and "1" in entry.details for entry in log)
    assert any(entry.stage == "manual" and "changed cells: 1" in entry.details for entry in log)


def test_insert_manual_depth_rows_adds_only_selected_interval():
    df = pd.DataFrame({"DEPT": [1000.0, 1000.4, 1001.0], "C1": [10, 14, 20]})

    result = insert_manual_depth_rows(
        df,
        depth_column="DEPT",
        start_depth=1000.0,
        end_depth=1000.4,
        step=0.2,
        fill_strategy="empty",
    )

    assert list(result.data["DEPT"]) == [1000.0, 1000.2, 1000.4, 1001.0]
    assert result.added_depths == (1000.2,)
    assert pd.isna(result.data.loc[1, "C1"])
    assert any("Manual interval rows added: 1" in item for item in result.operation_log)


def test_insert_manual_depth_rows_can_fill_and_audit_manual_interval():
    df = pd.DataFrame({"DEPT": [1.0, 1.4], "C1": [10, 14]})

    result = insert_manual_depth_rows(
        df,
        depth_column="DEPT",
        start_depth="1,0",
        end_depth="1,4",
        step="0,2",
        fill_strategy="linear",
    )
    log = build_las_edit_audit_log(
        depth_column="DEPT",
        target_step=0.2,
        fill_strategy="linear",
        manual_interval_log=result.operation_log,
        added_depths=result.added_depths,
    )

    assert list(result.data["C1"]) == pytest.approx([10, 12, 14])
    assert result.added_depths == (1.2,)
    assert any(entry.stage == "manual-interval" for entry in log)
    assert any("Manual interval rows added: 1" in entry.details for entry in log)


def test_las_editor_hints_explain_depth_gaps_nulls_and_manual_edits():
    df = pd.DataFrame({"DEPT": [1000.0, 1000.4, 1000.4, None], "C1": [10, -999.25, 14, 20]})
    diagnostics = diagnose_depths(df, depth_column="DEPT", expected_step=0.2)
    preview = build_las_edit_preview(
        pd.DataFrame({"DEPT": [1000.0, 1000.2], "C1": [10, 12]}),
        pd.DataFrame({"DEPT": [1000.0, 1000.2], "C1": [11, 12]}),
    )

    hints = build_las_editor_hints(
        diagnostics,
        added_depth_count=1,
        fill_strategy="linear",
        bulk_operation_log=("LAS NULL -999.25 replaced with empty values: 1 cells.",),
        manual_interval_log=("Manual interval rows added: 1.",),
        preview=preview,
    )

    topics = {hint.topic for hint in hints}
    assert "Шаг глубины" in topics
    assert "Пропуски глубины" in topics
    assert "NULL-значения" in topics
    assert "Ручное заполнение" in topics
    assert "Предпросмотр правок" in topics
    assert any(hint.status == "warning" and "пропущенными" in hint.message for hint in hints)
    assert any(hint.topic == "NULL-значения" and hint.status == "review" for hint in hints)
    assert any(hint.topic == "Предпросмотр правок" and "изменено ячеек 1" in hint.message for hint in hints)


def test_las_editor_hints_report_clean_depth_grid_as_ok():
    df = pd.DataFrame({"DEPT": [1.0, 1.2, 1.4], "C1": [10, 12, 14]})
    diagnostics = diagnose_depths(df, depth_column="DEPT", expected_step=0.2)

    hints = build_las_editor_hints(diagnostics, preview=build_las_edit_preview(df, df))

    assert any(hint.topic == "Шаг глубины" and hint.status == "ok" for hint in hints)
    assert any(hint.topic == "Пропуски глубины" and hint.status == "ok" for hint in hints)
    assert any(hint.topic == "Сохранение скважины" for hint in hints)
    assert any(hint.topic == "Выгрузка данных" for hint in hints)
