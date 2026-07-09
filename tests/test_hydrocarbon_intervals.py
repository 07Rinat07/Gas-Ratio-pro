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
    assert result.schema.endswith("/v14")


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
    assert result.schema.endswith("/v14")


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


def test_hydrocarbon_interval_engine_exports_structured_evidence_and_quality_flags() -> None:
    frame = pd.DataFrame(
        {
            "depth": [2200.0],
            "interpretation": ["Газовая залежь"],
            "wh": [6.0],
            "bh": [44.0],
            "c1_c2": [82.0],
            "oil_indicator": [0.04],
        }
    )

    result = detect_hydrocarbon_intervals(frame)
    interval = result.intervals[0]
    table_rows = hydrocarbon_interval_table_rows(result.intervals)
    markers = hydrocarbon_interval_marker_rows(result.intervals)

    assert result.schema.endswith("/v14")
    assert interval.evidence_items
    assert {item.method for item in interval.evidence_items} >= {"Haworth", "Pixler", "HydrocarbonIntervalEngine"}
    assert "single_sample_interval" in interval.quality_flags
    assert table_rows[0]["evidence_items"]
    assert "single_sample_interval" in table_rows[0]["quality_flags"]
    assert "single_sample_interval" in markers[0]["quality_flags"]



def test_hydrocarbon_interval_engine_calculates_confidence_score_and_factors() -> None:
    frame = pd.DataFrame(
        {
            "depth": [2300.0, 2301.0, 2302.0],
            "interpretation": ["Нефтяная залежь", "Нефтяная залежь", "Нефтяная залежь"],
            "wh": [26.0, 27.0, 28.0],
            "bh": [9.0, 10.0, 11.0],
            "c1_c2": [6.0, 7.0, 8.0],
            "oil_indicator": [0.18, 0.2, 0.22],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))
    interval = result.intervals[0]
    table_rows = hydrocarbon_interval_table_rows(result.intervals)
    markers = hydrocarbon_interval_marker_rows(result.intervals)

    assert result.schema.endswith("/v14")
    assert interval.confidence_score >= 75
    assert interval.confidence == "high"
    assert any(factor.startswith("haworth_evidence=") for factor in interval.confidence_factors)
    assert any(factor.startswith("pixler_evidence=") for factor in interval.confidence_factors)
    assert table_rows[0]["confidence_score"] == interval.confidence_score
    assert "final=" in table_rows[0]["confidence_factors"]
    assert markers[0]["confidence_score"] == interval.confidence_score
    assert "%" in markers[0]["annotation"]


def test_hydrocarbon_interval_engine_exports_method_registry_and_provenance() -> None:
    frame = pd.DataFrame(
        {
            "depth": [2400.0, 2401.0],
            "interpretation": ["Газовая залежь", "Газовая залежь"],
            "wh": [7.0, 8.0],
            "bh": [42.0, 40.0],
            "c1_c2": [80.0, 78.0],
            "oil_indicator": [0.04, 0.05],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))
    interval = result.intervals[0]
    rows = hydrocarbon_interval_table_rows(result.intervals)

    method_ids = {item.method_id for item in interval.evidence_items}
    assert {"haworth_mud_gas", "pixler_gas_ratio", "hydrocarbon_interval_engine"}.issubset(method_ids)
    assert rows[0]["evidence_provenance"]
    provenance_ids = {item["method_id"] for item in rows[0]["evidence_provenance"]}
    assert "pixler_gas_ratio" in provenance_ids
    assert all(item["authors"] for item in rows[0]["evidence_provenance"])


def test_interval_evidence_framework_exports_status_expected_and_reference() -> None:
    frame = pd.DataFrame(
        {
            "depth": [2500.0, 2501.0],
            "interpretation": ["Газовая залежь", "Газовая залежь"],
            "wh": [7.0, 8.0],
            "bh": [42.0, 40.0],
            "c1_c2": [80.0, 78.0],
            "oil_indicator": [0.04, 0.05],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))
    interval = result.intervals[0]
    rows = hydrocarbon_interval_table_rows(result.intervals)

    assert result.schema.endswith("/v14")
    assert interval.evidence_items
    assert all(item.evidence_id for item in interval.evidence_items)
    assert all(item.status in {"pass", "observed", "missing"} for item in interval.evidence_items)
    assert any(item.expected for item in interval.evidence_items)
    assert any("Pixler" in item.reference for item in interval.evidence_items)
    provenance = rows[0]["evidence_provenance"]
    assert all(item["status"] for item in provenance)
    assert all(item["reference"] for item in provenance)
    assert all("citation_note" in item for item in provenance)


