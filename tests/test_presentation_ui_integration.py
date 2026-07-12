from __future__ import annotations

from reports.presentation_ui import (
    build_presentation_export_ui_state,
    build_report_base_name,
    export_format_by_id,
    export_format_options,
    export_options_from_ui_state,
    normalize_export_format,
    normalize_report_profile,
    profile_by_id,
    report_profile_options,
)


def test_report_profile_options_keep_engineering_first_and_expert_second():
    profiles = report_profile_options()

    assert [profile.id for profile in profiles] == ["engineering", "expert"]
    assert profiles[0].include_technical_appendix is False
    assert profiles[1].include_technical_appendix is True
    assert "технические" not in profiles[0].description.lower()


def test_export_format_options_cover_all_renderers():
    formats = export_format_options()

    assert [option.id for option in formats] == ["pdf", "docx", "png", "svg", "xlsx", "bundle"]
    assert export_format_by_id("pdf").mime_type == "application/pdf"
    assert export_format_by_id("docx").extension == "docx"
    assert export_format_by_id("png").mime_type == "image/png"
    assert export_format_by_id("svg").extension == "svg"
    assert export_format_by_id("xlsx").extension == "xlsx"
    assert export_format_by_id("unknown").id == "pdf"


def test_profile_normalization_is_safe_for_ui_inputs():
    assert normalize_report_profile("expert") == "expert"
    assert normalize_report_profile("Экспертный") == "expert"
    assert normalize_report_profile("engineering") == "engineering"
    assert normalize_report_profile(None) == "engineering"
    assert profile_by_id("bad-value").id == "engineering"


def test_export_format_normalization_supports_bundle_aliases():
    assert normalize_export_format("pdf") == "pdf"
    assert normalize_export_format("all") == "bundle"
    assert normalize_export_format("zip") == "bundle"
    assert normalize_export_format("bad") == "pdf"


def test_report_base_name_is_path_safe():
    assert build_report_base_name("../well A", "project/1", "LAS\\source") == "well_A_project_1_LAS_source"


def test_ui_state_maps_profile_to_technical_appendix(tmp_path):
    state = build_presentation_export_ui_state(
        profile="expert",
        export_format="bundle",
        output_dir=tmp_path,
        base_name_parts=("Karakuik", "Well 12"),
        include_figures=True,
    )

    assert state.profile == "expert"
    assert state.export_format == "bundle"
    assert state.include_technical_appendix is True
    assert state.base_name == "Karakuik_Well_12"

    options = export_options_from_ui_state(state)
    assert options.output_dir == tmp_path
    assert options.base_name == "Karakuik_Well_12"
    assert options.include_technical_appendix is True
