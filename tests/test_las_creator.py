from __future__ import annotations

import pandas as pd
import pytest

from importers.las_importer import load_las_raw
from las_editor.las_creator import (
    LasCurveSpec,
    add_las_curve,
    build_las_creation_spec,
    builtin_las_templates,
    create_las_document,
    delete_las_curve,
    validate_las_creation,
)


def test_las_creation_wizard_builds_valid_mud_gas_las_document(tmp_path):
    spec = build_las_creation_spec(
        well_name="Well-101",
        start_depth="1000,0",
        stop_depth=1000.4,
        step=0.2,
        template_name="mud_gas",
        uwi="UWI-101",
        field="Demo Field",
    )

    result = create_las_document(spec)

    assert not [issue for issue in result.issues if issue.severity == "error"]
    assert list(result.data["DEPT"]) == [1000.0, 1000.2, 1000.4]
    assert "C1" in result.data.columns
    assert "~Version" in result.las_text
    assert "~Well" in result.las_text
    assert "~Curve" in result.las_text
    assert "~Parameter" in result.las_text
    assert "~ASCII" in result.las_text

    path = tmp_path / "created.las"
    path.write_bytes(result.las_bytes)
    loaded = load_las_raw(path)

    assert list(loaded.iloc[0, :3]) == ["DEPT", "C1", "C2"]
    assert loaded.attrs["las_units"]["DEPT"] == "M"


def test_las_creation_supports_custom_curves_and_sanitizes_mnemonics():
    spec = build_las_creation_spec(
        well_name="Well A",
        start_depth=1.0,
        stop_depth=1.2,
        step=0.2,
        curves=[{"mnemonic": "total gas", "unit": "ppm", "description": "Total gas"}, "123 bad curve"],
    )
    result = create_las_document(spec)

    assert "TOTAL_GAS" in result.data.columns
    assert "C123_BAD_CURVE" in result.data.columns
    assert "TOTAL_GAS.PPM" in result.las_text


def test_las_curve_manager_adds_and_deletes_non_depth_curves():
    spec = build_las_creation_spec(well_name="Well", start_depth=10, stop_depth=10.5, step=0.5)
    result = create_las_document(spec)

    with_gr = add_las_curve(result.data, LasCurveSpec("GR", "API", "Gamma ray"))
    assert "GR" in with_gr.columns
    assert with_gr.attrs["las_units"]["GR"] == "API"

    without_gr = delete_las_curve(with_gr, "GR")
    assert "GR" not in without_gr.columns

    with pytest.raises(ValueError):
        delete_las_curve(without_gr, "DEPT")


def test_las_creation_validator_reports_invalid_depth_range_and_sections():
    spec = build_las_creation_spec(well_name="Bad", start_depth=2, stop_depth=1, step=0.2)
    issues = validate_las_creation(spec, pd.DataFrame({"DEPT": [2, 1]}), las_text="~Version\n")
    codes = {issue.code for issue in issues}

    assert "DEPTH_RANGE_INVALID" in codes
    assert "SECTION_MISSING" in codes


def test_builtin_las_templates_are_available_for_ui():
    assert "empty" in builtin_las_templates()
    assert "mud_gas" in builtin_las_templates()
    assert "petrophysics" in builtin_las_templates()
