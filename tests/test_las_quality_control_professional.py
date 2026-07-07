import pandas as pd

from las_editor.las_quality_control import (
    LAS_QUALITY_CONTROL_SCHEMA,
    build_quality_control_manifest,
    builtin_quality_profiles,
    detect_depth_quality_issues,
    detect_flat_lines,
    detect_null_issues,
    detect_range_issues,
    detect_spikes,
    detect_unit_mismatch,
    quality_issue_table_rows,
    quality_profile_table_rows,
    render_quality_control_report,
    run_las_quality_control,
)


def _qc_df() -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.5, 1001.0, 1001.0, 1002.5, 1003.0, 1003.5],
            "GR": [80.0, 81.0, 82.0, 300.0, 83.0, -1.0, 83.0],
            "POR": [0.10, 0.10, 0.10, 0.10, -999.25, 1.2, 0.10],
            "C1": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
        }
    )
    df.attrs["las_units"] = {"GR": "GAPI", "POR": "PCT", "C1": "PPM"}
    return df


def test_depth_quality_detects_duplicates_and_missing_intervals():
    issues = detect_depth_quality_issues(_qc_df(), expected_step=0.5)
    codes = {issue.code for issue in issues}

    assert "duplicate_depth" in codes
    assert "non_monotonic_depth" in codes
    assert "missing_depth_interval" in codes


def test_null_range_spike_flatline_and_unit_checks_are_reported():
    df = _qc_df()
    codes = {issue.code for issue in detect_null_issues(df)}
    codes |= {issue.code for issue in detect_range_issues(df)}
    codes |= {issue.code for issue in detect_spikes(df)}
    codes |= {issue.code for issue in detect_flat_lines(df)}
    codes |= {issue.code for issue in detect_unit_mismatch(df)}

    assert "missing_values" in codes
    assert "negative_value" in codes
    assert "above_expected_range" in codes
    assert "curve_spike" in codes
    assert "flat_line" in codes
    assert "unit_mismatch" in codes


def test_complete_quality_control_report_manifest_and_markdown_are_ui_ready():
    report = run_las_quality_control(_qc_df(), expected_step=0.5)
    manifest = build_quality_control_manifest(report)
    markdown = render_quality_control_report(report)

    assert report.schema == LAS_QUALITY_CONTROL_SCHEMA
    assert report.summary["issue_count"] > 0
    assert report.summary["status"] == "failed"
    assert manifest["schema"] == LAS_QUALITY_CONTROL_SCHEMA
    assert manifest["issues"]
    assert "LAS Quality Control Report" in markdown
    assert quality_issue_table_rows(report.issues)


def test_builtin_profiles_are_available_as_ui_rows():
    profiles = builtin_quality_profiles()
    rows = quality_profile_table_rows(profiles)

    assert any(profile.mnemonic == "GR" for profile in profiles)
    assert any(row["mnemonic"] == "POR" for row in rows)
