from __future__ import annotations

from las_editor.las_creator import build_las_text
from las_editor.las_workspace_home import (
    action_table_rows,
    build_las_creation_wizard_preview,
    build_las_workspace_home_state,
    parse_curve_text,
)


def test_las_workspace_home_exposes_create_action_without_loaded_file():
    state = build_las_workspace_home_state()
    rows = action_table_rows(state.actions)

    create = next(row for row in rows if row["action_id"] == "create_las")
    assert create["title"] == "Создать LAS"
    assert create["enabled_without_file"] is True
    assert create["target_panel"] == "creation_wizard"


def test_las_creation_wizard_preview_builds_valid_dataframe_and_text():
    preview = build_las_creation_wizard_preview(
        well_name="WELL_A",
        start_depth=1000,
        stop_depth=1001,
        step=0.5,
        template_name="mud_gas",
        curve_text="GR,API,Gamma ray\nRT,OHMM,Deep resistivity",
    )

    assert preview.row_count == 3
    assert "DEPT" in preview.data.columns
    assert "C1" in preview.data.columns
    assert "GR" in preview.data.columns
    assert "RT" in preview.data.columns
    las_text = build_las_text(preview.spec, preview.data)
    assert "~Version" in las_text
    assert "~Well" in las_text
    assert "~Curve" in las_text
    assert "~ASCII" in las_text


def test_curve_text_parser_accepts_comma_and_pipe_formats():
    curves = parse_curve_text("GR,API,Gamma ray\nRHOB|G/C3|Bulk density")

    assert [curve.mnemonic for curve in curves] == ["GR", "RHOB"]
    assert [curve.unit for curve in curves] == ["API", "G/C3"]
