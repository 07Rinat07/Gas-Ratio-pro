from __future__ import annotations

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval, HydrocarbonIntervalResult
from reports.executive_summary import ExecutiveSummary
from reports.presentation_model import PresentationMetadata, build_presentation_model
from reports.well_log_plot import adaptive_detail_padding, group_intervals_for_report
from tests.visual_rebaseline_helpers import assert_visual_rebaseline


def interval(top: float, base: float, fluid: str, confidence: int) -> HydrocarbonInterval:
    return HydrocarbonInterval(
        top=top,
        base=base,
        sample_count=10,
        fluid_type=fluid,
        confidence="high",
        interpretation=fluid,
        confidence_score=confidence,
    )


def test_nearby_intervals_share_detail_page_and_distant_intervals_split() -> None:
    groups = group_intervals_for_report(
        (
            interval(1000, 1005, "oil", 90),
            interval(1010, 1014, "gas", 80),
            interval(1200, 1208, "condensate", 85),
        ),
        merge_gap_m=12,
    )
    assert len(groups) == 2
    assert len(groups[0].intervals) == 2
    assert groups[0].top == 1000
    assert groups[0].base == 1014


def test_client_profile_limits_detail_pages() -> None:
    intervals = tuple(interval(1000 + i * 50, 1005 + i * 50, "oil", 60 + i) for i in range(10))
    rows = pd.DataFrame({
        "depth": [995 + i for i in range(520)],
        "c1": [float(i % 10) for i in range(520)],
        "c2": [float(i % 7) for i in range(520)],
    })
    result = HydrocarbonIntervalResult(intervals=intervals, rows=rows)
    summary = ExecutiveSummary(title="Сводка", overall_assessment="", items=(), main_intervals=())
    model = build_presentation_model(
        result=result,
        source_df=rows,
        executive_summary=summary,
        metadata=PresentationMetadata(report_profile="client"),
    )
    assert model.well_log_plot is not None
    details = model.detail_well_log_plots
    assert_visual_rebaseline(
        "tests/test_report_interval_pages_v222_13.py::test_client_profile_limits_detail_pages",
        {
            "detail_page_limit": len(details),
            "figure_count": len(model.figures),
            "overview_report_kind": str(model.well_log_plot.report_kind),
            "detail_report_kinds": [str(item.report_kind) for item in details],
            "detail_interval_counts": [len(item.report_intervals) for item in details],
            "detail_depth_ranges": [[float(item.depth_start), float(item.depth_stop)] for item in details],
        },
    )

def test_detail_padding_is_adaptive() -> None:
    assert adaptive_detail_padding(1000, 1001) == 2.0
    assert adaptive_detail_padding(1000, 1006) == 5.0
    assert adaptive_detail_padding(1000, 1020) == 10.0
    assert adaptive_detail_padding(1000, 1100) == 25.0
