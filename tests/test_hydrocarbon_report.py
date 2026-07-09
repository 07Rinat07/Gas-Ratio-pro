from __future__ import annotations

import pandas as pd

from reports.hydrocarbon_report import build_hydrocarbon_report_payload


def test_hydrocarbon_report_payload_uses_one_interval_source_for_tables() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1005.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Нефтяная залежь"],
            "wh": [6.0, 7.0, 25.0],
            "bh": [45.0, 44.0, 10.0],
            "c1_c2": [20.0, 21.0, 6.0],
            "oil_indicator": [0.04, 0.05, 0.2],
        }
    )

    payload = build_hydrocarbon_report_payload(frame)

    assert payload.intervals
    assert payload.summary_table is not None
    assert payload.marker_table is not None
    assert payload.interpretation_table is not None
    assert payload.diagnostics_table is not None
    assert payload.summary_table.title == "Сводка выявленных УВ-интервалов"
    assert payload.marker_table.title == "Маркеры УВ-интервалов для графиков"
    assert payload.interpretation_table.title == "Инженерная интерпретация УВ-интервалов"
    assert len(payload.tables) == 4
    assert any("Сформировано УВ-интервалов" in row[1] for row in payload.diagnostics_table.rows)


def test_hydrocarbon_report_payload_handles_missing_depth_without_tables() -> None:
    frame = pd.DataFrame({"GR": [80.0, 90.0]})

    payload = build_hydrocarbon_report_payload(frame)

    assert payload.intervals == ()
    assert payload.summary_table is None
    assert payload.marker_table is None
    assert payload.interpretation_table is None
    assert payload.diagnostics_table is not None
    assert "Колонка глубины не найдена" in payload.diagnostics[0]
