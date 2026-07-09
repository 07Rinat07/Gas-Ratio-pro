from __future__ import annotations

import pandas as pd

from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.interval_cards import build_interval_report_cards, interval_cards_overview_table


def test_interval_cards_present_engineer_first_fields() -> None:
    frame = pd.DataFrame(
        {
            "depth": [2148.2, 2149.0, 2155.0, 2156.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Нефтяная залежь", "Нефтяная залежь"],
            "wh": [6.0, 7.0, 25.0, 26.0],
            "bh": [45.0, 44.0, 10.0, 11.0],
            "c1_c2": [80.0, 82.0, 6.0, 6.5],
            "oil_indicator": [0.04, 0.05, 0.2, 0.22],
            "lithology": ["Sandstone", "Sandstone", "Sandstone", "Sandstone"],
        }
    )

    payload = build_hydrocarbon_report_payload(frame)

    assert payload.interval_cards
    table = payload.interval_cards_table
    assert table is not None
    assert table.title == "Карточки интервалов залежей"
    assert "Строк" not in " ".join(table.headers)
    assert any("м" in str(row[1]) for row in table.rows)
    assert payload.interval_card_reasoning_table is not None


def test_interval_card_builder_uses_explanation_recommendations() -> None:
    frame = pd.DataFrame(
        {
            "depth": [3000.0],
            "interpretation": ["Газовая залежь"],
            "wh": [8.0],
            "bh": [42.0],
            "c1_c2": [90.0],
            "oil_indicator": [0.03],
            "lithology": ["Sandstone"],
        }
    )

    payload = build_hydrocarbon_report_payload(frame)
    cards = build_interval_report_cards(payload.intervals)

    assert cards
    first = cards[0]
    assert first.interval_id == "HC-001"
    assert first.depth_range.endswith(" м")
    assert first.summary
    assert first.confidence
    assert first.recommendations or first.limitations or first.reasoning


def test_interval_cards_overview_returns_none_for_empty_cards() -> None:
    assert interval_cards_overview_table(()) is None
