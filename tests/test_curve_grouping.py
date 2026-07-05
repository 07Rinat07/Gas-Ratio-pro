from __future__ import annotations

import pandas as pd
import pytest

from las_editor.curve_grouping import (
    CurveGroupingHistoryEntry,
    assign_curve_group,
    available_curve_groups,
    build_curve_groups,
    curve_group_table_rows,
    normalize_curve_group,
    suggest_curve_group,
    suggest_curve_groups,
    undo_last_group_assignment,
)


def test_suggest_and_build_curve_groups_from_las_columns():
    df = pd.DataFrame({"DEPT": [1000.0], "GR": [80.0], "TGAS": [1.2], "C1": [0.8], "UNKNOWN": [5]})

    groups = build_curve_groups(df.columns)

    assert groups["depth"] == ("DEPT",)
    assert groups["gamma"] == ("GR",)
    assert groups["total_gas"] == ("TGAS",)
    assert groups["gas_component"] == ("C1",)
    assert groups["other"] == ("UNKNOWN",)


def test_assign_curve_group_stores_override_history_and_references():
    df = pd.DataFrame({"DEPT": [1.0], "TGAS": [10.0]})
    references = {"manifest": {"TGAS": {"unit": "ppm"}}}

    result = assign_curve_group(
        df,
        "TGAS",
        " gamma ",
        references=references,
        timestamp="2026-01-01T00:00:00+00:00",
    )

    assert result.assigned
    assert result.overrides == {"TGAS": "gamma"}
    assert result.groups["gamma"] == ("TGAS",)
    assert result.history[-1].previous_group == "total_gas"
    assert result.history[-1].timestamp == "2026-01-01T00:00:00+00:00"
    assert result.references["curve_group_overrides"] == {"TGAS": "gamma"}
    assert result.references["manifest"]["TGAS"]["group"] == "gamma"


def test_assign_curve_group_validates_curve_and_group():
    df = pd.DataFrame({"DEPT": [1.0], "TGAS": [10.0]})

    with pytest.raises(ValueError, match="не найдена"):
        assign_curve_group(df, "MISSING", "gamma")

    with pytest.raises(ValueError, match="не поддерживается"):
        assign_curve_group(df, "TGAS", "bad_group")


def test_reassign_same_manual_group_is_noop():
    df = pd.DataFrame({"TGAS": [10.0]})

    result = assign_curve_group(df, "TGAS", "gamma", overrides={"TGAS": "gamma"})

    assert not result.assigned
    assert result.overrides == {"TGAS": "gamma"}
    assert result.history == ()


def test_undo_last_group_assignment_restores_automatic_group():
    df = pd.DataFrame({"TGAS": [10.0], "GR": [80.0]})
    assigned = assign_curve_group(df, "TGAS", "gamma")

    undone = undo_last_group_assignment(df, overrides=assigned.overrides, history=assigned.history, references=assigned.references)

    assert undone.overrides == {}
    assert undone.groups["total_gas"] == ("TGAS",)
    assert undone.groups["gamma"] == ("GR",)
    assert undone.history == ()


def test_undo_checks_current_state_changed():
    df = pd.DataFrame({"TGAS": [10.0]})
    history = (CurveGroupingHistoryEntry("TGAS", "gamma", "total_gas", "2026-01-01T00:00:00+00:00"),)

    with pytest.raises(ValueError, match="уже изменено"):
        undo_last_group_assignment(df, overrides={"TGAS": "other"}, history=history)


def test_curve_group_table_rows_include_alias_and_manual_flag():
    rows = curve_group_table_rows(["DEPT", "TGAS"], overrides={"TGAS": "gamma"}, aliases={"TGAS": "total_gas"})

    assert rows[1]["curve_name"] == "TGAS"
    assert rows[1]["alias"] == "total_gas"
    assert rows[1]["auto_group"] == "total_gas"
    assert rows[1]["group"] == "gamma"
    assert rows[1]["manual_override"] == "yes"


def test_group_helpers():
    assert "gamma" in available_curve_groups()
    assert normalize_curve_group(" Gas Component ") == "gas_component"
    assert suggest_curve_group("RDEEP") == "resistivity"
    assert suggest_curve_groups(["DEPT", "CH4"]) == {"DEPT": "depth", "CH4": "gas_component"}
