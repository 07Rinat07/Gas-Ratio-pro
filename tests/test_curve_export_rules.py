from __future__ import annotations

import pandas as pd
import pytest

from las_editor.curve_export_rules import (
    apply_curve_export_rules,
    available_export_profiles,
    build_curve_export_preview,
    curve_export_preview_rows,
    export_profile_rows,
)


def test_export_rules_canonicalize_aliases_and_preserve_source_dataframe():
    df = pd.DataFrame({"DEPT": [1000.0, 1001.0], "GAMMA": [80.0, 82.0], "DEN": [2.30, 2.31]})

    result = apply_curve_export_rules(df, profile_id="petrel")

    assert list(df.columns) == ["DEPT", "GAMMA", "DEN"]
    assert list(result.data.columns) == ["DEPT", "GR", "RHOB"]
    assert result.summary["exported"] == 3
    assert result.summary["renamed"] == 2
    assert result.curve_units["DEPT"] == "m"
    assert result.curve_units["RHOB"] == "g_cm3"


def test_export_rules_convert_supported_units():
    df = pd.DataFrame({"MD": [100.0, 101.0], "TGAS": [0.01, 0.02]})

    result = apply_curve_export_rules(
        df,
        profile_id="default_las",
        unit_overrides={"TGAS": "v_v"},
        unit_map={"TGAS": "percent"},
    )

    assert list(result.data.columns) == ["DEPT", "TGAS"]
    assert result.data["TGAS"].tolist() == [1.0, 2.0]
    assert result.summary["unit_converted"] == 1


def test_export_rules_duplicate_strategy_renames_or_excludes():
    df = pd.DataFrame({"GR": [80, 81], "GAMMA": [82, 83], "GK": [84, 85]})

    renamed = apply_curve_export_rules(df, profile_id="petrel", duplicate_strategy="rename")
    assert list(renamed.data.columns) == ["GR", "GR_2", "GR_3"]
    assert renamed.summary["duplicates_resolved"] == 2

    excluded = apply_curve_export_rules(df, profile_id="petrel", duplicate_strategy="exclude")
    assert list(excluded.data.columns) == ["GR"]
    assert excluded.summary["skipped"] == 2


def test_export_preview_and_profile_rows_are_ui_safe():
    df = pd.DataFrame({"DEPT": [1, 2], "CALC_RATIO": [0.4, 0.5], "HIDDEN": [3, 4]})

    preview = build_curve_export_preview(
        df,
        profile_id="default_las",
        curve_mode="selected",
        selected_curves=["DEPT", "CALC_RATIO"],
        hidden_curves=["HIDDEN"],
    )
    rows = curve_export_preview_rows(preview)
    profile_ids = {row["profile_id"] for row in export_profile_rows()}

    assert rows[0]["export"] == "yes"
    assert rows[2]["export"] == "no"
    assert "petrel" in available_export_profiles()
    assert "default_las" in profile_ids


def test_export_rules_validate_empty_result():
    df = pd.DataFrame({"GR": [80, 81]})

    with pytest.raises(ValueError):
        apply_curve_export_rules(df, curve_mode="selected", selected_curves=[])
