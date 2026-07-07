import pandas as pd

from las_editor.formation_evaluation_summary import (
    FORMATION_EVALUATION_SCHEMA,
    build_formation_evaluation_manifest,
    build_formation_evaluation_summary,
    formation_evaluation_interval_table_rows,
    formation_evaluation_issue_table_rows,
    render_formation_evaluation_markdown_report,
)


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 1001.0, 1002.0, 1003.0, 1004.0],
            "GR": [55.0, 58.0, 62.0, 90.0, 95.0],
            "RT": [22.0, 20.0, 18.0, 5.0, 4.0],
            "POR": [0.18, 0.17, 0.16, 0.08, 0.07],
            "SW": [0.35, 0.40, 0.42, 0.8, 0.85],
            "NG": [1.0, 1.0, 1.0, 0.0, 0.0],
            "C1": [100.0, 80.0, 60.0, 5.0, 4.0],
            "C2": [10.0, 8.0, 6.0, 0.2, 0.2],
            "C3": [8.0, 6.0, 5.0, 0.1, 0.1],
            "C4": [4.0, 3.0, 2.0, 0.05, 0.05],
            "C5": [2.0, 1.5, 1.0, 0.02, 0.02],
        }
    )


def test_summary_builds_default_intervals_and_embedded_qc_mud_gas_results():
    summary = build_formation_evaluation_summary(sample_frame(), well_name="WELL-01")

    assert summary.schema == FORMATION_EVALUATION_SCHEMA
    assert summary.well_name == "WELL-01"
    assert summary.depth_curve == "DEPT"
    assert summary.qc_report is not None
    assert summary.mud_gas_result is not None
    assert summary.intervals
    assert summary.intervals[0].sample_count >= 1


def test_summary_accepts_explicit_intervals_and_calculates_property_averages():
    summary = build_formation_evaluation_summary(
        sample_frame(),
        intervals=(("Reservoir A", 1000.0, 1002.0), ("Shaly interval", 1003.0, 1004.0)),
    )

    first = summary.intervals[0]
    second = summary.intervals[1]
    assert first.name == "Reservoir A"
    assert first.property_averages["POR"] == 0.17
    assert first.reservoir_flag in {"probable_reservoir", "possible_reservoir", "hydrocarbon_indication"}
    assert second.property_averages["NG"] == 0.0


def test_manifest_contains_counts_and_sources():
    summary = build_formation_evaluation_summary(
        sample_frame(),
        source_references=("docs/sources/application-of-mud-gas-analysis-for-reservoir-evaluation.pdf",),
    )
    manifest = build_formation_evaluation_manifest(summary)

    assert manifest["schema"] == FORMATION_EVALUATION_SCHEMA
    assert manifest["interval_count"] == len(summary.intervals)
    assert manifest["mud_gas_row_count"] == 5
    assert manifest["source_references"]


def test_ui_helpers_are_serializable():
    summary = build_formation_evaluation_summary(sample_frame())
    interval_rows = formation_evaluation_interval_table_rows(summary.intervals)
    issue_rows = formation_evaluation_issue_table_rows(summary.issues)

    assert interval_rows
    assert "reservoir_flag" in interval_rows[0]
    assert isinstance(issue_rows, list)


def test_markdown_report_contains_interval_table_and_sources():
    summary = build_formation_evaluation_summary(
        sample_frame(),
        well_name="WELL-02",
        source_references=("docs/sources/Lab_4_cube_properties.pdf",),
    )
    report = render_formation_evaluation_markdown_report(summary)

    assert "Formation Evaluation Summary" in report
    assert "WELL-02" in report
    assert "## Interval summary" in report
    assert "docs/sources/Lab_4_cube_properties.pdf" in report


def test_empty_dataframe_returns_error_issue():
    summary = build_formation_evaluation_summary(pd.DataFrame())

    assert not summary.intervals
    assert any(issue.code == "empty_dataframe" for issue in summary.issues)
