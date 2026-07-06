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
    curve_units: dict[str, str] | None = None,
    well_metadata: dict[str, object] | None = None,
) -> bytes:
    if df is None or df.empty:
        return b""

    columns = [str(column) for column in df.columns]
    depth_name = depth_column if depth_column in columns else columns[0]
    ordered_columns = [depth_name] + [column for column in columns if column != depth_name]
    export_df = df[ordered_columns].copy()

    sanitized_columns = [_sanitize_curve_name(column) for column in ordered_columns]
    metadata = {str(key).upper(): value for key, value in dict(well_metadata or {}).items()}
    resolved_well = str(metadata.get("WELL", well_name)).strip() or "WELL"
    resolved_null = metadata.get("NULL", null_value)
    try:
        resolved_null_value = float(resolved_null)
    except (TypeError, ValueError):
        resolved_null_value = float(null_value)

    depth_values = pd.to_numeric(export_df[depth_name], errors="coerce").dropna()
    if not depth_values.empty:
        start_depth = float(depth_values.iloc[0])
        stop_depth = float(depth_values.iloc[-1])
        diffs = depth_values.diff().dropna().abs()
        positive_diffs = diffs[diffs > 0].round(10)
        step_depth = float(positive_diffs.value_counts().idxmax()) if not positive_diffs.empty else 0.0
    else:
        start_depth = stop_depth = step_depth = 0.0

    depth_unit = dict(curve_units or {}).get(depth_name, "M") or "M"

    lines = [
        "~Version",
        "VERS. 2.0 : CWLS LAS version",
        "WRAP. NO  : One line per depth step",
        "~Well",
        f"WELL. {resolved_well} : Well name",
        f"STRT.{_sanitize_curve_name(depth_unit)} {start_depth:.10g} : Start depth",
        f"STOP.{_sanitize_curve_name(depth_unit)} {stop_depth:.10g} : Stop depth",
        f"STEP.{_sanitize_curve_name(depth_unit)} {step_depth:.10g} : Depth step",
        f"NULL. {resolved_null_value} : Null value",
    ]
    for key in ("COMPANY", "FIELD", "LOCATION", "DATE", "SERVICE_COMPANY"):
        if key in metadata and str(metadata[key]).strip():
            lines.append(f"{key}. {str(metadata[key]).strip()} : Export metadata")
    lines.append("~Curve")
    for original, sanitized in zip(ordered_columns, sanitized_columns):
        raw_unit = dict(curve_units or {}).get(original, "M" if original == depth_name else "")
        unit = _sanitize_curve_name(raw_unit) if raw_unit else ""
        lines.append(f"{sanitized}.{unit} : {original}")

    lines.append("~ASCII")
    for _index, row in export_df.iterrows():
        values = [_format_las_value(row[column], resolved_null_value) for column in ordered_columns]
        lines.append(" ".join(values))

    return ("\n".join(lines) + "\n").encode("utf-8")
