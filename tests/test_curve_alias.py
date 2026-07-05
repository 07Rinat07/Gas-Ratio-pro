from __future__ import annotations

import pandas as pd
import pytest

from las_editor.curve_alias import (
    CurveAliasHistoryEntry,
    assign_curve_alias,
    available_aliases,
    normalize_alias_name,
    suggest_curve_alias,
    suggest_curve_aliases,
    undo_last_alias,
)


def test_successful_alias_assignment_keeps_dataframe_columns():
    df = pd.DataFrame({"DEPT": [1.0, 1.2], "CH4": [10, 12]})

    result = assign_curve_alias(df, "CH4", " c1 ", timestamp="2026-01-01T00:00:00+00:00")

    assert result.aliases == {"CH4": "c1"}
    assert result.history[-1].curve_name == "CH4"
    assert result.history[-1].alias == "c1"
    assert result.history[-1].previous_alias == ""
    assert result.history[-1].timestamp == "2026-01-01T00:00:00+00:00"
    assert result.assigned


def test_alias_missing_curve_reports_error():
    df = pd.DataFrame({"DEPT": [1.0], "CH4": [10]})

    with pytest.raises(ValueError, match="не найдена"):
        assign_curve_alias(df, "C2", "c2")


def test_alias_to_empty_name_reports_error():
    df = pd.DataFrame({"DEPT": [1.0], "CH4": [10]})

    with pytest.raises(ValueError, match="не может быть пустым"):
        assign_curve_alias(df, "CH4", "   ")


def test_alias_to_unknown_standard_reports_error():
    df = pd.DataFrame({"DEPT": [1.0], "CH4": [10]})

    with pytest.raises(ValueError, match="не поддерживается"):
        assign_curve_alias(df, "CH4", "unknown")


def test_alias_history_appends_previous_alias_reason_and_source():
    df = pd.DataFrame({"DEPT": [1.0], "CH4": [10]})
    history = (CurveAliasHistoryEntry("OLD", "c1", "", "2025-01-01T00:00:00+00:00"),)

    result = assign_curve_alias(
        df,
        "CH4",
        "c2",
        aliases={"CH4": "c1"},
        history=history,
        reason="manual correction",
        source="test",
    )

    assert len(result.history) == 2
    assert result.history[-1].previous_alias == "c1"
    assert result.history[-1].reason == "manual correction"
    assert result.history[-1].source == "test"


def test_undo_last_alias_restores_previous_alias():
    df = pd.DataFrame({"DEPT": [1.0], "CH4": [10]})
    assigned = assign_curve_alias(df, "CH4", "c2", aliases={"CH4": "c1"})

    undone = undo_last_alias(aliases=assigned.aliases, history=assigned.history)

    assert undone.aliases == {"CH4": "c1"}
    assert undone.history == ()


def test_undo_last_alias_removes_new_assignment_without_previous_alias():
    df = pd.DataFrame({"DEPT": [1.0], "CH4": [10]})
    assigned = assign_curve_alias(df, "CH4", "c1")

    undone = undo_last_alias(aliases=assigned.aliases, history=assigned.history)

    assert undone.aliases == {}


def test_undo_last_alias_checks_current_state_changed():
    history = (CurveAliasHistoryEntry("CH4", "c1", "", "2026-01-01T00:00:00+00:00"),)

    with pytest.raises(ValueError, match="уже изменено"):
        undo_last_alias(aliases={"CH4": "c2"}, history=history)


def test_alias_reference_update_adds_manifest_and_alias_map():
    df = pd.DataFrame({"DEPT": [1.0], "CH4": [10]})
    references = {"manifest": {"CH4": {"unit": "ppm"}}, "curve_aliases": {}}

    result = assign_curve_alias(df, "CH4", "c1", references=references)

    assert result.references["manifest"]["CH4"]["alias"] == "c1"
    assert result.references["curve_aliases"] == {"CH4": "c1"}


def test_duplicate_alias_returns_warning_but_allows_assignment():
    df = pd.DataFrame({"DEPT": [1.0], "CH4": [10], "Methane": [11]})

    result = assign_curve_alias(df, "Methane", "c1", aliases={"CH4": "c1"})

    assert result.aliases["Methane"] == "c1"
    assert result.warnings


def test_suggest_curve_aliases_uses_existing_mapping_dictionary():
    assert suggest_curve_alias("CH4") == "c1"
    assert suggest_curve_aliases(["DEPT", "Ethane", "Unknown"]) == {"DEPT": "depth", "Ethane": "c2"}


def test_alias_helpers():
    assert "c1" in available_aliases()
    assert normalize_alias_name(" Depth From ") == "depth_from"
