from __future__ import annotations

import pytest

from las_editor.curve_manager import (
    add_curve_managed,
    build_curve_manifest,
    curve_manager_table_rows,
    delete_curve_managed,
    reorder_curves,
    update_curve_manifest_entry,
)
from las_editor.las_creator import LasCurveSpec, build_las_creation_spec, create_las_document


def _sample_df():
    spec = build_las_creation_spec(
        well_name="B2-Well",
        start_depth=1000,
        stop_depth=1001,
        step=0.5,
        template_name="petrophysics",
    )
    return create_las_document(spec).data


def test_curve_manifest_contains_units_roles_quality_and_order():
    df = _sample_df()
    manifest = build_curve_manifest(df, metadata={"GR": {"quality": "checked", "description": "Gamma Ray"}})

    assert manifest["DEPT"]["protected"] is True
    assert manifest["GR"]["group"] == "gamma"
    assert manifest["GR"]["quality"] == "checked"
    assert manifest["GR"]["description"] == "Gamma Ray"
    assert manifest["GR"]["order"] > manifest["DEPT"]["order"]

    rows = curve_manager_table_rows(manifest)
    assert rows[0]["curve_name"] == "DEPT"
    assert any(row["curve_name"] == "GR" and row["protected"] == "no" for row in rows)


def test_managed_add_and_delete_curve_preserve_original_dataframe():
    df = _sample_df()
    result = add_curve_managed(df, LasCurveSpec("ROP", "M/H", "Rate of penetration"))

    assert "ROP" not in df.columns
    assert "ROP" in result.data.columns
    assert result.manifest["ROP"]["description"] == "Rate of penetration"
    assert result.history[-1].action == "add_curve"

    deleted = delete_curve_managed(result.data, "ROP", metadata=result.references["curve_manager"]["metadata"], history=result.history)
    assert "ROP" not in deleted.data.columns
    assert deleted.history[-1].action == "delete_curve"


def test_curve_manager_protects_depth_curve_from_deletion():
    df = _sample_df()
    with pytest.raises(ValueError):
        delete_curve_managed(df, "DEPT")


def test_reorder_curves_keeps_depth_first_and_updates_manifest_order():
    df = _sample_df()
    result = reorder_curves(df, ["RT", "GR", "DEPT"])

    assert list(result.data.columns)[:3] == ["DEPT", "RT", "GR"]
    assert result.manifest["DEPT"]["order"] == 0
    assert result.manifest["RT"]["order"] == 1


def test_update_curve_manifest_entry_is_metadata_only():
    df = _sample_df()
    result = update_curve_manifest_entry(df, "GR", field="alias", value="Gamma Ray")

    assert list(result.data.columns) == list(df.columns)
    assert result.manifest["GR"]["alias"] == "GAMMA_RAY"
    assert result.references["curve_manager"]["metadata"]["GR"]["alias"] == "GAMMA_RAY"
    assert "Значения LAS-кривой не изменялись." in result.diagnostics
