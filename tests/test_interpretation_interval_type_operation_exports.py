from __future__ import annotations

import json
from io import BytesIO

import pandas as pd

from projects.interpretation_interval_type_operation_exports import (
    TYPE_OPERATION_EXPORT_SCHEMA,
    build_type_operation_export_rows,
    export_type_operations_csv,
    export_type_operations_json,
    export_type_operations_xlsx,
)
from projects.interpretation_interval_types import InterpretationIntervalTypeOperation


def _operation(*, operation_id: str, created_at: str, undone_at: str = "") -> InterpretationIntervalTypeOperation:
    return InterpretationIntervalTypeOperation(
        id=operation_id,
        operation="reassign_and_delete",
        source_type_id="source",
        target_type_id="target",
        interval_count=3,
        well_count=2,
        interpretation_count=2,
        target_color_applied=True,
        created_at=created_at,
        undo_available=not bool(undone_at),
        undone_at=undone_at,
    )


def test_operation_export_rows_are_newest_first_and_include_status() -> None:
    rows = build_type_operation_export_rows(
        (
            _operation(operation_id="old", created_at="2026-07-14T10:00:00Z", undone_at="2026-07-14T12:00:00Z"),
            _operation(operation_id="new", created_at="2026-07-14T11:00:00Z"),
        )
    )

    assert [row["id"] for row in rows] == ["new", "old"]
    assert rows[0]["status"] == "completed"
    assert rows[1]["status"] == "undone"


def test_operation_journal_json_contains_scope_and_schema() -> None:
    payload = json.loads(
        export_type_operations_json(
            (_operation(operation_id="one", created_at="2026-07-14T11:00:00Z"),),
            project_id="project-a",
        ).decode("utf-8")
    )

    assert payload["schema"] == TYPE_OPERATION_EXPORT_SCHEMA
    assert payload["project_id"] == "project-a"
    assert payload["operation_count"] == 1
    assert payload["operations"][0]["id"] == "one"


def test_operation_journal_csv_and_xlsx_are_readable() -> None:
    operations = (_operation(operation_id="one", created_at="2026-07-14T11:00:00Z"),)

    csv_frame = pd.read_csv(BytesIO(export_type_operations_csv(operations)))
    xlsx_frame = pd.read_excel(BytesIO(export_type_operations_xlsx(operations, project_id="project-a")), sheet_name="type_operations")

    assert csv_frame.loc[0, "id"] == "one"
    assert xlsx_frame.loc[0, "source_type_id"] == "source"
    assert xlsx_frame.loc[0, "status"] == "completed"
