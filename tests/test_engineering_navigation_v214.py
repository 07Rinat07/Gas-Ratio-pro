from __future__ import annotations

import pandas as pd

from app.streamlit_app import (
    _adjacent_interval_id,
    _interval_navigation_state,
    _interval_table_window,
    _ordered_interval_ids,
)


def _table(count: int = 30) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ID": [f"HC-{index:03d}" for index in range(1, count + 1)],
            "Интервал, м": [f"{1000 + index}–{1001 + index}" for index in range(count)],
            "Мощность, м": [1.0] * count,
        }
    )


def test_navigation_moves_without_wrapping() -> None:
    ids = ["HC-001", "HC-002", "HC-003"]
    assert _adjacent_interval_id(ids, "HC-002", -1) == "HC-001"
    assert _adjacent_interval_id(ids, "HC-002", 1) == "HC-003"
    assert _adjacent_interval_id(ids, "HC-001", -1) == "HC-001"
    assert _adjacent_interval_id(ids, "HC-003", 1) == "HC-003"


def test_window_centers_active_interval_and_marks_it() -> None:
    table = _table(40)
    window, start, end = _interval_table_window(table, "HC-025", window_size=11)
    assert start <= 24 < end
    assert len(window) == 11
    active = window.loc[window["ID"] == "HC-025", "Активный"].tolist()
    assert active == ["▶"]
    assert window.loc[window["ID"] != "HC-025", "Активный"].eq("").all()


def test_navigation_state_uses_current_table_order() -> None:
    table = _table(5).iloc[[4, 2, 0, 1, 3]].reset_index(drop=True)
    ids, position = _interval_navigation_state(table, "HC-001")
    assert ids == ["HC-005", "HC-003", "HC-001", "HC-002", "HC-004"]
    assert position == 2
    assert _ordered_interval_ids(table) == ids


def test_streamlit_source_contains_navigation_controls() -> None:
    source = open("app/streamlit_app.py", encoding="utf-8").read()
    assert "◀ Предыдущий интервал" in source
    assert "Следующий интервал ▶" in source
    assert "Активная строка удерживается в видимой области" in source
    assert 'window.insert(0, "Активный"' in source
