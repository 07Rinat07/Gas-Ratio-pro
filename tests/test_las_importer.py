from __future__ import annotations

from io import BytesIO

import pandas as pd
import pytest

from core.calculations import calculate_gas_ratios
from importers.header_detector import detect_header_row, prepare_dataframe_with_header
from importers.las_importer import load_las_raw, load_las_sheets, read_las
from mapping.mapper import apply_mapping, auto_map_columns


def test_load_las_raw_builds_header_row_and_data_rows():
    raw = load_las_raw("examples/sample_gas_data.las")

    assert list(raw.iloc[0]) == ["DEPT", "C1", "C2", "C3", "IC4", "NC4", "IC5", "NC5"]
    assert raw.iloc[1, 0] == 1000.0
    assert pd.isna(raw.iloc[3, 2])


def test_load_las_sheets_returns_single_las_sheet():
    sheets = load_las_sheets("examples/sample_gas_data.las")

    assert list(sheets) == ["LAS"]
    assert detect_header_row(sheets["LAS"]).header_row == 0


def test_read_las_prepares_dataframe_with_curve_columns():
    df = read_las("examples/sample_gas_data.las")

    assert list(df.columns) == ["DEPT", "C1", "C2", "C3", "IC4", "NC4", "IC5", "NC5"]
    assert len(df) == 3


def test_las_importer_accepts_decimal_comma_depth_values():
    las_bytes = b"""
~Well
NULL. -999.25
~Curve
DEPT.M : depth
C1.% : methane
C2.% : ethane
~ASCII
1,2 80 10
2,0 90 5
"""
    raw = load_las_raw(BytesIO(las_bytes))

    assert raw.iloc[1, 0] == 1.2
    assert raw.iloc[2, 0] == 2.0


def test_las_pipeline_maps_and_calculates_ratios():
    raw = load_las_raw("examples/sample_gas_data.las")
    prepared = prepare_dataframe_with_header(raw, 0)
    mapping = auto_map_columns(prepared.columns)
    mapped = apply_mapping(prepared, mapping.mapping)
    calculation = calculate_gas_ratios(mapped.data)

    assert mapping.mapping["depth"] == "DEPT"
    assert mapping.mapping["c1"] == "C1"
    assert mapping.mapping["nc5"] == "NC5"
    assert calculation.data.loc[0, "wh"] == pytest.approx(21.56862745098)
    assert pd.isna(calculation.data.loc[2, "c2"])
