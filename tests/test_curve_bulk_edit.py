from __future__ import annotations

import pandas as pd
import pytest

from las_editor.curve_bulk_edit import apply_curve_bulk_edit, curve_bulk_edit_operation_rows


def test_bulk_edit_assigns_group_to_selected_curves_without_mutating_dataframe():
    df = pd.DataFrame({"DEPT": [1, 2], "GR": [80, 82], "RT": [10, 12]})

    result = apply_curve_bulk_edit(
        df,
        selected_curves=["GR", "RT"],
        action="assign_group",
        group="petrophysics",
    )

    assert list(df.columns) == ["DEPT", "GR", "RT"]
    assert result.group_overrides["GR"] == "petrophysics"
    assert result.group_overrides["RT"] == "petrophysics"
    assert result.references["curve_bulk_edit_summary"]["applied"] == 2


def test_bulk_edit_assigns_unit_with_existing_context():
    df = pd.DataFrame({"C1": [1.1, 1.2], "C2": [0.2, 0.3]})

    result = apply_curve_bulk_edit(
        df,
        selected_curves=["C1", "C2"],
        action="assign_unit",
        unit="ppm",
        group_overrides={"C1": "gas_component"},
        category_overrides={"C1": "mud_gas"},
    )

    assert result.unit_overrides == {"C1": "ppm", "C2": "ppm"}
    assert result.group_overrides["C1"] == "gas_component"


def test_bulk_edit_metadata_patch_merges_default_record():
    df = pd.DataFrame({"GR": [80, 81]})

    result = apply_curve_bulk_edit(
        df,
        selected_curves=["GR"],
        action="assign_metadata",
        metadata_patch={"description": "Gamma ray from main run", "status": "approved"},
    )

    assert result.metadata["GR"]["description"] == "Gamma ray from main run"
    assert result.metadata["GR"]["status"] == "approved"
    assert "quality" in result.metadata["GR"]


def test_bulk_edit_prefix_renames_columns_and_moves_overrides():
    df = pd.DataFrame({"GR": [80, 81], "RT": [10, 11]})

    result = apply_curve_bulk_edit(
        df,
        selected_curves=["GR"],
        action="prefix",
        prefix="RAW_",
        group_overrides={"GR": "gamma"},
        unit_overrides={"GR": "api"},
    )

    assert list(result.data.columns) == ["RAW_GR", "RT"]
    assert "GR" not in result.group_overrides
    assert result.group_overrides["RAW_GR"] == "gamma"
    assert result.unit_overrides["RAW_GR"] == "api"


def test_bulk_edit_skips_affix_name_collision():
    df = pd.DataFrame({"GR": [80, 81], "RAW_GR": [82, 83]})

    result = apply_curve_bulk_edit(df, selected_curves=["GR"], action="prefix", prefix="RAW_")

    assert list(result.data.columns) == ["GR", "RAW_GR"]
    assert result.operations[0].status == "skipped"
    assert result.references["curve_bulk_edit_summary"]["skipped"] == 1
    assert result.warnings


def test_bulk_edit_rows_and_validation():
    df = pd.DataFrame({"GR": [80, 81]})

    result = apply_curve_bulk_edit(df, selected_curves=["GR"], action="assign_category", category="petrophysics")
    rows = curve_bulk_edit_operation_rows(result.operations)

    assert rows[0]["action_label"] == "Assign category"
    assert rows[0]["new_value"] == "petrophysics"

    with pytest.raises(ValueError):
        apply_curve_bulk_edit(df, selected_curves=["BAD"], action="assign_group", group="gamma")
