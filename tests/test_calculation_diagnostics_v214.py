import numpy as np
import pandas as pd

from core.calculation_diagnostics import (
    build_calculation_diagnostics_report,
    column_quality_dataframe,
    formula_diagnostics_dataframe,
)
from core.calculations import CalculationConfig, calculate_gas_ratios


def _frame():
    return pd.DataFrame({
        "depth": [1, 2, 3, 4],
        "c1": [10, 10, 10, 10],
        "c2": [2, 0, 2, "bad"],
        "c3": [1, 1, np.nan, 1],
        "ic4": [1, 1, 1, 1],
        "nc4": [1, 1, 1, 1],
        "ic5": [1, 1, 1, 1],
        "nc5": [1, 1, 1, 1],
    })


def test_report_explains_invalid_formulas():
    calculated = calculate_gas_ratios(_frame(), CalculationConfig(ch_mode="A")).data
    report = build_calculation_diagnostics_report(calculated, ch_mode="A")
    bar2 = next(item for item in report.formulas if item.formula == "bar2")
    assert bar2.invalid_rows == 2
    assert bar2.zero_denominator_rows == 1
    assert bar2.non_numeric_rows == 0  # numeric coercion already happened in calculation pipeline
    assert not report.problematic_rows.empty


def test_column_quality_reports_missing_and_zero_values():
    calculated = calculate_gas_ratios(_frame(), CalculationConfig(ch_mode="A")).data
    report = build_calculation_diagnostics_report(calculated)
    table = column_quality_dataframe(report)
    c2 = table.loc[table["Компонент"] == "C2"].iloc[0]
    assert c2["NaN/пусто"] == 1
    assert c2["Нулей"] == 1


def test_formula_table_contains_expression_and_percent():
    calculated = calculate_gas_ratios(_frame(), CalculationConfig(ch_mode="A")).data
    table = formula_diagnostics_dataframe(build_calculation_diagnostics_report(calculated))
    assert {"Формула", "Рассчитано, %", "Основная причина"}.issubset(table.columns)
    assert table.loc[table["Коэффициент"] == "Ch", "Формула"].iloc[0].endswith("/ C3")


def test_reserved_ch_is_explained():
    calculated = calculate_gas_ratios(_frame(), CalculationConfig(ch_mode="reserved")).data
    report = build_calculation_diagnostics_report(calculated, ch_mode="reserved")
    ch = next(item for item in report.formulas if item.formula == "ch")
    assert ch.valid_rows == 0
    assert "отключена" in ch.dominant_reason
