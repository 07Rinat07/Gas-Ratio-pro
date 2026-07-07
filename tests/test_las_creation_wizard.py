from __future__ import annotations

from las_editor.las_creation_wizard import (
    DEFAULT_CURVE_LIBRARY,
    build_las_creation_manifest,
    build_las_creation_wizard_draft,
    curve_library_table_rows,
    las_creation_visible_tools,
    run_las_creation_wizard,
    template_table_rows,
)


def test_las_creation_wizard_tools_are_visible_without_loaded_las():
    tools = las_creation_visible_tools()

    assert "New LAS" in tools
    assert "Template Manager" in tools
    assert "Header Builder" in tools
    assert "Depth Generator" in tools
    assert "Curve Library" in tools
    assert "ASCII Builder" in tools
    assert "Validate Before Save" in tools


def test_las_creation_wizard_creates_new_las_from_template():
    draft = build_las_creation_wizard_draft(
        well_name="Well-202",
        start_depth=1500,
        stop_depth=1501,
        step=0.5,
        template_name="petrophysics",
        field="Demo Field",
    )

    result = run_las_creation_wizard(draft)

    assert result.can_save is True
    assert result.document is not None
    assert list(result.document.data["DEPT"]) == [1500.0, 1500.5, 1501.0]
    assert "GR" in result.document.data.columns
    assert "RHOB" in result.document.data.columns
    assert "~ASCII" in result.document.las_text


def test_las_creation_wizard_manifest_for_ui():
    draft = build_las_creation_wizard_draft(
        well_name="Well-UI",
        start_depth=1,
        stop_depth=2,
        step=1,
        curves=["GR"],
    )
    result = run_las_creation_wizard(draft)
    manifest = build_las_creation_manifest(result)

    assert manifest["visible_without_loaded_las"] is True
    assert manifest["can_save"] is True
    assert manifest["row_count"] == 2
    assert manifest["curve_count"] == 1


def test_las_creation_wizard_tables_for_frontend():
    curve_rows = curve_library_table_rows(DEFAULT_CURVE_LIBRARY)
    template_rows = template_table_rows()

    assert any(row["mnemonic"] == "GR" for row in curve_rows)
    assert any(row["template"] == "mud_gas" for row in template_rows)
