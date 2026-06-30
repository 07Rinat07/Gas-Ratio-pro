from __future__ import annotations

import pandas as pd

from importers.header_detector import detect_header_row, prepare_dataframe_with_header


def test_detects_header_row():
    raw = pd.DataFrame(
        [
            ["Report", None, None],
            ["Generated", "2026-06-30", None],
            ["Depth", "CH4", "C2"],
            [1000, 80, 10],
            [1001, 81, 9],
        ]
    )

    result = detect_header_row(raw)

    assert result.header_row == 2


def test_prepare_dataframe_with_header_removes_empty_rows():
    raw = pd.DataFrame(
        [
            ["Depth", "CH4", "Unnamed: 2"],
            [1000, 80, None],
            [None, None, None],
            [1001, 81, None],
        ]
    )

    prepared = prepare_dataframe_with_header(raw, 0)

    assert list(prepared.columns) == ["Depth", "CH4"]
    assert len(prepared) == 2
