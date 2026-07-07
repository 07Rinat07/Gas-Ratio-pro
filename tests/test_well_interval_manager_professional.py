import pandas as pd

from las_editor.formation_evaluation_summary import build_formation_evaluation_summary
from las_editor.well_interval_manager import (
    WELL_INTERVAL_MANAGER_SCHEMA,
    IntervalCutoffSet,
    build_well_interval_manifest,
    build_well_intervals_from_summary,
    calculate_interval_thickness_summary,
    merge_adjacent_intervals,
    render_well_interval_markdown_report,
    split_well_interval,
    well_interval_issue_table_rows,
    well_interval_table_rows,
)


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 1001.0, 1002.0, 1003.0, 1004.0, 1005.0],
            "GR": [55.0, 58.0, 62.0, 90.0, 95.0, 100.0],
            "RT": [22.0, 20.0, 18.0, 5.0, 4.0, 3.0],
            "POR": [0.18, 0.17, 0.16, 0.08, 0.07, 0.05],
            "SW": [0.35, 0.40, 0.42, 0.8, 0.85, 0.9],
            "NG": [1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
            "C1": [100.0, 80.0, 60.0, 5.0, 4.0, 3.0],
            "C2": [10.0, 8.0, 6.0, 0.2, 0.2, 0.1],
            "C3": [8.0, 6.0, 5.0, 0.1, 0.1, 0.05],
            "C4": [4.0, 3.0, 2.0, 0.05, 0.05, 0.02],
            "C5": [2.0, 1.5, 1.0, 0.02, 0.02, 0.01],
        }
    )


def build_summary():
    return build_formation_evaluation_summary(
        sample_frame(),
        well_name="WELL-PAY-01",
        intervals=(("Sand A", 1000.0, 1002.0), ("Shale B", 1003.0, 1005.0)),
        source_references=("docs/sources/application-of-mud-gas-analysis-for-reservoir-evaluation.pdf",),
    )


def test_build_well_intervals_from_summary_detects_pay_and_non_reservoir():
    interval_set = build_well_intervals_from_summary(build_summary())

    assert interval_set.schema == WELL_INTERVAL_MANAGER_SCHEMA
    assert interval_set.well_name == "WELL-PAY-01"
    assert len(interval_set.intervals) == 2
    assert interval_set.intervals[0].interval_type == "pay"
    assert interval_set.intervals[0].pay_thickness == 2.0
    assert interval_set.intervals[1].interval_type in {"gross", "non_reservoir", "net"}


def test_custom_cutoffs_can_make_interval_non_pay():
    interval_set = build_well_intervals_from_summary(
        build_summary(),
        cutoffs=IntervalCutoffSet(porosity_min=0.25),
    )

    assert interval_set.intervals[0].interval_type != "pay"
    assert interval_set.intervals[0].pay_thickness == 0.0


def test_thickness_summary_and_manifest_are_serializable():
    interval_set = build_well_intervals_from_summary(build_summary())
    thickness = calculate_interval_thickness_summary(interval_set.intervals)
    manifest = build_well_interval_manifest(interval_set)

    assert thickness["gross_thickness"] >= thickness["net_thickness"] >= thickness["pay_thickness"]
    assert manifest["schema"] == WELL_INTERVAL_MANAGER_SCHEMA
    assert manifest["thickness"]["pay_thickness"] == thickness["pay_thickness"]
    assert manifest["source_references"]


def test_split_interval_preserves_ratios_and_boundaries():
    interval_set = build_well_intervals_from_summary(build_summary())
    first, second = split_well_interval(interval_set.intervals[0], 1001.0)

    assert first.name.endswith("A")
    assert second.name.endswith("B")
    assert first.base == 1001.0
    assert second.top == 1001.0
    assert first.pay_to_net == 1.0
    assert second.pay_to_net == 1.0


def test_merge_adjacent_intervals_merges_matching_pay_zones():
    interval_set = build_well_intervals_from_summary(
        build_formation_evaluation_summary(
            sample_frame(),
            intervals=(("Pay 1", 1000.0, 1001.0), ("Pay 2", 1001.0, 1002.0)),
        )
    )
    merged = merge_adjacent_intervals(interval_set.intervals, max_gap=0.0, group_by=("interval_type",))

    assert len(merged) == 1
    assert merged[0].top == 1000.0
    assert merged[0].base == 1002.0
    assert merged[0].pay_thickness == 2.0


def test_ui_helpers_and_markdown_report():
    interval_set = build_well_intervals_from_summary(build_summary())
    rows = well_interval_table_rows(interval_set.intervals)
    issue_rows = well_interval_issue_table_rows(interval_set.issues)
    report = render_well_interval_markdown_report(interval_set)

    assert rows
    assert "pay_thickness" in rows[0]
    assert isinstance(issue_rows, list)
    assert "Well Interval & Pay Zone Summary" in report
    assert "WELL-PAY-01" in report
    assert "docs/sources/application-of-mud-gas-analysis-for-reservoir-evaluation.pdf" in report
