from __future__ import annotations

import pandas as pd

from core.hydrocarbon_intervals import (
    HydrocarbonIntervalRuleSet,
    detect_hydrocarbon_intervals,
    hydrocarbon_interval_marker_rows,
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


def test_hydrocarbon_interval_engine_adds_printable_notes_and_thickness() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1200.0, 1201.5],
            "wh": [28.0, 30.0],
            "bh": [9.0, 11.0],
            "c1_c2": [6.0, 7.0],
            "oil_indicator": [0.18, 0.22],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))
    interval = result.intervals[0]
    table_rows = hydrocarbon_interval_table_rows(result.intervals)

    assert interval.fluid_type == "oil"
    assert interval.thickness == 1.5
    assert interval.confidence in {"medium", "high"}
    assert "Нефтяной интервал" in interval.engineering_note
    assert "предварительный" in interval.engineering_note
    assert table_rows[0]["thickness"] == 1.5
    assert "engineering_note" in table_rows[0]


def test_hydrocarbon_interval_engine_keeps_transition_candidates_when_enabled() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1300.0, 1301.0],
            "interpretation": ["Переходный нефтегазовый признак", "boundary anomaly"],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))

    assert len(result.intervals) == 1
    assert result.intervals[0].fluid_type in {"mixed", "transition"}
    assert result.rows["hydrocarbon_candidate"].all()
    assert result.schema.endswith("/v6")


def test_hydrocarbon_interval_engine_builds_graph_marker_rows() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1600.0, 1601.0],
            "interpretation": ["Нефтяная залежь", "Нефтяная залежь"],
            "wh": [26.0, 28.0],
            "bh": [9.0, 10.0],
            "c1_c2": [6.0, 7.0],
            "oil_indicator": [0.19, 0.21],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))
    markers = hydrocarbon_interval_marker_rows(result.intervals)

    assert markers[0]["marker_id"] == "HC-001"
    assert markers[0]["label"] == "OIL"
    assert markers[0]["line_color"].startswith("#")
    assert "1600" in markers[0]["annotation"]


def test_hydrocarbon_interval_engine_distinguishes_directional_oil_gas_labels() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1700.0, 1701.0, 1705.0, 1706.0],
            "interpretation": [
                "Газонефтяной смешанный интервал",
                "Газонефтяной смешанный интервал",
                "Нефтегазовый смешанный интервал",
                "Нефтегазовый смешанный интервал",
            ],
            "wh": [12.0, 13.0, 26.0, 28.0],
            "bh": [40.0, 42.0, 10.0, 11.0],
        }
    )

    result = detect_hydrocarbon_intervals(
        frame,
        rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0, merge_compatible_fluids=False),
    )

    assert [interval.fluid_type for interval in result.intervals] == ["gas_oil", "oil_gas"]
    assert result.schema.endswith("/v6")


def test_hydrocarbon_interval_engine_keeps_uncertain_candidates_but_excludes_water() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1800.0, 1801.0, 1810.0],
            "interpretation": ["Сомнительный газовый признак", "ambiguous anomaly", "Водонасыщенный интервал"],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))

    assert len(result.intervals) == 1
    assert result.intervals[0].fluid_type == "uncertain"
    assert result.rows.loc[result.rows["hydrocarbon_fluid_type"] == "water", "hydrocarbon_candidate"].eq(False).all()
    assert "неустойчивый" in " ".join(result.intervals[0].warnings)


def test_hydrocarbon_interval_engine_preserves_explicit_barrier_gaps() -> None:
    frame = pd.DataFrame(
        {
            "top": [2148.2, 2150.2],
            "base": [2150.0, 2154.8],
            "depth": [2148.2, 2150.2],
            "interpretation": ["Газовая залежь", "Газовая залежь"],
            "wh": [7.0, 8.0],
            "bh": [45.0, 48.0],
            "c1_c2": [80.0, 82.0],
            "oil_indicator": [0.04, 0.05],
        }
    )

    result = detect_hydrocarbon_intervals(frame)
    table_rows = hydrocarbon_interval_table_rows(result.intervals)

    assert len(result.intervals) == 2
    assert [(interval.top, interval.base, interval.fluid_type) for interval in result.intervals] == [
        (2148.2, 2150.0, "gas"),
        (2150.2, 2154.8, "gas"),
    ]
    assert table_rows[1]["separated_by_gap"] is True


def test_hydrocarbon_interval_engine_can_merge_explicit_gaps_when_requested() -> None:
    frame = pd.DataFrame(
        {
            "top": [2148.2, 2150.2],
            "base": [2150.0, 2154.8],
            "depth": [2148.2, 2150.2],
            "interpretation": ["Газовая залежь", "Газовая залежь"],
        }
    )

    result = detect_hydrocarbon_intervals(
        frame,
        rules=HydrocarbonIntervalRuleSet(preserve_explicit_gaps=False),
    )

    assert len(result.intervals) == 1
    assert result.intervals[0].top == 2148.2
    assert result.intervals[0].base == 2154.8


def test_hydrocarbon_interval_engine_records_lithology_barrier_rows() -> None:
    frame = pd.DataFrame(
        {
            "top": [2148.2, 2150.0, 2150.2],
            "base": [2150.0, 2150.2, 2154.8],
            "depth": [2148.2, 2150.0, 2150.2],
            "interpretation": ["Газовая залежь", "Claystone barrier", "Газовая залежь"],
            "lithology": ["Sandstone", "Claystone", "Sandstone"],
            "wh": [7.0, None, 8.0],
            "bh": [45.0, None, 48.0],
            "c1_c2": [80.0, None, 82.0],
        }
    )

    result = detect_hydrocarbon_intervals(frame)

    assert [(interval.top, interval.base, interval.fluid_type) for interval in result.intervals] == [
        (2148.2, 2150.0, "gas"),
        (2150.2, 2154.8, "gas"),
    ]
    assert len(result.barriers) == 1
    assert result.barriers[0].top == 2150.0
    assert result.barriers[0].base == 2150.2
    assert result.barriers[0].lithology == "claystone"
    assert result.barriers[0].inferred is False
    assert result.rows.loc[1, "barrier_candidate"] is True or bool(result.rows.loc[1, "barrier_candidate"])


def test_hydrocarbon_interval_engine_records_inferred_barrier_for_explicit_gap() -> None:
    frame = pd.DataFrame(
        {
            "top": [2148.2, 2150.2],
            "base": [2150.0, 2154.8],
            "depth": [2148.2, 2150.2],
            "interpretation": ["Газовая залежь", "Газовая залежь"],
        }
    )

    result = detect_hydrocarbon_intervals(frame)

    assert len(result.intervals) == 2
    assert len(result.barriers) == 1
    assert result.barriers[0].top == 2150.0
    assert result.barriers[0].base == 2150.2
    assert result.barriers[0].lithology == "unknown_barrier"
    assert result.barriers[0].inferred is True
