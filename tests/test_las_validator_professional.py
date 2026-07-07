import pandas as pd

from las_editor.header_editor import build_default_header_cards, make_header_card
from las_editor.las_validator import (
    detect_las_sections,
    render_validation_report,
    validate_curve_ascii_alignment,
    validate_las_sections,
    validate_las_workspace,
    validation_table_rows,
)


def _cards():
    return build_default_header_cards(
        well_name="WELL-1",
        start_depth=1000.0,
        stop_depth=1000.2,
        step=0.1,
        curves=(
            {"mnemonic": "GR", "unit": "API", "description": "Gamma ray"},
            {"mnemonic": "RT", "unit": "OHMM", "description": "Resistivity"},
        ),
    )


def _ascii():
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.1, 1000.2],
            "GR": [80.0, 82.0, 81.0],
            "RT": [10.0, 11.0, 12.0],
        }
    )


def test_detect_las_sections_from_text():
    text = "~Version\nVERS. 2.0\n~Well\nWELL. TEST\n~Curve\nDEPT.M\n~Ascii\n1 2"

    sections = detect_las_sections(text)

    assert sections == ("~Version", "~Well", "~Curve", "~ASCII")


def test_validate_las_sections_reports_missing_ascii():
    issues = validate_las_sections(("~Version", "~Well", "~Curve", "~Parameter"))

    assert any(issue.code == "SECTION_MISSING" and issue.section == "~ASCII" for issue in issues)


def test_validate_workspace_passes_for_consistent_header_and_ascii():
    report = validate_las_workspace(cards=_cards(), ascii_data=_ascii())

    assert report.status in {"passed", "warning"}  # optional ~Other may add info only
    assert report.error_count == 0
    assert report.summary["ascii_row_count"] == 3
    assert report.summary["ascii_curve_count"] == 3


def test_validate_workspace_reports_duplicate_depth_and_step_mismatch():
    df = pd.DataFrame({"DEPT": [1000.0, 1000.1, 1000.1], "GR": [1, 2, 3], "RT": [4, 5, 6]})

    report = validate_las_workspace(cards=_cards(), ascii_data=df)

    codes = {finding.code for finding in report.findings}
    assert "DUPLICATE_DEPTH" in codes
    assert report.error_count >= 1


def test_validate_alignment_reports_missing_curve_card():
    df = _ascii()
    df["POR"] = [0.1, 0.2, 0.3]

    issues = validate_curve_ascii_alignment(_cards(), df)

    assert any(issue.code == "ASCII_COLUMN_WITHOUT_CURVE_CARD" and issue.mnemonic == "POR" for issue in issues)


def test_validate_alignment_reports_curve_without_ascii_column():
    cards = _cards() + (make_header_card("Curve", "NPHI", unit="V/V", description="Neutron"),)

    issues = validate_curve_ascii_alignment(cards, _ascii())

    assert any(issue.code == "CURVE_CARD_WITHOUT_ASCII_COLUMN" and issue.mnemonic == "NPHI" for issue in issues)


def test_validation_table_and_markdown_report_are_ui_ready():
    report = validate_las_workspace(cards=_cards(), ascii_data=_ascii())

    rows = validation_table_rows(report.findings)
    text = render_validation_report(report)

    assert isinstance(rows, tuple)
    assert "LAS Validation Report" in text
    assert "Status:" in text
