from __future__ import annotations

from pathlib import Path

import pandas as pd

from las_editor.curve_importer import (
    build_curve_import_manifest,
    build_curve_import_plan,
    curve_import_issue_table_rows,
    curve_import_table_rows,
    import_curve_specs_from_table,
    merge_imported_curves,
    normalize_curve_import_table,
    read_curve_import_csv,
)


def _target_df() -> pd.DataFrame:
    df = pd.DataFrame({"DEPT": [1000.0, 1000.5, 1001.0], "GR": [80.0, 82.0, 85.0]})
    df.attrs["las_units"] = {"DEPT": "M", "GR": "API"}
    df.attrs["las_null_value"] = -999.25
    return df


def test_normalize_curve_import_table_makes_unique_las_names() -> None:
    df = pd.DataFrame([[1, 2, 3]], columns=["Depth (m)", "Gamma Ray", "Gamma Ray"])

    result = normalize_curve_import_table(df)

    assert list(result.columns) == ["DEPTH_M", "GAMMA_RAY", "GAMMA_RAY_2"]


def test_build_curve_import_plan_selects_curves_and_metadata() -> None:
    incoming = pd.DataFrame({"DEPT": [1000.0, 1001.0], "NPHI": [0.2, 0.25]})

    plan = build_curve_import_plan(
        _target_df(),
        incoming,
        rename_map={"NPHI": "TNPH"},
        units={"NPHI": "v/v"},
        match_policy="interpolate",
        conflict_policy="suffix",
    )

    assert plan.curves == ("NPHI",)
    assert plan.rename_map["NPHI"] == "TNPH"
    assert plan.units["NPHI"] == "V/V"
    assert curve_import_table_rows(plan)[0]["target_curve"] == "TNPH"


def test_merge_imported_curves_interpolates_to_target_depth_grid() -> None:
    target = _target_df()
    incoming = pd.DataFrame({"DEPT": [1000.0, 1001.0], "NPHI": [0.2, 0.4]})
    plan = build_curve_import_plan(target, incoming, match_policy="interpolate", rename_map={"NPHI": "TNPH"})

    result = merge_imported_curves(target, incoming, plan)

    assert result.imported_curves == ("TNPH",)
    assert list(result.data["TNPH"].round(3)) == [0.2, 0.3, 0.4]
    assert "TNPH" in result.data.columns
    assert result.history[-1].action == "import_curves"


def test_merge_imported_curves_suffixes_conflicting_names() -> None:
    target = _target_df()
    incoming = pd.DataFrame({"DEPT": [1000.0, 1000.5, 1001.0], "GR": [70.0, 71.0, 72.0]})
    plan = build_curve_import_plan(target, incoming, conflict_policy="suffix", match_policy="exact")

    result = merge_imported_curves(target, incoming, plan)

    assert result.imported_curves == ("GR_2",)
    assert "GR" in result.data.columns
    assert "GR_2" in result.data.columns
    assert list(result.data["GR_2"]) == [70.0, 71.0, 72.0]


def test_merge_imported_curves_can_skip_conflicts() -> None:
    target = _target_df()
    incoming = pd.DataFrame({"DEPT": [1000.0, 1000.5, 1001.0], "GR": [70.0, 71.0, 72.0]})
    plan = build_curve_import_plan(target, incoming, conflict_policy="skip", match_policy="exact")

    result = merge_imported_curves(target, incoming, plan)

    assert result.imported_curves == ()
    assert result.skipped_curves == ("GR",)
    assert result.warnings


def test_read_curve_import_csv_and_manifest(tmp_path: Path) -> None:
    path = tmp_path / "curves.csv"
    path.write_text("DEPT,RHOB\n1000,2.31\n1001,2.36\n", encoding="utf-8")

    incoming = read_curve_import_csv(path)
    plan = build_curve_import_plan(_target_df(), incoming)
    result = merge_imported_curves(_target_df(), incoming, plan)
    manifest = build_curve_import_manifest(result)

    assert "RHOB" in incoming.columns
    assert manifest["schema"] == "gas-ratio-pro/las-curve-import-manifest/v1"
    assert manifest["imported_curves"] == ["RHOB"]


def test_import_curve_specs_from_table_ignores_depth_column() -> None:
    incoming = pd.DataFrame({"DEPT": [1.0, 2.0], "C1": [100.0, 120.0], "C2": [20.0, 25.0]})

    specs = import_curve_specs_from_table(incoming, units={"C1": "ppm", "C2": "ppm"})

    assert [spec.mnemonic for spec in specs] == ["C1", "C2"]
    assert [spec.unit for spec in specs] == ["PPM", "PPM"]


def test_invalid_plan_returns_issue_table_without_merging() -> None:
    incoming = pd.DataFrame({"DEPT": [1.0, 2.0], "C1": [1.0, 2.0]})
    plan = build_curve_import_plan(_target_df(), incoming, curves=["MISSING"])
    result = merge_imported_curves(_target_df(), incoming, plan)

    assert result.imported_curves == ()
    assert result.issues[0].code == "missing_import_curve"
    assert curve_import_issue_table_rows(result.issues)[0]["severity"] == "error"
