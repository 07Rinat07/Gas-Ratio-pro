from __future__ import annotations

import pandas as pd

from mapping.mapper import apply_mapping, auto_map_columns, detect_standard_field


def test_detects_ch4_as_c1():
    assert detect_standard_field("CH4") == "c1"


def test_detects_depth_as_depth():
    assert detect_standard_field("Depth") == "depth"


def test_auto_mapping_and_apply_mapping():
    df = pd.DataFrame(
        {
            "Depth": [1000, 1001],
            "CH4": [80, 81],
            "Ethane": [10, 9],
            "Unknown": ["x", "y"],
        }
    )

    mapping = auto_map_columns(df.columns)
    prepared = apply_mapping(df, mapping.mapping)

    assert mapping.mapping["depth"] == "Depth"
    assert mapping.mapping["c1"] == "CH4"
    assert mapping.mapping["c2"] == "Ethane"
    assert "Unknown" in mapping.unmapped_columns
    assert list(prepared.data["depth"]) == [1000, 1001]
    assert "c3" in prepared.data.columns
