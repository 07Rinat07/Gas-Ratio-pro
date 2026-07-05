from __future__ import annotations

import pandas as pd
import pytest

from las_editor.curve_metadata import (
    CurveMetadataHistoryEntry,
    assign_curve_metadata,
    available_metadata_fields,
    build_curve_metadata,
    curve_metadata_table_rows,
    metadata_summary_rows,
    normalize_metadata_field,
    normalize_metadata_value,
    undo_last_metadata_assignment,
)


def test_build_curve_metadata_uses_existing_curve_context():
    metadata = build_curve_metadata(
        ["DEPT", "TGAS"],
        aliases={"TGAS": "total_gas"},
        group_overrides={"TGAS": "total_gas"},
        unit_overrides={"TGAS": "ppm"},
    )
    assert metadata["TGAS"]["alias"] == "total_gas"
    assert metadata["TGAS"]["group"] == "total_gas"
    assert metadata["TGAS"]["unit"] == "ppm"
    assert metadata["TGAS"]["status"] == "draft"


def test_assign_curve_metadata_updates_manifest_and_history():
    df = pd.DataFrame({"DEPT": [1.0], "TGAS": [10.0]})
    result = assign_curve_metadata(
        df,
        "TGAS",
        "description",
        "  Total gas from chromatograph  ",
        references={"manifest": {"TGAS": {"unit": "percent"}}},
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert result.assigned
    assert result.metadata["TGAS"]["description"] == "Total gas from chromatograph"
    assert result.history[-1].previous_value == "LAS curve TGAS"
    assert result.references["curve_metadata"]["TGAS"]["description"] == "Total gas from chromatograph"
    assert result.references["manifest"]["TGAS"]["description"] == "Total gas from chromatograph"


def test_assign_curve_metadata_validates_inputs():
    df = pd.DataFrame({"TGAS": [10.0]})
    with pytest.raises(ValueError, match="не найдена"):
        assign_curve_metadata(df, "MISSING", "description", "x")
    with pytest.raises(ValueError, match="не поддерживается"):
        assign_curve_metadata(df, "TGAS", "unsupported", "x")
    with pytest.raises(ValueError, match="Статус"):
        assign_curve_metadata(df, "TGAS", "status", "bad")


def test_reassign_same_manual_metadata_is_noop():
    df = pd.DataFrame({"TGAS": [10.0]})
    result = assign_curve_metadata(
        df,
        "TGAS",
        "source",
        "Mud log",
        metadata={"TGAS": {"source": "Mud log"}},
    )
    assert not result.assigned
    assert result.history == ()


def test_undo_last_metadata_assignment_restores_previous_value():
    df = pd.DataFrame({"TGAS": [10.0]})
    assigned = assign_curve_metadata(df, "TGAS", "quality", "checked")
    undone = undo_last_metadata_assignment(
        df,
        metadata=assigned.references["curve_metadata"],
        history=assigned.history,
    )
    assert undone.metadata["TGAS"]["quality"] == "unknown"
    assert undone.history == ()


def test_undo_checks_current_value_changed():
    df = pd.DataFrame({"TGAS": [10.0]})
    history = (CurveMetadataHistoryEntry("TGAS", "status", "approved", "draft", "2026-01-01T00:00:00+00:00"),)
    with pytest.raises(ValueError, match="уже изменено"):
        undo_last_metadata_assignment(df, metadata={"TGAS": {"status": "review"}}, history=history)


def test_metadata_rows_summary_and_normalizers():
    rows = curve_metadata_table_rows(
        ["TGAS"],
        metadata={"TGAS": {"status": "approved", "quality": "corrected", "comment": "QA passed"}},
    )
    assert rows[0]["status_label"] == "Approved"
    assert rows[0]["quality_label"] == "Corrected"
    assert rows[0]["manual_fields"] == "comment, quality, status"
    summary = metadata_summary_rows(build_curve_metadata(["TGAS"], metadata={"TGAS": {"status": "approved"}}))
    assert next(row for row in summary if row["key"] == "approved")["curve_count"] == "1"
    assert "description" in available_metadata_fields()
    assert normalize_metadata_field("quality flag") == "quality"
    assert normalize_metadata_value("quality", "QC") == "checked"
