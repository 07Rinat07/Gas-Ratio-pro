from __future__ import annotations

import pandas as pd

from core.interpretation import engineering_interval_summary


def test_engineering_summary_returns_intervals_not_row_counts() -> None:
    df = pd.DataFrame({
        "depth": [1000.0, 1000.2, 1000.4, 1001.0, 1001.2],
        "wh": [10.0, 11.0, 12.0, 25.0, 26.0],
        "bh": [20.0, 21.0, 22.0, 5.0, 4.0],
        "ch": [1.0] * 5,
        "c1_c2": [3.0] * 5,
        "c1_c3": [5.0] * 5,
        "oil_indicator": [0.4, 0.4, 0.4, 2.0, 2.0],
        "interpretation": ["Газовая залежь"] * 3 + ["Нефтяная залежь"] * 2,
    })
    result = engineering_interval_summary(df)
    assert "Интервал, м" in result.columns
    assert "Вероятный флюид" in result.columns
    assert "Инженерное заключение" in result.columns
    assert "count" not in result.columns
    assert not result.empty
