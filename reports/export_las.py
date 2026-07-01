from __future__ import annotations

import math
import re

import pandas as pd


def _sanitize_curve_name(value: object) -> str:
    name = re.sub(r"[^0-9A-Za-z_]+", "_", str(value).strip().upper()).strip("_")
    if not name:
        return "CURVE"
    if name[0].isdigit():
        return f"C{name}"
    return name[:32]


def _format_las_value(value: object, null_value: float) -> str:
    if value is None or pd.isna(value):
        return str(null_value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(float(value)):
            return str(null_value)
        return f"{float(value):.10g}"
    text = str(value).strip()
    if not text:
        return str(null_value)
    return re.sub(r"\s+", "_", text)


def export_las_bytes(
    df: pd.DataFrame,
    well_name: str = "WELL",
    depth_column: str | None = None,
    null_value: float = -999.25,
) -> bytes:
    if df is None or df.empty:
        return b""

    columns = [str(column) for column in df.columns]
    depth_name = depth_column if depth_column in columns else columns[0]
    ordered_columns = [depth_name] + [column for column in columns if column != depth_name]
    export_df = df[ordered_columns].copy()

    sanitized_columns = [_sanitize_curve_name(column) for column in ordered_columns]
    lines = [
        "~Version",
        "VERS. 2.0 : CWLS LAS version",
        "WRAP. NO  : One line per depth step",
        "~Well",
        f"WELL. {str(well_name).strip() or 'WELL'} : Well name",
        f"NULL. {null_value} : Null value",
        "~Curve",
    ]
    for original, sanitized in zip(ordered_columns, sanitized_columns):
        unit = "M" if original == depth_name else ""
        lines.append(f"{sanitized}.{unit} : {original}")

    lines.append("~ASCII")
    for _index, row in export_df.iterrows():
        values = [_format_las_value(row[column], null_value) for column in ordered_columns]
        lines.append(" ".join(values))

    return ("\n".join(lines) + "\n").encode("utf-8")
