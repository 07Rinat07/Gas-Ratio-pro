from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd

from las_editor.curve_categories import CURVE_CATEGORY_LABELS, suggest_curve_category
from las_editor.curve_grouping import normalize_curve_group, suggest_curve_group
from las_editor.curve_rename import normalize_curve_name
from las_editor.curve_units import curve_unit_label, suggest_curve_unit

METADATA_STATUS_LABELS: dict[str, str] = {
    "draft": "Draft",
    "review": "Review",
    "approved": "Approved",
    "deprecated": "Deprecated",
}

METADATA_QUALITY_LABELS: dict[str, str] = {
    "unknown": "Unknown",
    "raw": "Raw",
    "checked": "Checked",
    "corrected": "Corrected",
    "derived": "Derived",
}

TEXT_FIELDS: tuple[str, ...] = ("description", "source", "tool", "comment")
CONTROLLED_FIELDS: tuple[str, ...] = ("status", "quality")
EDITABLE_FIELDS: tuple[str, ...] = TEXT_FIELDS + CONTROLLED_FIELDS


@dataclass(frozen=True)
class CurveMetadataHistoryEntry:
    curve_name: str
    field: str
    value: str
    previous_value: str
    timestamp: str
    reason: str = "manual"
    source: str = "las_editor"


@dataclass(frozen=True)
class CurveMetadataResult:
    metadata: dict[str, dict[str, str]]
    history: tuple[CurveMetadataHistoryEntry, ...]
    references: dict[str, Any]
    diagnostics: tuple[str, ...] = ()
    assigned: bool = False
    curve_name: str = ""
    field: str = ""
    value: str = ""


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_metadata_field(field: object) -> str:
    value = str(field).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "desc": "description",
        "описание": "description",
        "источник": "source",
        "instrument": "tool",
        "device": "tool",
        "статус": "status",
        "qa": "quality",
        "quality_flag": "quality",
        "качество": "quality",
        "note": "comment",
        "notes": "comment",
        "комментарий": "comment",
    }
    return aliases.get(value, value)


def normalize_metadata_value(field: object, value: object) -> str:
    field_key = normalize_metadata_field(field)
    text = str(value or "").strip()
    if field_key == "status":
        normalized = text.lower().replace("-", "_").replace(" ", "_") or "draft"
        aliases = {"new": "draft", "todo": "draft", "checked": "approved", "ok": "approved", "archive": "deprecated"}
        return aliases.get(normalized, normalized)
    if field_key == "quality":
        normalized = text.lower().replace("-", "_").replace(" ", "_") or "unknown"
        aliases = {"qc": "checked", "valid": "checked", "edited": "corrected", "calc": "derived", "calculated": "derived"}
        return aliases.get(normalized, normalized)
    return " ".join(text.split())


def available_metadata_fields() -> tuple[str, ...]:
    return EDITABLE_FIELDS


def available_metadata_statuses() -> tuple[str, ...]:
    return tuple(METADATA_STATUS_LABELS.keys())


def available_metadata_qualities() -> tuple[str, ...]:
    return tuple(METADATA_QUALITY_LABELS.keys())


def metadata_status_label(status: object) -> str:
    key = normalize_metadata_value("status", status)
    return METADATA_STATUS_LABELS.get(key, key)


def metadata_quality_label(quality: object) -> str:
    key = normalize_metadata_value("quality", quality)
    return METADATA_QUALITY_LABELS.get(key, key)