def test_hydrocarbon_interval_rule_engine_exports_applied_rules_and_trace() -> None:
    frame = pd.DataFrame(
        {
            "depth": [2600.0, 2601.0, 2602.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Газовая залежь"],
            "wh": [7.0, 8.0, 9.0],
            "bh": [42.0, 43.0, 44.0],
            "c1_c2": [82.0, 80.0, 78.0],
            "c1_c3": [180.0, 175.0, 170.0],
            "oil_indicator": [0.04, 0.05, 0.04],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))
    interval = result.intervals[0]
    rows = hydrocarbon_interval_table_rows(result.intervals)
    markers = hydrocarbon_interval_marker_rows(result.intervals)

    assert result.schema.endswith("/v14")
    assert "HC-GAS-HIGH-001" in interval.applied_rule_ids
    assert interval.rule_traces
    assert any(trace.status == "applied" for trace in interval.rule_traces)
    assert interval.interpretation_status == "high_confidence_preliminary"
    assert rows[0]["rule_traces"]
    assert "HC-GAS-HIGH-001" in rows[0]["applied_rule_ids"]
    assert markers[0]["interpretation_status"] == interval.interpretation_status


def test_hydrocarbon_interval_rule_engine_flags_single_sample_review() -> None:
    frame = pd.DataFrame(
        {
            "depth": [2700.0],
            "interpretation": ["Нефтяная залежь"],
            "wh": [28.0],
            "bh": [10.0],
            "c1_c2": [6.0],
            "oil_indicator": [0.2],
        }
    )

    result = detect_hydrocarbon_intervals(frame)
    interval = result.intervals[0]
    rows = hydrocarbon_interval_table_rows(result.intervals)

    assert "HC-SINGLE-SAMPLE-001" in interval.applied_rule_ids
    assert interval.interpretation_status == "requires_review"
    assert "rule_delta=" in rows[0]["confidence_factors"]
    assert any(trace.rule_id == "HC-SINGLE-SAMPLE-001" and trace.status == "applied" for trace in interval.rule_traces)


def test_hydrocarbon_interval_engine_validation_case_passes_for_gas_reference() -> None:
    from core.hydrocarbon_intervals import (
        HydrocarbonValidationCase,
        hydrocarbon_engine_api_contract,
        hydrocarbon_validation_result_rows,
        validate_hydrocarbon_interval_result,
    )

    frame = pd.DataFrame(
        {
            "depth": [2800.0, 2801.0, 2802.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Газовая залежь"],
            "wh": [7.0, 8.0, 9.0],
            "bh": [42.0, 43.0, 44.0],
            "c1_c2": [82.0, 80.0, 78.0],
            "c1_c3": [180.0, 175.0, 170.0],
            "oil_indicator": [0.04, 0.05, 0.04],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))
    case = HydrocarbonValidationCase(
        case_id="gas-reference",
        title="Reference gas-bearing interval",
        expected_fluid_types=("gas",),
        minimum_confidence_score=70,
        required_rule_ids=("HC-GAS-HIGH-001",),
    )

    validation = validate_hydrocarbon_interval_result(result, case)
    rows = hydrocarbon_validation_result_rows((validation,))
    contract = hydrocarbon_engine_api_contract()

    assert validation.passed is True
    assert rows[0]["passed"] is True
    assert contract["schema"].endswith("/v14")
    assert "detect_hydrocarbon_intervals" in contract["public_builders"]


def test_hydrocarbon_interval_engine_validation_case_catches_barrier_regression() -> None:
    from core.hydrocarbon_intervals import HydrocarbonValidationCase, validate_hydrocarbon_interval_result

    frame = pd.DataFrame(
        {
            "top": [2900.0, 2901.0, 2901.2],
            "base": [2901.0, 2901.2, 2903.0],
            "depth": [2900.0, 2901.0, 2901.2],
            "interpretation": ["Газовая залежь", "Claystone barrier", "Газовая залежь"],
            "lithology": ["Sandstone", "Claystone", "Sandstone"],
            "wh": [8.0, None, 9.0],
            "bh": [44.0, None, 45.0],
            "c1_c2": [80.0, None, 82.0],
        }
    )

    result = detect_hydrocarbon_intervals(frame)
    case = HydrocarbonValidationCase(
        case_id="barrier-reference",
        title="Separated gas intervals with Claystone barrier",
        expected_fluid_types=("gas",),
        expected_min_intervals=2,
        expected_barriers=1,
    )

    validation = validate_hydrocarbon_interval_result(result, case)

    assert validation.passed is True
    assert validation.observed_interval_count == 2
    assert validation.observed_barrier_count == 1


def test_hydrocarbon_interval_engine_exports_interpretation_context_and_decision_level() -> None:
    frame = pd.DataFrame(
        {
            "depth": [3000.0, 3001.0, 3002.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Газовая залежь"],
            "lithology": ["Sandstone", "Sandstone", "Sandstone"],
            "c1": [1.0, 1.1, 1.2],
            "wh": [7.0, 8.0, 9.0],
            "bh": [42.0, 43.0, 44.0],
            "c1_c2": [82.0, 80.0, 78.0],
            "c1_c3": [180.0, 175.0, 170.0],
            "oil_indicator": [0.04, 0.05, 0.04],
            "formation": ["A", "A", "A"],
            "well_name": ["Well-1", "Well-1", "Well-1"],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))
    interval = result.intervals[0]
    rows = hydrocarbon_interval_table_rows(result.intervals)
    markers = hydrocarbon_interval_marker_rows(result.intervals)

    assert result.schema.endswith("/v14")
    assert interval.context is not None
    assert interval.context.lithology == "sandstone"
    assert interval.context.curve_quality in {"good", "limited"}
    assert interval.data_confidence_score == interval.confidence_score
    assert interval.geological_confidence_score >= 70
    assert interval.decision_level in {"high", "very_high"}
    assert rows[0]["context"]["lithology"] == "sandstone"
    assert rows[0]["decision_level"] == interval.decision_level
    assert rows[0]["evidence_tree"]
    assert markers[0]["decision_level"] == interval.decision_level


def test_hydrocarbon_interval_engine_context_tracks_neighboring_barriers() -> None:
    frame = pd.DataFrame(
        {
            "top": [3100.0, 3101.0, 3101.3],
            "base": [3101.0, 3101.3, 3102.4],
            "depth": [3100.0, 3101.0, 3101.3],
            "interpretation": ["Газовая залежь", "Claystone barrier", "Газовая залежь"],
            "lithology": ["Sandstone", "Claystone", "Sandstone"],
            "wh": [8.0, None, 9.0],
            "bh": [44.0, None, 45.0],
            "c1_c2": [80.0, None, 82.0],
        }
    )

    result = detect_hydrocarbon_intervals(frame)

    assert len(result.intervals) == 2
    assert result.intervals[0].context is not None
    assert "Claystone" in result.intervals[0].context.barrier_below
    assert result.intervals[1].context is not None
    assert "Claystone" in result.intervals[1].context.barrier_above
    assert "above:gas" in result.intervals[1].context.neighbor_summary


def test_hydrocarbon_interval_engine_public_payload_hides_technical_details_by_default() -> None:
    from core.hydrocarbon_intervals import build_hydrocarbon_interval_engine_payload, summarize_hydrocarbon_interval_result

    frame = pd.DataFrame(
        {
            "depth": [3200.0, 3201.0, 3202.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Газовая залежь"],
            "lithology": ["Sandstone", "Sandstone", "Sandstone"],
            "c1": [1.0, 1.1, 1.2],
            "wh": [7.0, 8.0, 9.0],
            "bh": [42.0, 43.0, 44.0],
            "c1_c2": [82.0, 80.0, 78.0],
            "c1_c3": [180.0, 175.0, 170.0],
        }
    )

    result = detect_hydrocarbon_intervals(frame, rules=HydrocarbonIntervalRuleSet(max_depth_gap=2.0))
    summary = summarize_hydrocarbon_interval_result(result)
    payload = build_hydrocarbon_interval_engine_payload(result)
    technical_payload = build_hydrocarbon_interval_engine_payload(result, include_technical=True)

    assert result.schema.endswith("/v14")
    assert summary["total_intervals"] == 1
    assert summary["productive_intervals"] == 1
    assert "row_count" not in payload
    assert "diagnostics" not in payload
    assert "technical" not in payload
    assert payload["summary"]["main_intervals"][0]["fluid_type"] == "gas"
    assert payload["intervals"][0]["decision_level"] in {"medium", "high", "very_high"}
    assert "technical" in technical_payload
    assert technical_payload["technical"]["row_count"] == 3
