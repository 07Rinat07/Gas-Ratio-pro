from __future__ import annotations

import json
from io import BytesIO

import pandas as pd
import pytest

from projects.interpretation_interval_exports import (
    export_interpretation_intervals_csv,
    export_interpretation_intervals_json,
    export_interpretation_intervals_xlsx,
)
from projects.interpretation_interval_imports import (
    apply_interpretation_interval_import,
    parse_interpretation_interval_import,
)
from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_intervals import build_interpretation_interval


def _interval(interval_id: str, label: str, top: float, base: float):
    return build_interpretation_interval(
        interval_id=interval_id,
        label=label,
        top=top,
        base=base,
        interval_type="gas",
        color="#123456",
        comment="test",
    )


def test_json_csv_and_xlsx_round_trip_parsing():
    intervals = (
        _interval("550e8400-e29b-41d4-a716-446655440000", "A", 100, 110),
        _interval("550e8400-e29b-41d4-a716-446655440001", "B", 120, 130),
    )
    json_payload = parse_interpretation_interval_import(
        export_interpretation_intervals_json(
            intervals, project_id="p", well_id="w", interpretation_id="default"
        ),
        "intervals.json",
    )
    csv_payload = parse_interpretation_interval_import(
        export_interpretation_intervals_csv(intervals), "intervals.csv"
    )
    xlsx_payload = parse_interpretation_interval_import(
        export_interpretation_intervals_xlsx(
            intervals, project_id="p", well_id="w", interpretation_id="default"
        ),
        "intervals.xlsx",
    )

    assert [item.id for item in json_payload.intervals] == [item.id for item in intervals]
    assert [item.label for item in csv_payload.intervals] == ["A", "B"]
    assert [item.top for item in xlsx_payload.intervals] == [100.0, 120.0]
    assert json_payload.project_id == "p"


def test_parser_rejects_invalid_schema_and_missing_columns():
    with pytest.raises(ValueError, match="схема"):
        parse_interpretation_interval_import(
            json.dumps({"schema": "wrong", "intervals": []}).encode(), "bad.json"
        )

    frame = pd.DataFrame([{"label": "A", "top": 100.0}])
    buffer = BytesIO()
    frame.to_csv(buffer, index=False)
    with pytest.raises(ValueError, match="base"):
        parse_interpretation_interval_import(buffer.getvalue(), "bad.csv")


def test_upsert_import_is_single_undoable_operation(tmp_path):
    state = {}
    manager = InterpretationIntervalManager(
        state, root=tmp_path, project_id="project", well_id="well"
    )
    original = manager.create(label="Old", top=100, base=110)
    manager.commands.clear_history()

    updated = build_interpretation_interval(
        interval_id=original.id,
        label="Updated",
        top=101,
        base=111,
        created_at=original.created_at,
    )
    created = _interval("550e8400-e29b-41d4-a716-446655440010", "New", 120, 130)
    data = export_interpretation_intervals_json(
        (updated, created), project_id="project", well_id="well", interpretation_id="default"
    )
    payload = parse_interpretation_interval_import(data, "import.json")

    result = apply_interpretation_interval_import(manager, payload, mode="upsert")
    assert result.created_count == 1
    assert result.updated_count == 1
    assert [item.label for item in manager.list_intervals()] == ["Updated", "New"]
    assert manager.history_status()["undo_count"] == 1

    assert manager.undo() is True
    restored = manager.list_intervals()
    assert len(restored) == 1
    assert restored[0].label == "Old"


def test_append_rejects_existing_uuid(tmp_path):
    manager = InterpretationIntervalManager({}, root=tmp_path, project_id="p", well_id="w")
    existing = manager.create(label="A", top=100, base=110)
    data = export_interpretation_intervals_json(
        (existing,), project_id="p", well_id="w", interpretation_id="default"
    )
    payload = parse_interpretation_interval_import(data, "same.json")

    with pytest.raises(ValueError, match="уже существуют"):
        apply_interpretation_interval_import(manager, payload, mode="append")


def test_replace_mode_replaces_complete_set(tmp_path):
    manager = InterpretationIntervalManager({}, root=tmp_path, project_id="p", well_id="w")
    manager.create(label="Old", top=10, base=20)
    imported = _interval("550e8400-e29b-41d4-a716-446655440020", "Only", 30, 40)
    payload = parse_interpretation_interval_import(
        export_interpretation_intervals_csv((imported,)), "replace.csv"
    )

    result = apply_interpretation_interval_import(manager, payload, mode="replace")
    assert result.total_count == 1
    assert manager.list_intervals()[0].label == "Only"
