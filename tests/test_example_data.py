from __future__ import annotations

from pathlib import Path

from core.calculations import calculate_gas_ratios
from importers.csv_importer import read_csv
from mapping.mapper import apply_mapping, auto_map_columns


def test_sample_gas_data_can_be_imported_and_calculated():
    sample_path = Path(__file__).resolve().parents[1] / "examples" / "sample_gas_data.csv"

    imported = read_csv(sample_path)
    mapping = auto_map_columns(imported.columns)
    prepared = apply_mapping(imported, mapping.mapping)
    calculated = calculate_gas_ratios(prepared.data).data

    assert not calculated.empty
    assert {"depth", "c1", "c2", "wh", "bh", "c1_c2"}.issubset(calculated.columns)
    assert calculated["wh"].notna().any()