def _normalize_metadata_map(metadata: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    for curve, values in dict(metadata or {}).items():
        if not isinstance(values, dict):
            continue
        curve_name = str(curve)
        normalized[curve_name] = {}
        for field, value in values.items():
            field_key = normalize_metadata_field(field)
            if field_key in EDITABLE_FIELDS:
                normalized[curve_name][field_key] = normalize_metadata_value(field_key, value)
    return normalized


def build_curve_metadata(
    columns: Iterable[object],
    *,
    aliases: dict[str, str] | None = None,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    unit_overrides: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, dict[str, str]]:
    """Build normalized metadata rows for LAS curves without mutating curve values."""

    alias_map = {str(curve): str(alias) for curve, alias in dict(aliases or {}).items()}
    group_map = {str(curve): normalize_curve_group(group) for curve, group in dict(group_overrides or {}).items()}
    category_map = {str(curve): str(category).strip().lower().replace("-", "_") for curve, category in dict(category_overrides or {}).items()}
    unit_map = {str(curve): str(unit) for curve, unit in dict(unit_overrides or {}).items()}
    manual_metadata = _normalize_metadata_map(metadata)

    result: dict[str, dict[str, str]] = {}
    for column in columns:
        curve_name = str(column)
        group = group_map.get(curve_name, suggest_curve_group(curve_name))
        category = category_map.get(curve_name, suggest_curve_category(curve_name, group=group))
        if category not in CURVE_CATEGORY_LABELS:
            category = "uncategorized"
        unit = unit_map.get(curve_name, suggest_curve_unit(curve_name, group=group, category=category))
        base = {
            "description": f"LAS curve {curve_name}",
            "source": "LAS import",
            "tool": "unknown",
            "status": "draft",
            "quality": "unknown",
            "comment": "",
            "alias": alias_map.get(curve_name, ""),
            "group": group,
            "category": category,
            "unit": unit,
        }
        base.update(manual_metadata.get(curve_name, {}))
        result[curve_name] = base
    return result


def curve_metadata_table_rows(
    columns: Iterable[object],
    *,
    aliases: dict[str, str] | None = None,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    unit_overrides: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    built = build_curve_metadata(
        columns,
        aliases=aliases,
        group_overrides=group_overrides,
        category_overrides=category_overrides,
        unit_overrides=unit_overrides,
        metadata=metadata,
    )
    manual = _normalize_metadata_map(metadata)
    for curve_name, values in built.items():
        rows.append({
            "curve_name": curve_name,
            "alias": values.get("alias", ""),
            "group": values.get("group", "other"),
            "category": values.get("category", "uncategorized"),
            "unit": values.get("unit", "unknown"),
            "unit_label": curve_unit_label(values.get("unit", "unknown")),
            "description": values.get("description", ""),
            "source": values.get("source", ""),
            "tool": values.get("tool", ""),
            "status": values.get("status", "draft"),
            "status_label": metadata_status_label(values.get("status", "draft")),
            "quality": values.get("quality", "unknown"),
            "quality_label": metadata_quality_label(values.get("quality", "unknown")),
            "comment": values.get("comment", ""),
            "manual_fields": ", ".join(sorted(manual.get(curve_name, {}).keys())),
        })
    return tuple(rows)


def _update_metadata_references(references: dict[str, Any], metadata: dict[str, dict[str, str]], curve_name: str) -> dict[str, Any]:
    updated = dict(references or {})
    updated["curve_metadata"] = {curve: dict(values) for curve, values in metadata.items()}
    manifest = updated.get("manifest")
    if isinstance(manifest, dict):
        manifest = dict(manifest)
        curve_manifest = dict(manifest.get(curve_name, {})) if isinstance(manifest.get(curve_name), dict) else {}
        curve_manifest.update(metadata.get(curve_name, {}))
        manifest[curve_name] = curve_manifest
        updated["manifest"] = manifest
    return updated


def assign_curve_metadata(
    df: pd.DataFrame,
    curve_name: str,
    field: str,
    value: object,
    *,
    aliases: dict[str, str] | None = None,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    unit_overrides: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
    history: tuple[CurveMetadataHistoryEntry, ...] | list[CurveMetadataHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor",
    timestamp: str | None = None,
) -> CurveMetadataResult:
    columns = tuple(str(column) for column in df.columns)
    normalized_curve = normalize_curve_name(curve_name)
    field_key = normalize_metadata_field(field)
    normalized_value = normalize_metadata_value(field_key, value)
    diagnostics: list[str] = []

    if not normalized_curve:
        raise ValueError("Кривая для metadata не указана.")
    if normalized_curve not in columns:
        raise ValueError(f"Кривая {normalized_curve!r} не найдена.")
    if field_key not in EDITABLE_FIELDS:
        allowed = ", ".join(available_metadata_fields())
        raise ValueError(f"Поле metadata {field_key!r} не поддерживается. Доступно: {allowed}.")
    if field_key == "status" and normalized_value not in METADATA_STATUS_LABELS:
        raise ValueError(f"Статус {normalized_value!r} не поддерживается.")
    if field_key == "quality" and normalized_value not in METADATA_QUALITY_LABELS:
        raise ValueError(f"Качество {normalized_value!r} не поддерживается.")

    current = _normalize_metadata_map(metadata)
    built_before = build_curve_metadata(
        columns,
        aliases=aliases,
        group_overrides=group_overrides,
        category_overrides=category_overrides,
        unit_overrides=unit_overrides,
        metadata=current,
    )
    previous_value = built_before.get(normalized_curve, {}).get(field_key, "")
    diagnostics.append(f"Кривая найдена: {normalized_curve}.")
    diagnostics.append(f"Поле metadata нормализовано: {field_key}.")

    if previous_value == normalized_value and field_key in current.get(normalized_curve, {}):
        return CurveMetadataResult(
            built_before,
            tuple(history),
            _update_metadata_references(dict(references or {}), built_before, normalized_curve),
            tuple(diagnostics) + ("Metadata уже содержит такое значение: изменения не применены.",),
            False,
            normalized_curve,
            field_key,
            normalized_value,
        )

    current.setdefault(normalized_curve, {})[field_key] = normalized_value
    built_after = build_curve_metadata(
        columns,
        aliases=aliases,
        group_overrides=group_overrides,
        category_overrides=category_overrides,
        unit_overrides=unit_overrides,
        metadata=current,
    )
    entry = CurveMetadataHistoryEntry(
        normalized_curve,
        field_key,
        normalized_value,
        previous_value,
        timestamp or _timestamp_utc(),
        reason or "manual",
        source or "las_editor",
    )
    return CurveMetadataResult(
        built_after,
        tuple(history) + (entry,),
        _update_metadata_references(dict(references or {}), built_after, normalized_curve),
        tuple(diagnostics) + (f"Metadata обновлена: {normalized_curve}.{field_key}.",),
        True,
        normalized_curve,
        field_key,
        normalized_value,
    )


def undo_last_metadata_assignment(
    df: pd.DataFrame,
    *,
    aliases: dict[str, str] | None = None,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    unit_overrides: dict[str, str] | None = None,
    metadata: dict[str, Any] | None,
    history: tuple[CurveMetadataHistoryEntry, ...] | list[CurveMetadataHistoryEntry],
    references: dict[str, Any] | None = None,
) -> CurveMetadataResult:
    current_history = tuple(history)
    if not current_history:
        raise ValueError("История metadata пуста: отменять нечего.")
    last = current_history[-1]
    current = _normalize_metadata_map(metadata)
    if current.get(last.curve_name, {}).get(last.field) != last.value:
        raise ValueError("Нельзя отменить metadata: текущее значение уже изменено.")
    if last.previous_value:
        current.setdefault(last.curve_name, {})[last.field] = last.previous_value
        restored_value = last.previous_value
    else:
        current.get(last.curve_name, {}).pop(last.field, None)
        if not current.get(last.curve_name):
            current.pop(last.curve_name, None)
        restored_value = ""
    columns = tuple(str(column) for column in df.columns)
    built = build_curve_metadata(
        columns,
        aliases=aliases,
        group_overrides=group_overrides,
        category_overrides=category_overrides,
        unit_overrides=unit_overrides,
        metadata=current,
    )
    return CurveMetadataResult(
        built,
        current_history[:-1],
        _update_metadata_references(dict(references or {}), built, last.curve_name),
        (f"Отменено последнее metadata-изменение для {last.curve_name}.",),
        True,
        last.curve_name,
        last.field,
        restored_value,
    )


def metadata_summary_rows(metadata: dict[str, dict[str, str]]) -> tuple[dict[str, str], ...]:
    status_counts: dict[str, int] = {status: 0 for status in available_metadata_statuses()}
    quality_counts: dict[str, int] = {quality: 0 for quality in available_metadata_qualities()}
    for values in metadata.values():
        status_counts[normalize_metadata_value("status", values.get("status", "draft"))] = status_counts.get(normalize_metadata_value("status", values.get("status", "draft")), 0) + 1
        quality_counts[normalize_metadata_value("quality", values.get("quality", "unknown"))] = quality_counts.get(normalize_metadata_value("quality", values.get("quality", "unknown")), 0) + 1
    rows: list[dict[str, str]] = []
    for status, count in status_counts.items():
        rows.append({"type": "status", "key": status, "label": metadata_status_label(status), "curve_count": str(count)})
    for quality, count in quality_counts.items():
        rows.append({"type": "quality", "key": quality, "label": metadata_quality_label(quality), "curve_count": str(count)})
    return tuple(rows)
