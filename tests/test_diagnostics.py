from __future__ import annotations

import pandas as pd

from core.calculations import calculate_gas_ratios
from core.diagnostics import (
    build_mapping_diagnostics,
    build_ratio_nan_diagnostics,
    interval_ratio_diagnostic_messages,
    mapping_warning_messages,
    ratio_nan_warning_messages,
)


def test_mapping_diagnostics_reports_missing_gas_component():
    diagnostics = build_mapping_diagnostics(
        {"depth": "DEPT", "c1": "C1", "c2": "C2"},
        source_columns=["DEPT", "C1", "C2"],
    )

    c3_row = diagnostics.loc[diagnostics["field"] == "c3"].iloc[0]

    assert c3_row["status"] == "missing"
    assert "0" in c3_row["effect"]


def test_mapping_warning_messages_explain_depth_fallback():
    messages = mapping_warning_messages({"c1": "C1"}, source_columns=["C1"])

    assert any("depth не сопоставлен" in message for message in messages)
    assert any("C2 не сопоставлен" in message for message in messages)


def test_ratio_nan_diagnostics_explain_zero_denominators():
    calculation = calculate_gas_ratios(
        pd.DataFrame(
            {
                "c1": [10.0],
                "c2": [0.0],
                "c3": [0.0],
                "ic4": [0.0],
                "nc4": [0.0],
                "ic5": [0.0],
                "nc5": [0.0],
            }
        )
    )

    diagnostics = build_ratio_nan_diagnostics(calculation.data)
    bar2 = diagnostics.loc[diagnostics["ratio"] == "bar2"].iloc[0]
    bh = diagnostics.loc[diagnostics["ratio"] == "bh"].iloc[0]

    assert bar2["nan_count"] == 1
    assert "знаменатель C2" in bar2["causes"]
    assert bh["nan_count"] == 1
    assert "C3+iC4+nC4+iC5+nC5" in bh["causes"]


def test_ratio_nan_warning_messages_include_row_counts():
    df = pd.DataFrame({"wh": [float("nan"), 10.0], "c1": [0, 1], "c2": [0, 1]})

    messages = ratio_nan_warning_messages(df, ratios=("wh",))

    assert messages == (
        "Wh: NaN в 1 из 2 строк. Причина: нет колонок: C3, iC4, nC4, iC5, nC5; "
        "нулевой или пустой знаменатель C1+C2+C3+iC4+nC4+iC5+nC5: 1 строка. "
        "Что проверить: проверьте mapping, числовой формат и нули в знаменателях. "
        "См. [docs/troubleshooting.md#все-расчеты-дают-nan](docs/troubleshooting.md#все-расчеты-дают-nan).",
    )


def test_interval_ratio_diagnostic_messages_explain_selected_row_nan():
    row = pd.Series({"wh": float("nan"), "c1": 0.0, "c2": 0.0})

    messages = interval_ratio_diagnostic_messages(row, ratios=("wh",))

    assert len(messages) == 1
    assert "Wh: нет расчета" in messages[0]
    assert "Проверьте mapping" in messages[0]


def test_ratio_nan_diagnostics_cover_inverse_oil_indicator_denominator():
    calculation = calculate_gas_ratios(
        pd.DataFrame(
            {
                "c1": [10.0],
                "c2": [0.0],
                "c3": [0.0],
                "ic4": [0.0],
                "nc4": [0.0],
                "ic5": [0.0],
                "nc5": [0.0],
            }
        )
    )

    diagnostics = build_ratio_nan_diagnostics(calculation.data, ratios=("inverse_oil_indicator",))
    row = diagnostics.iloc[0]

    assert row["label"] == "Inverse oil indicator"
    assert row["nan_count"] == 1
    assert "C3+iC4+nC4+iC5+nC5" in row["causes"]


def test_mapping_warning_messages_include_documentation_links():
    messages = mapping_warning_messages({"c1": "BAD"}, source_columns=["C1"])

    assert any("docs/troubleshooting.md#колонки-не-сопоставились" in message for message in messages)
    assert any("docs/troubleshooting.md#глубина-отсутствует" in message for message in messages)


def test_ch_nan_warning_points_to_formula_documentation():
    df = pd.DataFrame({"ch": [float("nan")], "c3": [1.0], "ic4": [0.0], "nc4": [0.0], "ic5": [0.0], "nc5": [0.0]})

    messages = ratio_nan_warning_messages(df, ratios=("ch",), ch_mode="B")

    assert len(messages) == 1
    assert "docs/formulas.md" in messages[0]
