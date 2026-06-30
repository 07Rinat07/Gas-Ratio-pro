from __future__ import annotations

import numpy as np
import pandas as pd

from core.calculations import safe_divide


def test_safe_divide_series_by_scalar_zero_returns_nan_series():
    result = safe_divide(pd.Series([1, 2]), 0)

    assert result.isna().all()


def test_safe_divide_scalar_by_series_zero_keeps_nonzero_values():
    result = safe_divide(10, pd.Series([2, 0]))

    assert result.iloc[0] == 5
    assert np.isnan(result.iloc[1])
