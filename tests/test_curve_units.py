from __future__ import annotations

import pandas as pd
import pytest

from las_editor.curve_units import (
    CurveUnitHistoryEntry,
    assign_curve_unit,
    available_curve_units,
    build_curve_units,
    conversion_factor,
    curve_unit_table_rows,
    normalize_curve_unit,
    suggest_curve_unit,
    unit_summary_rows,
    undo_last_unit_assignment,
)


def test_suggest_units_from_groups_and_categories():
    assert suggest_curve_unit("DEPT") == "m"
    assert suggest_curve_unit("GR") == "api"
    assert suggest_curve_unit("TGAS") == "percent"
    assert suggest_curve_unit("RATIO", group="gas_ratio") == "unitless"


def test_build_curve_units_uses_manual_overrides():
    units = build_curve_units(["DEPT", "TGAS"], unit_overrides={"TGAS": "ppm"})
    assert units == {"DEPT": "m", "TGAS": "ppm"}


def test_assign_curve_unit_updates_manifest_and_history():
    df = pd.DataFrame({"DEPT": [1.0], "TGAS": [10.0]})
    result = assign_curve_unit(
        df,
        "TGAS",
        "ppm",
        references={"manifest": {"TGAS": {"source": "las_editor"}}},
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert result.assigned
    assert result.overrides == {"TGAS": "ppm"}
    assert result.units["TGAS"] == "ppm"
    assert result.history[-1].previous_unit == "percent"
    assert result.references["curve_unit_overrides"] == {"TGAS": "ppm"}
    assert result.references["manifest"]["TGAS"]["unit"] == "ppm"


def test_assign_curve_unit_validates_curve_and_unit():
    df = pd.DataFrame({"TGAS": [10.0]})
    with pytest.raises(ValueError, match="не найдена"):
        assign_curve_unit(df, "MISSING", "ppm")
    with pytest.raises(ValueError, match="не поддерживается"):
        assign_curve_unit(df, "TGAS", "bad_unit")


def test_reassign_same_manual_unit_is_noop():
    df = pd.DataFrame({"TGAS": [10.0]})
    result = assign_curve_unit(df, "TGAS", "ppm", unit_overrides={"TGAS": "ppm"})
    assert not result.assigned
    assert result.history == ()


def test_undo_last_unit_assignment_restores_automatic_unit():
    df = pd.DataFrame({"TGAS": [10.0], "DEPT": [1.0]})
    assigned = assign_curve_unit(df, "TGAS", "ppm")
    undone = undo_last_unit_assignment(df, unit_overrides=assigned.overrides, history=assigned.history)
    assert undone.overrides == {}
    assert undone.units["TGAS"] == "percent"
    assert undone.history == ()


def test_undo_checks_current_state_changed():
    df = pd.DataFrame({"TGAS": [10.0]})
    history = (CurveUnitHistoryEntry("TGAS", "ppm", "percent", "2026-01-01T00:00:00+00:00"),)
    with pytest.raises(ValueError, match="уже изменено"):
        undo_last_unit_assignment(df, unit_overrides={"TGAS": "percent"}, history=history)


def test_curve_unit_rows_and_summary():
    rows = curve_unit_table_rows(["DEPT", "TGAS"], unit_overrides={"TGAS": "ppm"}, aliases={"TGAS": "total_gas"})
    assert rows[1]["alias"] == "total_gas"
    assert rows[1]["auto_unit"] == "percent"
    assert rows[1]["unit"] == "ppm"
    assert rows[1]["manual_override"] == "yes"
    summary = unit_summary_rows({"DEPT": "m", "TGAS": "ppm"})
    ppm = next(row for row in summary if row["unit"] == "ppm")
    assert ppm["curve_count"] == "1"
    assert ppm["curves"] == "TGAS"


def test_unit_helpers_and_conversion_factor():
    assert "ppm" in available_curve_units()
    assert normalize_curve_unit("%") == "percent"
    assert conversion_factor("percent", "ppm") == 10000.0
    with pytest.raises(ValueError, match="Нет безопасного"):
        conversion_factor("api", "ppm")
