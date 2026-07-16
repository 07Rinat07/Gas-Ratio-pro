"""JSON-safe localized metadata import preview projections."""
from __future__ import annotations

from .metadata_scanner import MetadataScanResult


def build_metadata_import_preview(result: MetadataScanResult, translate) -> dict[str, object]:
    """Build a compact user-facing preview without exposing adapter objects."""
    metadata = dict(result.metadata)
    format_name = result.format_id.upper() if result.format_id != "lis79" else "LIS79"
    summary_key = f"import.preview.{result.format_id}.summary"
    summary = translate(summary_key, format_name=format_name)
    if summary == summary_key:
        summary = translate("import.preview.generic.summary", format_name=format_name)
    warnings = []
    for code in result.warnings:
        key = f"import.preview.warning.{code}"
        text = translate(key)
        warnings.append({"code": code, "message": text if text != key else code})
    preferred = (
        "logical_file_count", "frame_count", "channel_count", "trace_count",
        "trace_count_estimate", "samples_per_trace", "sample_interval_us",
        "segy_revision_major", "segy_revision_minor", "inline_min", "inline_max",
        "crossline_min", "crossline_max", "adapter_available", "file_size_bytes",
    )
    fields = [
        {"key": key, "label": translate(f"import.preview.field.{key}"), "value": metadata[key]}
        for key in preferred if key in metadata
    ]
    for field in fields:
        if field["label"] == f"import.preview.field.{field['key']}":
            field["label"] = str(field["key"])
    return {
        "format_id": result.format_id,
        "summary": summary,
        "complete": result.complete,
        "bytes_read": result.bytes_read,
        "fields": fields,
        "warnings": warnings,
    }
