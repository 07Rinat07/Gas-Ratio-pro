from __future__ import annotations

import pandas as pd
import pytest

from las_editor.curve_rename import (
    CurveRenameHistoryEntry,
    normalize_curve_name,
    rename_curve,
    undo_last_rename,
    update_curve_references,
)


def test_successful_rename_normalizes_name_and_keeps_data():
    df = pd.DataFrame({"DEPT": [1.0, 1.2], "C1": [10, 12]})

    result = rename_curve(df, "C1", " Methane Gas ", timestamp="2026-01-01T00:00:00+00:00")

    assert list(result.data.columns) == ["DEPT", "Methane_Gas"]
    assert list(result.data["Methane_Gas"]) == [10, 12]
    assert result.history[-1].old_name == "C1"
    assert result.history[-1].new_name == "Methane_Gas"
    assert result.history[-1].timestamp == "2026-01-01T00:00:00+00:00"
    assert result.renamed


def test_rename_missing_curve_reports_error():
    df = pd.DataFrame({"DEPT": [1.0], "C1": [10]})

    with pytest.raises(ValueError, match="не найдена"):
        rename_curve(df, "C2", "ETH")


def test_rename_to_empty_name_reports_error():
    df = pd.DataFrame({"DEPT": [1.0], "C1": [10]})

    with pytest.raises(ValueError, match="не может быть пустым"):
        rename_curve(df, "C1", "   ")


def test_rename_to_existing_name_reports_error():
    df = pd.DataFrame({"DEPT": [1.0], "C1": [10], "C2": [2]})

    with pytest.raises(ValueError, match="уже существует"):
        rename_curve(df, "C1", "C2")


def test_rename_history_appends_reason_and_source():
    df = pd.DataFrame({"DEPT": [1.0], "C1": [10]})
    history = (CurveRenameHistoryEntry("OLD", "OLDER", "2025-01-01T00:00:00+00:00"),)

    result = rename_curve(df, "C1", "C1_GAS", history=history, reason="quality review", source="test")

    assert len(result.history) == 2
    assert result.history[-1].reason == "quality review"
    assert result.history[-1].source == "test"


def test_undo_last_rename_restores_previous_name_and_history():
    df = pd.DataFrame({"DEPT": [1.0], "C1": [10]})
    renamed = rename_curve(df, "C1", "C1_GAS")

    undone = undo_last_rename(renamed.data, history=renamed.history)

    assert list(undone.data.columns) == ["DEPT", "C1"]
    assert undone.history == ()
    assert undone.renamed


def test_undo_rename_checks_reverse_name_conflict():
    df = pd.DataFrame({"DEPT": [1.0], "C1": [10], "C1_OLD": [11]})
    history = (CurveRenameHistoryEntry("C1_OLD", "C1", "2026-01-01T00:00:00+00:00"),)

    with pytest.raises(ValueError, match="уже занято"):
        undo_last_rename(df, history=history)


def test_reference_update_handles_existing_project_structures():
    references = {
        "tablet_tracks": ["DEPT", "C1"],
        "templates": {"gas": {"curve": "C1"}},
        "presets": [{"tracks": ["C1", "C2"]}],
        "saved_calculations": {"mapping": {"c1": "C1"}},
        "exports": {"columns": ("DEPT", "C1")},
        "manifest": {"C1": {"unit": "ppm"}},
    }

    updated = update_curve_references(references, "C1", "C1_GAS")

    assert updated["tablet_tracks"] == ["DEPT", "C1_GAS"]
    assert updated["templates"]["gas"]["curve"] == "C1_GAS"
    assert updated["presets"][0]["tracks"] == ["C1_GAS", "C2"]
    assert updated["saved_calculations"]["mapping"]["c1"] == "C1_GAS"
    assert updated["exports"]["columns"] == ("DEPT", "C1_GAS")
    assert "C1_GAS" in updated["manifest"]
    assert "C1" not in updated["manifest"]


def test_rename_curve_returns_updated_references():
    df = pd.DataFrame({"DEPT": [1.0], "C1": [10]})
    references = {"tablet_tracks": ["C1"], "manifest": {"C1": {"unit": "ppm"}}}

    result = rename_curve(df, "C1", "C1_GAS", references=references)

    assert result.references["tablet_tracks"] == ["C1_GAS"]
    assert "C1_GAS" in result.references["manifest"]


def test_normalize_curve_name_collapses_spaces():
    assert normalize_curve_name("  Total Gas  Curve ") == "Total_Gas_Curve"
