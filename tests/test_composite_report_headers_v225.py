from __future__ import annotations

import pandas as pd

from app.visualization_v3.composite_v4 import build_composite_log_v4


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "depth": [1000.0, 1001.0, 1002.0],
        "c1": [0.1, 0.2, 0.3],
        "ic4": [0.01, 0.02, 0.03],
        "nc5": [0.001, 0.002, 0.003],
    })


def test_russian_composite_has_full_component_names() -> None:
    result = build_composite_log_v4(_frame(), include_keys=("c1", "ic4", "nc5"), locale="ru")
    assert "Метан" in result.svg
    assert "Изобутан" in result.svg
    assert "Н-пентан" in result.svg
    assert "Глубина" in result.svg


def test_kazakh_composite_localizes_depth_and_overview_copy() -> None:
    result = build_composite_log_v4(_frame(), include_keys=("c1",), locale="kk", report_kind="overview")
    assert "Тереңдік" in result.svg
    assert "Жұмыс аралығы" in result.svg
    assert "Рабочий диапазон" not in result.svg


def test_english_composite_localizes_depth_and_component_description() -> None:
    result = build_composite_log_v4(_frame(), include_keys=("c1", "ic4"), locale="en", report_kind="overview")
    assert "Depth" in result.svg
    assert "Methane" in result.svg
    assert "Isobutane" in result.svg
    assert "Working range" in result.svg
    assert "Рабочий диапазон" not in result.svg
