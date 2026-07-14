from projects.interpretation_interval_analysis import (
    InterpretationIntervalFilter,
    filter_interpretation_intervals,
    summarize_interpretation_intervals,
)
from projects.interpretation_intervals import build_interpretation_interval


def _interval(label, top, base, interval_type="gas", source="manual", comment=""):
    return build_interpretation_interval(
        label=label,
        top=top,
        base=base,
        interval_type=interval_type,
        source=source,
        comment=comment,
    )


def test_filter_combines_text_type_source_depth_and_thickness():
    intervals = (
        _interval("A", 100, 110, "gas", "manual", "target"),
        _interval("B", 112, 125, "water", "import", "target"),
        _interval("C", 130, 134, "gas", "manual", "other"),
    )
    result = filter_interpretation_intervals(
        intervals,
        InterpretationIntervalFilter(
            query="target",
            interval_types=("gas",),
            sources=("manual",),
            depth_top=105,
            depth_base=120,
            min_thickness=5,
            max_thickness=12,
        ),
    )
    assert [item.label for item in result] == ["A"]


def test_depth_filter_requires_positive_intersection():
    intervals = (_interval("touch", 90, 100), _interval("cross", 99, 101))
    result = filter_interpretation_intervals(
        intervals, InterpretationIntervalFilter(depth_top=100, depth_base=110)
    )
    assert [item.label for item in result] == ["cross"]


def test_summary_calculates_union_coverage_without_double_counting_overlap():
    intervals = (
        _interval("A", 100, 110, "gas"),
        _interval("B", 105, 120, "gas"),
        _interval("C", 130, 135, "water", source="import"),
    )
    summary = summarize_interpretation_intervals(intervals)
    assert summary.count == 3
    assert summary.total_thickness == 30
    assert summary.covered_depth == 25
    assert summary.min_top == 100
    assert summary.max_base == 135
    assert summary.type_count == 2
    assert summary.source_count == 2
    assert [(row.interval_type, row.count) for row in summary.by_type] == [("gas", 2), ("water", 1)]


def test_invalid_filter_ranges_are_rejected():
    intervals = (_interval("A", 100, 110),)
    for criteria in (
        InterpretationIntervalFilter(depth_top=120, depth_base=110),
        InterpretationIntervalFilter(min_thickness=-1),
        InterpretationIntervalFilter(min_thickness=10, max_thickness=5),
    ):
        try:
            filter_interpretation_intervals(intervals, criteria)
        except ValueError:
            pass
        else:
            raise AssertionError("ValueError expected")
