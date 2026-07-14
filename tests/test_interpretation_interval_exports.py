from __future__ import annotations

import json
from io import BytesIO

import pandas as pd

from projects.interpretation_interval_exports import (
    INTERVAL_EXPORT_SCHEMA,
    build_interpretation_interval_export_dataframe,
    export_interpretation_intervals_csv,
    export_interpretation_intervals_json,
    export_interpretation_intervals_xlsx,
)
from projects.interpretation_intervals import build_interpretation_interval


def _intervals():
    deep = build_interpretation_interval(
        interval_id="550e8400-e29b-41d4-a716-446655440001",
        label="Газ",
        top=120.0,
        base=130.5,
        interval_type="gas",
        color="#112233",
        comment="Перспективный интервал",
    )
    shallow = build_interpretation_interval(
        interval_id="550e8400-e29b-41d4-a716-446655440000",
        label="Нефть",
        top=100.0,
        base=110.0,
        interval_type="oil",
    )
    return deep, shallow


def test_export_dataframe_is_sorted_and_contains_derived_metrics():
    frame = build_interpretation_interval_export_dataframe(_intervals())

    assert frame["label"].tolist() == ["Нефть", "Газ"]
    assert frame["thickness"].tolist() == [10.0, 10.5]
    assert frame["middle_depth"].tolist() == [105.0, 125.25]


def test_json_export_contains_scope_and_versioned_schema():
    payload = json.loads(
        export_interpretation_intervals_json(
            _intervals(),
            project_id="project-1",
            well_id="well-1",
            interpretation_id="primary",
        ).decode("utf-8")
    )

    assert payload["schema"] == INTERVAL_EXPORT_SCHEMA
    assert payload["project_id"] == "project-1"
    assert payload["well_id"] == "well-1"
    assert payload["interpretation_id"] == "primary"
    assert [item["label"] for item in payload["intervals"]] == ["Нефть", "Газ"]


def test_csv_export_uses_utf8_bom_and_round_trips():
    data = export_interpretation_intervals_csv(_intervals())

    assert data.startswith(b"\xef\xbb\xbf")
    frame = pd.read_csv(BytesIO(data))
    assert frame["label"].tolist() == ["Нефть", "Газ"]


def test_xlsx_export_contains_interval_and_metadata_sheets():
    data = export_interpretation_intervals_xlsx(
        _intervals(),
        project_id="project-1",
        well_id="well-1",
        interpretation_id="primary",
    )

    workbook = pd.ExcelFile(BytesIO(data))
    assert workbook.sheet_names == ["Параметры отчёта", "intervals"]
    frame = pd.read_excel(BytesIO(data), sheet_name="intervals")
    metadata = pd.read_excel(BytesIO(data), sheet_name="Параметры отчёта")
    assert frame["label"].tolist() == ["Нефть", "Газ"]
    assert "Interval count" in metadata["Параметр"].tolist()


def test_empty_tabular_exports_return_empty_bytes():
    assert export_interpretation_intervals_csv(()) == b""
    assert export_interpretation_intervals_xlsx(
        (), project_id="p", well_id="w", interpretation_id="i"
    ) == b""
