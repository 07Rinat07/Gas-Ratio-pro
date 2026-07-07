import pandas as pd

from las_editor.header_editor import make_header_card
from las_editor.las_diagnostics_center import (
    diagnostics_finding_table_rows,
    render_diagnostics_report,
    run_las_diagnostics_center,
)


def _cards():
    return [
        make_header_card("Version", "VERS", value="2.0"),
        make_header_card("Version", "WRAP", value="NO"),
        make_header_card("Well", "STRT", unit="M", value="1000.0"),
        make_header_card("Well", "STOP", unit="M", value="1001.0"),
        make_header_card("Well", "STEP", unit="M", value="0.5"),
        make_header_card("Well", "NULL", value="-999.25"),
        make_header_card("Curve", "DEPT", unit="M"),
        make_header_card("Curve", "GR", unit="API"),
        make_header_card("Parameter", "RUN", value="1"),
    ]


def test_diagnostics_center_aggregates_validation_quality_and_depth_findings_without_mutation() -> None:
    df = pd.DataFrame({"DEPT": [1000.0, 1001.0, 1000.5], "GR": [80.0, -5.0, 90.0]})
    original = df.copy(deep=True)

    report = run_las_diagnostics_center(df, cards=_cards(), expected_step=0.5)
    codes = {finding.code for finding in report.findings}
    sources = set(report.summary["sources"])

    assert df.equals(original)
    assert report.schema.endswith("las-diagnostics-center/v1")
    assert {"validator", "quality_control", "depth_repair"}.issubset(sources)
    assert "DEPTH_DECREASES" in codes
    assert "negative_value" in codes
    assert report.status in {"warning", "failed"}
    assert report.manifest["summary"]["finding_count"] == len(report.findings)


def test_diagnostics_center_table_rows_and_markdown_report_are_ui_ready() -> None:
    df = pd.DataFrame({"DEPT": [1.0, 2.0, 3.0], "GR": [70.0, 72.0, 75.0]})

    report = run_las_diagnostics_center(df, include_validation=False)
    rows = diagnostics_finding_table_rows(report.findings)
    markdown = render_diagnostics_report(report)

    assert isinstance(rows, tuple)
    assert "LAS Diagnostics Center Report" in markdown
    assert "read-only mode" in markdown
    assert report.summary["row_count"] == 3
