from __future__ import annotations

"""Export helpers for manually managed interpretation intervals.

The module is deliberately independent from Streamlit.  It accepts immutable
interval models and returns in-memory bytes suitable for downloads, project
exports, tests or future API endpoints.
"""

import json
from dataclasses import asdict
from io import BytesIO
from typing import Iterable

import pandas as pd

from projects.interpretation_intervals import InterpretationInterval
from reports.export_csv import export_csv_bytes
from reports.export_xlsx import export_xlsx_bytes

INTERVAL_EXPORT_SCHEMA = "gas-ratio-pro/interpretation-interval-export/v1"
INTERVAL_EXPORT_COLUMNS = (
    "id",
    "label",
    "top",
    "base",
    "thickness",
    "middle_depth",
    "interval_type",
    "color",
    "comment",
    "source",
    "created_at",
    "updated_at",
)


def build_interpretation_interval_export_rows(
    intervals: Iterable[InterpretationInterval],
) -> tuple[dict[str, object], ...]:
    """Return deterministic, JSON-compatible export rows."""

    ordered = sorted(intervals, key=lambda item: (item.top, item.base, item.label.lower(), item.id))
    rows: list[dict[str, object]] = []
    for interval in ordered:
        raw = asdict(interval)
        rows.append(
            {
                "id": raw["id"],
                "label": raw["label"],
                "top": raw["top"],
                "base": raw["base"],
                "thickness": interval.thickness,
                "middle_depth": interval.middle_depth,
                "interval_type": raw["interval_type"],
                "color": raw["color"],
                "comment": raw["comment"],
                "source": raw["source"],
                "created_at": raw["created_at"],
                "updated_at": raw["updated_at"],
            }
        )
    return tuple(rows)


def build_interpretation_interval_export_dataframe(
    intervals: Iterable[InterpretationInterval],
) -> pd.DataFrame:
    """Build a stable tabular representation for CSV/XLSX exports."""

    return pd.DataFrame(
        build_interpretation_interval_export_rows(intervals),
        columns=list(INTERVAL_EXPORT_COLUMNS),
    )


def export_interpretation_intervals_json(
    intervals: Iterable[InterpretationInterval],
    *,
    project_id: str,
    well_id: str,
    interpretation_id: str,
) -> bytes:
    """Export intervals with their storage scope and a versioned schema."""

    payload = {
        "schema": INTERVAL_EXPORT_SCHEMA,
        "project_id": str(project_id),
        "well_id": str(well_id),
        "interpretation_id": str(interpretation_id),
        "intervals": list(build_interpretation_interval_export_rows(intervals)),
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def export_interpretation_intervals_csv(
    intervals: Iterable[InterpretationInterval],
) -> bytes:
    """Export intervals as UTF-8 BOM CSV for spreadsheet compatibility."""

    return export_csv_bytes(build_interpretation_interval_export_dataframe(intervals))


def export_interpretation_intervals_xlsx(
    intervals: Iterable[InterpretationInterval],
    *,
    project_id: str,
    well_id: str,
    interpretation_id: str,
) -> bytes:
    """Export intervals as a readable XLSX workbook with scope metadata."""

    dataframe = build_interpretation_interval_export_dataframe(intervals)
    if dataframe.empty:
        return b""
    return export_xlsx_bytes(
        dataframe,
        sheet_name="intervals",
        metadata={
            "Project ID": project_id,
            "Well ID": well_id,
            "Interpretation ID": interpretation_id,
            "Schema": INTERVAL_EXPORT_SCHEMA,
            "Interval count": len(dataframe.index),
        },
    )
