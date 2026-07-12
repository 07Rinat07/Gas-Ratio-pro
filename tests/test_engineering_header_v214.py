from __future__ import annotations

from app.streamlit_app import (
    _active_interval_table_marker,
    _fluid_visual,
    _interval_table_window,
)
import pandas as pd


def test_fluid_visuals_are_stable_for_engineering_types() -> None:
    assert _fluid_visual("oil") == ("Нефть", "#22c55e", "🟩")
    assert _fluid_visual("Газовый интервал") == ("Газ", "#ef4444", "🟥")
    assert _fluid_visual("Газоконденсатный интервал") == ("Газоконденсат", "#f59e0b", "🟧")
    assert _fluid_visual("water")[2] == "🟦"


def test_active_interval_marker_contains_direction_and_fluid_color() -> None:
    assert _active_interval_table_marker("Нефтяной интервал", active=True) == "▶ 🟩"
    assert _active_interval_table_marker("Газовый интервал", active=False) == "🟥"


def test_interval_table_window_marks_every_row_by_fluid_and_active_row() -> None:
    table = pd.DataFrame(
        [
            {"ID": "HC-001", "Вероятный флюид": "Газовый интервал"},
            {"ID": "HC-002", "Вероятный флюид": "Нефтяной интервал"},
            {"ID": "HC-003", "Вероятный флюид": "Газоконденсатный интервал"},
        ]
    )
    window, start, end = _interval_table_window(table, "HC-002", window_size=5)
    assert (start, end) == (0, 3)
    assert window["Активный"].tolist() == ["🟥", "▶ 🟩", "🟧"]
