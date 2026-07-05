from __future__ import annotations

import pandas as pd
import pytest

from las_editor.curve_categories import (
    CurveCategoryHistoryEntry,
    assign_curve_category,
    available_curve_categories,
    build_curve_categories,
    category_summary_rows,
    curve_category_table_rows,
    normalize_curve_category,
    suggest_curve_categories,
    suggest_curve_category,
    undo_last_category_assignment,
)


def test_suggest_and_build_curve_categories_from_las_columns():
    df = pd.DataFrame({"DEPT": [1000.0], "GR": [80.0], "TGAS": [1.2], "ROP": [12.0], "UNKNOWN": [5]})

    categories = build_curve_categories(df.columns)

    assert categories["depth_reference"] == ("DEPT",)
    assert categories["petrophysics"] == ("GR",)
    assert categories["mud_gas"] == ("TGAS",)
    assert categories["drilling"] == ("ROP",)
    assert categories["uncategorized"] == ("UNKNOWN",)


def test_group_overrides_drive_automatic_category():
    assert suggest_curve_category("TGAS") == "mud_gas"
    assert suggest_curve_category("TGAS", group="gamma") == "petrophysics"
    assert suggest_curve_categories(["TGAS"], group_overrides={"TGAS": "gamma"}) == {"TGAS": "petrophysics"}


def test_assign_curve_category_stores_override_history_and_references():
    df = pd.DataFrame({"DEPT": [1.0], "TGAS": [10.0]})
    references = {"manifest": {"TGAS": {"unit": "ppm"}}}

    result = assign_curve_category(
        df,
        "TGAS",
        " interpretation ",
        references=references,
        timestamp="2026-01-01T00:00:00+00:00",
    )

    assert result.assigned
    assert result.overrides == {"TGAS": "interpretation"}
    assert result.categories["interpretation"] == ("TGAS",)
    assert result.history[-1].previous_category == "mud_gas"
    assert result.history[-1].timestamp == "2026-01-01T00:00:00+00:00"
    assert result.references["curve_category_overrides"] == {"TGAS": "interpretation"}
    assert result.references["manifest"]["TGAS"]["category"] == "interpretation"


def test_assign_curve_category_validates_curve_and_category():
    df = pd.DataFrame({"DEPT": [1.0], "TGAS": [10.0]})

    with pytest.raises(ValueError, match="не найдена"):
        assign_curve_category(df, "MISSING", "mud_gas")

    with pytest.raises(ValueError, match="не поддерживается"):
        assign_curve_category(df, "TGAS", "bad_category")


def test_reassign_same_manual_category_is_noop():
    df = pd.DataFrame({"TGAS": [10.0]})

    result = assign_curve_category(df, "TGAS", "interpretation", category_overrides={"TGAS": "interpretation"})

    assert not result.assigned
    assert result.overrides == {"TGAS": "interpretation"}
    assert result.history == ()


def test_undo_last_category_assignment_restores_automatic_category():
    df = pd.DataFrame({"TGAS": [10.0], "GR": [80.0]})
    assigned = assign_curve_category(df, "TGAS", "interpretation")

    undone = undo_last_category_assignment(
        df,
        category_overrides=assigned.overrides,
        history=assigned.history,
        references=assigned.references,
    )

    assert undone.overrides == {}
    assert undone.categories["mud_gas"] == ("TGAS",)
    assert undone.categories["petrophysics"] == ("GR",)
    assert undone.history == ()


def test_undo_checks_current_state_changed():
    df = pd.DataFrame({"TGAS": [10.0]})
    history = (CurveCategoryHistoryEntry("TGAS", "interpretation", "mud_gas", "2026-01-01T00:00:00+00:00"),)

    with pytest.raises(ValueError, match="уже изменено"):
        undo_last_category_assignment(df, category_overrides={"TGAS": "mud_gas"}, history=history)


def test_curve_category_table_rows_include_group_alias_and_manual_flag():
    rows = curve_category_table_rows(
        ["DEPT", "TGAS"],
        group_overrides={"TGAS": "gamma"},
        category_overrides={"TGAS": "interpretation"},
        aliases={"TGAS": "total_gas"},
    )

    assert rows[1]["curve_name"] == "TGAS"
    assert rows[1]["alias"] == "total_gas"
    assert rows[1]["group"] == "gamma"
    assert rows[1]["auto_category"] == "petrophysics"
    assert rows[1]["category"] == "interpretation"
    assert rows[1]["manual_override"] == "yes"


def test_category_helpers_and_summary_rows():
    assert "mud_gas" in available_curve_categories()
    assert normalize_curve_category(" Mud Gas ") == "mud_gas"
    summary = category_summary_rows({"mud_gas": ("TGAS", "C1")})
    mud_gas = next(row for row in summary if row["category"] == "mud_gas")
    assert mud_gas["curve_count"] == "2"
    assert mud_gas["curves"] == "TGAS, C1"
