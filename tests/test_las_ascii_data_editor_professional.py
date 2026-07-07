from __future__ import annotations

import pandas as pd

from las_editor.ascii_data_editor import (
    ascii_editor_summary,
    build_ascii_table,
    delete_ascii_rows,
    edit_ascii_cell,
    edit_ascii_range,
    find_replace_ascii_values,
    insert_ascii_rows,
    preview_ascii_changes,
    render_ascii_section,
    sort_ascii_by_depth,
    validate_ascii_data,
)


def sample_df() -> pd.DataFrame:
    df = pd.DataFrame({"DEPT": [1000.0, 1000.5, 1001.0], "GR": [80.0, 82.0, -999.25], "C1": [10.0, 11.0, 12.0]})
    df.attrs["las_null_value"] = -999.25
    return df


def test_edit_ascii_cell_preserves_original_and_history() -> None:
    df = sample_df()
    result = edit_ascii_cell(df, row_index=1, column="GR", value=90.0)

    assert df.loc[1, "GR"] == 82.0
    assert result.data.loc[1, "GR"] == 90.0
    assert result.history[-1].action == "edit_cell"
    assert "Исходный LAS" in result.diagnostics[-1]


def test_edit_ascii_range_and_preview_changes() -> None:
    df = sample_df()
    result = edit_ascii_range(df, row_start=0, row_stop=1, columns=["C1"], value=15.0)
    changes = preview_ascii_changes(df, result.data)

    assert result.data.loc[0, "C1"] == 15.0
    assert result.data.loc[1, "C1"] == 15.0
    assert len(changes) == 2


def test_insert_delete_and_sort_rows() -> None:
    df = sample_df()
    inserted = insert_ascii_rows(df, [{"DEPT": 999.5, "GR": 70.0, "C1": 9.0}], position=0)
    sorted_result = sort_ascii_by_depth(inserted.data)
    deleted = delete_ascii_rows(sorted_result.data, [0])

    assert list(sorted_result.data["DEPT"]) == [999.5, 1000.0, 1000.5, 1001.0]
    assert len(deleted.data) == 3
    assert deleted.history[-1].action == "delete_rows"


def test_find_replace_and_render_ascii_section() -> None:
    df = sample_df()
    result = find_replace_ascii_values(df, find_value=-999.25, replace_value=None, columns=["GR"])
    text = render_ascii_section(result.data)

    assert pd.isna(result.data.loc[2, "GR"])
    assert "-999.25" in text
    assert result.history[-1].details["replacement_count"] == 1


def test_validate_ascii_data_reports_duplicate_depth_and_step() -> None:
    df = pd.DataFrame({"DEPT": [1000.0, 1000.5, 1000.5, 1002.0], "GR": [1, 2, 3, 4]})
    issues = validate_ascii_data(df, expected_step=0.5)
    codes = {issue.code for issue in issues}

    assert "DUPLICATE_DEPTH" in codes
    assert "DEPTH_NOT_INCREASING" in codes or "DEPTH_STEP_MISMATCH" in codes


def test_table_and_summary_are_ui_ready() -> None:
    df = sample_df()
    rows = build_ascii_table(df)
    summary = ascii_editor_summary(df)

    assert rows[0]["DEPT"] == 1000.0
    assert summary["row_count"] == 3
    assert summary["curve_count"] == 3
    assert summary["depth_column"] == "DEPT"
