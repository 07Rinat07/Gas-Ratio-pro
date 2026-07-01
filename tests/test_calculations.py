from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.calculations import calculate_gas_ratios, safe_divide


def test_wh_calculation():
    df = pd.DataFrame(
        {
            "c1": [80],
            "c2": [10],
            "c3": [5],
            "ic4": [3],
            "nc4": [2],
            "ic5": [0],
            "nc5": [0],
        }
    )

    result = calculate_gas_ratios(df).data

    assert result.loc[0, "wh"] == pytest.approx(20.0)


def test_bh_calculation():
    df = pd.DataFrame(
        {
            "c1": [80],
            "c2": [10],
            "c3": [5],
            "ic4": [3],
            "nc4": [2],
            "ic5": [0],
            "nc5": [0],
        }
    )

    result = calculate_gas_ratios(df).data

    assert result.loc[0, "bh"] == pytest.approx(9.0)


def test_pixler_ratios():
    df = pd.DataFrame(
        {
            "c1": [80],
            "c2": [10],
            "c3": [5],
            "ic4": [3],
            "nc4": [2],
            "ic5": [1],
            "nc5": [1],
        }
    )

    result = calculate_gas_ratios(df).data

    assert result.loc[0, "c1_c2"] == pytest.approx(8.0)
    assert result.loc[0, "c1_c3"] == pytest.approx(16.0)
    assert result.loc[0, "c1_c4"] == pytest.approx(16.0)
    assert result.loc[0, "c1_c5"] == pytest.approx(40.0)


def test_division_by_zero_returns_nan():
    assert np.isnan(safe_divide(1, 0))

    df = pd.DataFrame(
        {
            "c1": [1],
            "c2": [0],
            "c3": [0],
            "ic4": [0],
            "nc4": [0],
            "ic5": [0],
            "nc5": [0],
        }
    )

    result = calculate_gas_ratios(df).data

    assert np.isnan(result.loc[0, "bar2"])
    assert np.isnan(result.loc[0, "bh"])

def test_depth_uses_interval_midpoint_when_depth_column_missing():
    df = pd.DataFrame(
        {
            "depth_from": [1000, 1002],
            "depth_to": [1001, 1004],
            "c1": [80, 81],
            "c2": [10, 9],
            "c3": [5, 4],
            "ic4": [3, 3],
            "nc4": [2, 2],
            "ic5": [1, 1],
            "nc5": [1, 1],
        }
    )

    calculation = calculate_gas_ratios(df)

    assert list(calculation.data["depth"]) == [1000.5, 1003.0]
    assert any("середина интервала" in warning for warning in calculation.warnings)
