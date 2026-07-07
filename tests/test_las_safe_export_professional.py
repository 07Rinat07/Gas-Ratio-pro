from __future__ import annotations

from pathlib import Path

from las_editor.las_safe_export import (
    LAS_EXPORT_SCHEMA,
    build_las_export_manifest,
    builtin_las_template_profiles,
    create_las_spec_from_template,
    export_las_document_safely,
    export_las_text_safely,
    get_las_template_profile,
    las_template_table_rows,
    validate_safe_export_request,
)
from las_editor.las_creator import build_las_text, create_las_dataframe


def test_builtin_template_profiles_are_ui_ready():
    profiles = builtin_las_template_profiles()
    names = {profile.name for profile in profiles}

    assert {"empty", "mud_gas", "petrophysics"}.issubset(names)

    rows = las_template_table_rows(profiles)
    mud_gas = next(row for row in rows if row["name"] == "mud_gas")
    assert mud_gas["curve_count"] >= 1
    assert "C1" in mud_gas["curves"]


def test_create_las_spec_from_template_merges_metadata():
    spec = create_las_spec_from_template(
        "petrophysics",
        well_name="Well-01",
        start_depth=100,
        stop_depth=101,
        step=0.5,
        company="Test Company",
    )

    assert spec.well_name == "Well-01"
    assert spec.company == "Test Company"
    assert any(curve.mnemonic == "GR" for curve in spec.curves)
    assert get_las_template_profile("petrophysics").title


def test_safe_export_blocks_source_overwrite(tmp_path: Path):
    source = tmp_path / "source.las"
    source.write_text("old", encoding="utf-8")

    target, issues = validate_safe_export_request(source, source_path=source)

    assert target == source
    assert any(issue.code == "SOURCE_OVERWRITE_BLOCKED" for issue in issues)


def test_safe_export_blocks_existing_target_without_overwrite(tmp_path: Path):
    target = tmp_path / "target.las"
    target.write_text("old", encoding="utf-8")

    manifest = build_las_export_manifest("~Version\n", target)

    assert manifest.schema == LAS_EXPORT_SCHEMA
    assert manifest.status == "blocked"
    assert any(issue.code == "TARGET_ALREADY_EXISTS" for issue in manifest.issues)


def test_export_las_text_safely_writes_new_file(tmp_path: Path):
    target = tmp_path / "exports" / "new_file"
    manifest = export_las_text_safely("~Version\nVERS. 2.0 : Version\n", target)

    written = tmp_path / "exports" / "new_file.las"
    assert manifest.is_ready
    assert written.exists()
    assert written.read_text(encoding="utf-8").startswith("~Version")


def test_export_las_document_safely_from_template(tmp_path: Path):
    spec = create_las_spec_from_template("mud_gas", well_name="Gas-01", start_depth=10, stop_depth=11, step=0.5)
    df = create_las_dataframe(spec)
    target = tmp_path / "gas_01.las"

    manifest = export_las_document_safely(spec, target, dataframe=df)

    assert manifest.is_ready
    assert manifest.curve_count == len(df.columns)
    assert manifest.row_count == len(df)
    assert target.read_text(encoding="utf-8").count("~ASCII") == 1


def test_export_las_document_does_not_overwrite_source_even_when_overwrite_allowed(tmp_path: Path):
    spec = create_las_spec_from_template("empty", well_name="Safe", start_depth=0, stop_depth=1, step=1)
    source = tmp_path / "safe.las"
    source.write_text(build_las_text(spec), encoding="utf-8")

    manifest = export_las_document_safely(spec, source, source_path=source, allow_overwrite=True)

    assert manifest.status == "blocked"
    assert any(issue.code == "SOURCE_OVERWRITE_BLOCKED" for issue in manifest.issues)
