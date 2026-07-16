from dataclasses import dataclass

from reports.report_design_compat import (
    build_report_design,
    construct_compatible_dataclass,
)


def test_current_report_design_accepts_document_locale():
    design = build_report_design(document_code="GRP-TEST", document_locale="kk")
    assert design.document_code == "GRP-TEST"
    assert design.document_locale == "kk"


def test_legacy_frozen_design_receives_deferred_optional_field():
    @dataclass(frozen=True)
    class LegacyReportDesign:
        document_code: str = "GRP-REPORT"

    design = construct_compatible_dataclass(
        LegacyReportDesign,
        document_code="GRP-LEGACY",
        document_locale="en",
    )
    assert design.document_code == "GRP-LEGACY"
    assert design.document_locale == "en"


def test_unknown_optional_fields_do_not_break_constructor():
    @dataclass
    class MinimalDesign:
        title: str = "Report"

    design = construct_compatible_dataclass(
        MinimalDesign,
        title="Updated",
        future_option=True,
    )
    assert design.title == "Updated"
    assert design.future_option is True


def test_streamlit_export_panel_uses_compat_constructor():
    from pathlib import Path

    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert source.count("build_report_design(") >= 2
    assert "preview_design = ReportDesign(" not in source
    assert "report_design = ReportDesign(" not in source
