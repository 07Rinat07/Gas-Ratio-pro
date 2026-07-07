from __future__ import annotations

import pandas as pd

from las_editor.las_creation_wizard import (
    LasCreationMode,
    build_las_creation_wizard_draft,
    build_las_creation_wizard_preview_v2,
    finalize_las_creation_wizard,
    las_creation_mode_rows,
    las_creation_template_rows,
    summarize_source_las,
    wizard_issue_rows,
    wizard_step_rows,
)


def test_creation_wizard_modes_and_templates_are_ui_ready():
    modes = las_creation_mode_rows()
    templates = las_creation_template_rows()

    assert {row["mode"] for row in modes} >= {"empty", "template", "from_las", "from_csv", "from_excel", "manual"}
    assert any(row["template"] == "mud_gas" and "C1" in row["curves"] for row in templates)


def test_creation_wizard_builds_template_preview_and_finalize_result():
    draft = build_las_creation_wizard_draft(
        mode=LasCreationMode.TEMPLATE,
        well_name="WELL_A",
        start_depth=1000,
        stop_depth=1001,
        step=0.5,
        template_name="mud_gas",
        company="Demo Oil",
        field="Field A",
    )
    preview = build_las_creation_wizard_preview_v2(draft)
    final = finalize_las_creation_wizard(draft)

    assert preview.can_finalize is True
    assert preview.data.shape[0] == 3
    assert "C1" in preview.data.columns
    assert "TGAS" in preview.data.columns
    assert "~ASCII" in preview.las_text
    assert final.filename.endswith(".las")
    assert final.las_bytes.startswith(b"~Version")
    assert final.journal_entry.status.value == "completed"
    assert final.journal_entry.creates_copy is True


def test_creation_wizard_can_clone_curve_structure_from_source_las():
    source = """
~Version
VERS. 2.0 : version
WRAP. NO : wrap
~Well
STRT.M 500 : start
STOP.M 501 : stop
STEP.M 0.5 : step
WELL. SOURCE_WELL : well
~Curve
DEPT.M : Depth
GR.API : Gamma ray
RT.OHMM : Deep resistivity
~ASCII
500 80 12
500.5 81 13
501 82 14
"""
    summary = summarize_source_las(source)
    draft = build_las_creation_wizard_draft(mode="from_las", well_name="NEW_WELL", source_las_text=source)
    preview = build_las_creation_wizard_preview_v2(draft)

    assert summary.curve_count == 2
    assert {curve.mnemonic for curve in summary.curves} == {"GR", "RT"}
    assert preview.data["DEPT"].tolist() == [500.0, 500.5, 501.0]
    assert "GR" in preview.data.columns
    assert "RT" in preview.data.columns


def test_creation_wizard_can_prepare_from_tabular_source():
    df = pd.DataFrame({"DEPTH": [10.0, 10.5, 11.0], "GR": [80, 81, 82], "GAS_SUM": [1.2, 1.5, 2.0]})
    draft = build_las_creation_wizard_draft(mode="from_csv", well_name="CSV_WELL", source_dataframe=df)
    preview = build_las_creation_wizard_preview_v2(draft)

    assert preview.data["DEPT"].tolist() == [10.0, 10.5, 11.0]
    assert "GR" in preview.data.columns
    assert "GAS_SUM" in preview.data.columns
    assert preview.can_finalize is True


def test_creation_wizard_reports_validation_errors_before_finalize():
    draft = build_las_creation_wizard_draft(well_name="BAD", start_depth=100, stop_depth=90, step=0.5)
    preview = build_las_creation_wizard_preview_v2(draft)
    rows = wizard_issue_rows(preview.issues)

    assert preview.can_finalize is False
    assert any(row["code"] == "DEPTH_RANGE_INVALID" for row in rows)
    assert any(row["completed"] is False for row in wizard_step_rows(draft))
