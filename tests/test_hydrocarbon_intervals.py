from __future__ import annotations

import pandas as pd

from core.hydrocarbon_intervals import (
    HydrocarbonIntervalRuleSet,
    detect_hydrocarbon_intervals,
    hydrocarbon_interval_table_rows,
)


def test_hydrocarbon_interval_engine_detects_oil_gas_and_condensate_candidates() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0, 1005.0, 1006.0, 1010.0],
            "interpretation": [
                "Газовая залежь",
                "Газовая залежь",
                "Недостаточно данных",
                "Нефтяная залежь",
                "Жирный газ / конденсат",
                "Сухой газ / непродуктивно",
            ],
            "wh": [5.0, 6.0, None, 25.0, 12.0, 0.2],
            "bh": [50.0, 45.0, None, 10.0, 8.0, 120.0],
            "c1_c2": [25.0, 30.0, None, 6.0, 18.0, 90.0],
            "oil_indicator": [0.04, 0.05, None, 0.2, 0.08, 0.03],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0, merge_compatible_fluids=False))

    assert [interval.fluid_type for interval in result.intervals] == ["gas", "oil", "condensate", "gas"]
    assert result.intervals[0].top == 1000.0
    assert result.intervals[0].base == 1001.0
    assert result.intervals[0].sample_count == 2
    assert result.rows["hydrocarbon_candidate"].sum() == 5


def test_hydrocarbon_interval_engine_uses_ratio_fallback_without_text_interpretation() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1500.0, 1500.5, 1501.0],
            "c1_c2": [5.0, 7.0, 20.0],
            "oil_indicator": [0.2, 0.18, 0.08],
            "wh": [22.0, 24.0, 10.0],
            "bh": [8.0, 9.0, 6.0],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=1.0))
    table_rows = hydrocarbon_interval_table_rows(result.intervals)

    assert len(result.intervals) == 1
    assert result.intervals[0].fluid_type in {"oil", "condensate"}
    assert table_rows[0]["top"] == 1500.0
    assert "avg_C1/C2" in table_rows[0]
    assert "Oil indicator" in table_rows[0]["evidence"]
