import pandas as pd

from las_editor.header_editor import build_default_header_cards
from las_editor.las_validator import (
    LASValidator,
    LasValidatorConfig,
    recommended_validator_actions,
    validate_las_workspace,
    validate_numeric_ranges,
)


def _cards():
    return build_default_header_cards(
        well_name="WELL-A9",
        start_depth=1000.0,
        stop_depth=1000.2,
        step=0.1,
        curves=(
            {"mnemonic": "GR", "unit": "API", "description": "Gamma ray"},
            {"mnemonic": "RT", "unit": "OHMM", "description": "Resistivity"},
        ),
    )


def test_validator_adds_quality_score_to_workspace_report():
    df = pd.DataFrame({"DEPT": [1000.0, 1000.1, 1000.2], "GR": [80.0, 81.0, 82.0], "RT": [10.0, 11.0, 12.0]})

    report = validate_las_workspace(cards=_cards(), ascii_data=df)

    assert 0 <= report.quality_score <= 100
    assert report.summary["quality_score"] == report.quality_score
    assert "Quality score:" in report.summary or report.quality_score > 0


def test_numeric_range_validation_reports_engineering_outliers_without_mutating_data():
    df = pd.DataFrame({"DEPT": [1.0, 2.0], "GR": [90.0, 450.0], "RT": [5.0, -1.0]})
    before = df.copy(deep=True)

    findings = validate_numeric_ranges(df)

    codes = {finding.code for finding in findings}
    assert "CURVE_VALUE_ABOVE_RANGE" in codes
    assert "CURVE_VALUE_BELOW_RANGE" in codes
    pd.testing.assert_frame_equal(df, before)


def test_las_validator_center_returns_ui_ready_payload_and_actions():
    df = pd.DataFrame({"DEPT": [1000.0, 1000.1, 1000.1], "GR": [80.0, 450.0, 90.0], "RT": [10.0, 11.0, 12.0]})
    validator = LASValidator(LasValidatorConfig())

    result = validator.validate_center(cards=_cards(), ascii_data=df)

    assert result.report.error_count >= 1
    assert result.table_rows
    assert "LAS Validation Report" in result.markdown_report
    assert "Open Depth Repair Center" in result.actions
    assert "Open ASCII Spreadsheet" in result.actions


def test_recommended_actions_allow_export_when_no_errors():
    df = pd.DataFrame({"DEPT": [1000.0, 1000.1, 1000.2], "GR": [80.0, 81.0, 82.0], "RT": [10.0, 11.0, 12.0]})
    report = validate_las_workspace(cards=_cards(), ascii_data=df)

    actions = recommended_validator_actions(report)

    assert "Export Center is available" in actions
