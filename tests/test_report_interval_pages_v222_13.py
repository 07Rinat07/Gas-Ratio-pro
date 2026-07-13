from __future__ import annotations

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval, HydrocarbonIntervalResult
from reports.executive_summary import ExecutiveSummary
from reports.presentation_model import PresentationMetadata, build_presentation_model
from reports.well_log_plot import adaptive_detail_padding, group_intervals_for_report


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
    assert len(model.detail_well_log_plots) == 5
    assert len(model.figures) == 6
    meta = dict(model.detail_well_log_plots[0].figure.layout.meta["gas_ratio_report_legend"])
    assert meta["report_kind"] == "detail"
    assert meta["intervals"]


def test_detail_padding_is_adaptive() -> None:
    assert adaptive_detail_padding(1000, 1001) == 2.0
    assert adaptive_detail_padding(1000, 1006) == 5.0
    assert adaptive_detail_padding(1000, 1020) == 10.0
    assert adaptive_detail_padding(1000, 1100) == 25.0
