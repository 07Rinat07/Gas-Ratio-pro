from __future__ import annotations

"""Export helpers for the project-level interval type operation journal."""

import json
from dataclasses import asdict
from typing import Iterable

import pandas as pd

from projects.interpretation_interval_types import InterpretationIntervalTypeOperation
from reports.export_csv import export_csv_bytes
from reports.export_xlsx import export_xlsx_bytes

TYPE_OPERATION_EXPORT_SCHEMA = "gas-ratio-pro/interpretation-interval-type-operation-export/v1"
TYPE_OPERATION_EXPORT_COLUMNS = (
    "id",
    "operation",
    "source_type_id",
    "target_type_id",
    "interval_count",
    "well_count",
    "interpretation_count",
    "target_color_applied",
    "created_at",
    "undo_available",
    "undone_at",
    "status",
)


def build_type_operation_export_rows(
    operations: Iterable[InterpretationIntervalTypeOperation],
) -> tuple[dict[str, object], ...]:
    """Build deterministic JSON-compatible rows, newest operation first."""

    ordered = sorted(
        operations,
        key=lambda item: (item.created_at, item.id),
        reverse=True,
    )
    rows: list[dict[str, object]] = []
    for operation in ordered:
        raw = asdict(operation)
        rows.append(
            {
                "id": raw["id"],
                "operation": raw["operation"],
                "source_type_id": raw["source_type_id"],
                "target_type_id": raw["target_type_id"],
                "interval_count": raw["interval_count"],
                "well_count": raw["well_count"],
                "interpretation_count": raw["interpretation_count"],
                "target_color_applied": raw["target_color_applied"],
                "created_at": raw["created_at"],
                "undo_available": raw["undo_available"],
                "undone_at": raw["undone_at"],
                "status": "undone" if raw["undone_at"] else "completed",
            }
        )
    return tuple(rows)


def build_type_operation_export_dataframe(
    operations: Iterable[InterpretationIntervalTypeOperation],
) -> pd.DataFrame:
    return pd.DataFrame(
        build_type_operation_export_rows(operations),
        columns=list(TYPE_OPERATION_EXPORT_COLUMNS),
    )


def export_type_operations_json(
    operations: Iterable[InterpretationIntervalTypeOperation],
    *,
    project_id: str,
) -> bytes:
    rows = build_type_operation_export_rows(operations)
    payload = {
        "schema": TYPE_OPERATION_EXPORT_SCHEMA,
        "project_id": str(project_id),
        "operation_count": len(rows),
        "operations": list(rows),
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def export_type_operations_csv(
    operations: Iterable[InterpretationIntervalTypeOperation],
) -> bytes:
    return export_csv_bytes(build_type_operation_export_dataframe(operations))


def export_type_operations_xlsx(
    operations: Iterable[InterpretationIntervalTypeOperation],
    *,
    project_id: str,
) -> bytes:
    dataframe = build_type_operation_export_dataframe(operations)
    if dataframe.empty:
        return b""
    return export_xlsx_bytes(
        dataframe,
        sheet_name="type_operations",
        metadata={
            "Project ID": project_id,
            "Schema": TYPE_OPERATION_EXPORT_SCHEMA,
            "Operation count": len(dataframe.index),
        },
    )
