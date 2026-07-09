import pandas as pd
import pytest

from las_editor.mud_gas_interpretation import (
    build_mud_gas_interpretation_manifest,
    build_mud_gas_source_columns,
    calculate_mud_gas_ratios,
    classify_haworth,
    classify_oil_indicator,
    classify_pixler,
    interpret_mud_gas_dataframe,
    mud_gas_interval_table_rows,
    mud_gas_interpretation_table_rows,
    render_mud_gas_markdown_report,
)


def sample_gas_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 1001.0, 1002.0, 1003.0],
            "C1": [100.0, 20.0, 8.0, 300.0],
            "C2": [2.0, 4.0, 2.0, 5.0],
            "C3": [0.8, 3.0, 2.0, 2.0],
            "C4": [0.2, 2.0, 1.5, 0.5],
            "C5": [0.1, 1.0, 0.5, 0.1],
        }
    )


def test_source_column_resolution_accepts_standard_mnemonics():
    mapping, issues = build_mud_gas_source_columns(sample_gas_frame())

    assert not issues
    assert mapping["depth"] == "DEPT"
    assert mapping["c1"] == "C1"
    assert mapping["c5"] == "C5"


def test_ratio_calculation_returns_haworth_pixler_and_oil_indicator_values():
    df = sample_gas_frame()
    mapping, _issues = build_mud_gas_source_columns(df)
    ratios, issues = calculate_mud_gas_ratios(df, mapping)

    assert not issues
    assert len(ratios) == 4
    assert ratios[0].wetness == 3.00679
    assert ratios[0].pixler_c1_c2 == 50.0
    assert ratios[0].oil_indicator == 0.011


def test_haworth_classifier_handles_dry_gas_and_oil_association():
    dry_gas, _notes = classify_haworth(0.2, 20.0, 0.1)
    associated, notes = classify_haworth(10.0, 5.0, 0.8)

    assert dry_gas == "Легкий сухой газ"
    assert associated == "Газ, ассоциированный с нефтью"
    assert any("Character" in note for note in notes)


def test_pixler_classifier_uses_c1_c2_ranges():
    assert classify_pixler(3.0)[0] == "Низкоплотная / тяжелая нефть API 10-15"
    assert classify_pixler(6.0)[0] == "Нефть средней плотности API 15-35"
    assert classify_pixler(20.0)[0] == "Газ / газоконденсат"
    assert classify_pixler(70.0)[0] == "Легкий газ, вероятно непродуктивный"


def test_oil_indicator_classifier_supports_inverse_ratio():
    assert classify_oil_indicator(0.05)[0] == "Сухой газ"
    assert classify_oil_indicator(0.2)[0] == "Нефть"
    assert classify_oil_indicator(None, 5.0)[0] == "Нефть"


def test_full_dataframe_interpretation_builds_rows_intervals_and_manifest():
    result = interpret_mud_gas_dataframe(sample_gas_frame())
    manifest = build_mud_gas_interpretation_manifest(result)

    assert len(result.rows) == 4
    assert result.intervals
    assert manifest["schema"] == "gas-ratio-pro/mud-gas-interpretation/v1"
    assert manifest["row_count"] == 4
    assert manifest["issue_count"] == 0


def test_ui_table_helpers_return_serializable_rows():
    result = interpret_mud_gas_dataframe(sample_gas_frame())
    rows = mud_gas_interpretation_table_rows(result.rows)
    intervals = mud_gas_interval_table_rows(result.intervals)

    assert rows[0]["depth"] == 1000.0
    assert "fluid_character" in rows[0]
    assert intervals[0]["sample_count"] >= 1


def test_markdown_report_contains_intervals_and_sources():
    result = interpret_mud_gas_dataframe(sample_gas_frame())
    report = render_mud_gas_markdown_report(result)

    assert "Mud Gas Interpretation Report" in report
    assert "## Source curves" in report
    assert "## Intervals" in report
    assert "DEPT" in report


def test_missing_required_curve_is_reported_as_error():
    df = sample_gas_frame().drop(columns=["C5"])
    result = interpret_mud_gas_dataframe(df)

    assert not result.rows
    assert any(issue.code == "missing_curve" for issue in result.issues)


def test_mud_gas_character_ratio_uses_haworth_formula():
    df = pd.DataFrame(
        {
            "DEPTH": [1000.0],
            "C1": [80.0],
            "C2": [10.0],
            "C3": [5.0],
            "C4": [5.0],
            "C5": [2.0],
        }
    )

    ratios, issues = calculate_mud_gas_ratios(
        df,
        {"depth": "DEPTH", "c1": "C1", "c2": "C2", "c3": "C3", "c4": "C4", "c5": "C5"},
    )

    assert not [issue for issue in issues if issue.severity == "error"]
    assert ratios[0].character == pytest.approx((5.0 + 2.0) / 5.0)
