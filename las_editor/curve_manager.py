from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

import pandas as pd

from las_editor.curve_categories import suggest_curve_category
from las_editor.curve_grouping import suggest_curve_group
from las_editor.curve_rename import update_curve_references
from las_editor.curve_units import curve_unit_label, normalize_curve_unit, suggest_curve_unit
from las_editor.las_creator import LasCurveSpec, add_las_curve, delete_las_curve, normalize_las_mnemonic, normalize_las_unit


PROTECTED_DEPTH_CURVES: tuple[str, ...] = ("DEPT", "DEPTH", "MD", "TVD")
CURVE_MANAGER_STORAGE_KEY = "curve_manager"


@dataclass(frozen=True)
class CurveManagerHistoryEntry:
    action: str
    curve_name: str
    timestamp: str
    details: dict[str, Any]
    reason: str = "manual"
    source: str = "las_editor.curve_manager"


@dataclass(frozen=True)
class CurveManagerResult:
    data: pd.DataFrame
    manifest: dict[str, dict[str, Any]]
    history: tuple[CurveManagerHistoryEntry, ...]
    references: dict[str, Any]
    diagnostics: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _copy_attrs(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    target.attrs.update(source.attrs)
    return target


def _columns(df: pd.DataFrame) -> tuple[str, ...]:
    return tuple(str(column) for column in df.columns)


def is_depth_curve(curve_name: object) -> bool:
    return normalize_las_mnemonic(str(curve_name)) in PROTECTED_DEPTH_CURVES


def normalize_curve_manager_metadata(metadata: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for curve_name, raw in dict(metadata or {}).items():
        curve = normalize_las_mnemonic(str(curve_name))
        if not isinstance(raw, dict) or not curve:
            continue
        normalized[curve] = {
            "description": str(raw.get("description", "") or "").strip(),
            "alias": normalize_las_mnemonic(str(raw.get("alias", "") or ""), fallback="") if raw.get("alias") else "",
            "group": str(raw.get("group", "") or "").strip().lower(),
            "category": str(raw.get("category", "") or "").strip().lower(),
            "unit": normalize_curve_unit(raw.get("unit", "unknown")),
            "quality": str(raw.get("quality", "unknown") or "unknown").strip().lower(),
            "status": str(raw.get("status", "draft") or "draft").strip().lower(),
            "source": str(raw.get("source", "") or "").strip(),
            "comment": str(raw.get("comment", "") or "").strip(),
        }
    return normalized


def build_curve_manifest(
    df: pd.DataFrame,
    *,
    metadata: dict[str, Any] | None = None,
    aliases: dict[str, str] | None = None,
    units: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build one normalized manifest row per LAS curve.

    The manifest is a metadata-only layer. It never changes original LAS values,
    but it gives the UI, export rules, reports and future validators a stable
    place for curve role, unit, alias, quality and ordering information.
    """

    manual_metadata = normalize_curve_manager_metadata(metadata)
    alias_map = {normalize_las_mnemonic(k): normalize_las_mnemonic(v, fallback="") for k, v in dict(aliases or {}).items()}
    unit_map = {normalize_las_mnemonic(k): normalize_curve_unit(v) for k, v in dict(units or {}).items()}
    attr_units = {normalize_las_mnemonic(k): normalize_las_unit(v) for k, v in dict(df.attrs.get("las_units", {})).items()}

    manifest: dict[str, dict[str, Any]] = {}
    for index, column in enumerate(_columns(df)):
        curve = normalize_las_mnemonic(column)
        stored = manual_metadata.get(curve, {})
        group = stored.get("group") or suggest_curve_group(curve)
        category = stored.get("category") or suggest_curve_category(curve, group=group)
        unit = unit_map.get(curve) or stored.get("unit") or normalize_curve_unit(attr_units.get(curve, ""))
        if unit == "unknown":
            unit = suggest_curve_unit(curve, group=group, category=category)
        manifest[curve] = {
            "curve_name": curve,
            "original_name": column,
            "order": index,
            "protected": is_depth_curve(curve),
            "alias": alias_map.get(curve) or stored.get("alias", ""),
            "group": group,
            "category": category,
            "unit": unit,
            "unit_label": curve_unit_label(unit),
            "description": stored.get("description") or f"LAS curve {curve}",
            "quality": stored.get("quality", "unknown"),
            "status": stored.get("status", "draft"),
            "source": stored.get("source", ""),
            "comment": stored.get("comment", ""),
            "non_null_count": int(df[column].notna().sum()),
            "sample_count": int(len(df[column])),
        }
    return manifest


def curve_manager_table_rows(manifest: dict[str, dict[str, Any]]) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for curve, item in sorted(manifest.items(), key=lambda pair: int(pair[1].get("order", 0))):
        rows.append({
            "order": str(item.get("order", "")),
            "curve_name": curve,
            "alias": str(item.get("alias", "")),
            "group": str(item.get("group", "")),
            "category": str(item.get("category", "")),
            "unit": str(item.get("unit", "")),
            "unit_label": str(item.get("unit_label", "")),
            "quality": str(item.get("quality", "")),
            "status": str(item.get("status", "")),
            "protected": "yes" if item.get("protected") else "no",
            "non_null_count": str(item.get("non_null_count", 0)),
            "sample_count": str(item.get("sample_count", 0)),
            "description": str(item.get("description", "")),
        })
    return tuple(rows)


def _history(
    history: Sequence[CurveManagerHistoryEntry],
    *,
    action: str,
    curve_name: str,
    details: dict[str, Any],
    reason: str,
    source: str,
    timestamp: str | None,
) -> tuple[CurveManagerHistoryEntry, ...]:
    return tuple(history) + (
        CurveManagerHistoryEntry(
            action=action,
            curve_name=curve_name,
            timestamp=timestamp or _timestamp_utc(),
            details=dict(details),
            reason=reason or "manual",
            source=source or "las_editor.curve_manager",
        ),
    )


def add_curve_managed(
    df: pd.DataFrame,
    curve: LasCurveSpec | dict[str, Any] | str,
    *,
    metadata: dict[str, Any] | None = None,
    history: Sequence[CurveManagerHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor.curve_manager",
    timestamp: str | None = None,
) -> CurveManagerResult:
    if isinstance(curve, LasCurveSpec):
        spec = curve
    elif isinstance(curve, dict):
        spec = LasCurveSpec(
            mnemonic=str(curve.get("mnemonic", "")),
            unit=str(curve.get("unit", "")),
            description=str(curve.get("description", "")),
            default_value=curve.get("default_value"),
        )
    else:
        spec = LasCurveSpec(str(curve))
    curve_name = normalize_las_mnemonic(spec.mnemonic)
    updated_df = add_las_curve(df, spec)
    updated_df = _copy_attrs(df, updated_df)
    metadata_map = normalize_curve_manager_metadata(metadata)
    metadata_map[curve_name] = {
        **metadata_map.get(curve_name, {}),
        "description": spec.description or curve_name,
        "unit": normalize_curve_unit(spec.unit or "unknown"),
        "status": "draft",
        "quality": "unknown",
        "source": "created",
    }
    manifest = build_curve_manifest(updated_df, metadata=metadata_map)
    updated_refs = dict(references or {})
    updated_refs[CURVE_MANAGER_STORAGE_KEY] = {"manifest": manifest, "metadata": metadata_map}
    return CurveManagerResult(
        data=updated_df,
        manifest=manifest,
        history=_history(history, action="add_curve", curve_name=curve_name, details={"unit": spec.unit, "description": spec.description}, reason=reason, source=source, timestamp=timestamp),
        references=updated_refs,
        diagnostics=(f"Кривая добавлена: {curve_name}.", "Исходный LAS не перезаписывается; изменение выполняется в рабочей копии."),
    )


def delete_curve_managed(
    df: pd.DataFrame,
    curve_name: str,
    *,
    metadata: dict[str, Any] | None = None,
    history: Sequence[CurveManagerHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor.curve_manager",
    timestamp: str | None = None,
) -> CurveManagerResult:
    curve = normalize_las_mnemonic(curve_name)
    if is_depth_curve(curve):
        raise ValueError("Depth/reference curve cannot be deleted by Curve Manager.")
    updated_df = delete_las_curve(df, curve)
    updated_df = _copy_attrs(df, updated_df)
    metadata_map = normalize_curve_manager_metadata(metadata)
    metadata_map.pop(curve, None)
    manifest = build_curve_manifest(updated_df, metadata=metadata_map)
    updated_refs = update_curve_references(dict(references or {}), curve, "")
    updated_refs[CURVE_MANAGER_STORAGE_KEY] = {"manifest": manifest, "metadata": metadata_map}
    return CurveManagerResult(
        data=updated_df,
        manifest=manifest,
        history=_history(history, action="delete_curve", curve_name=curve, details={}, reason=reason, source=source, timestamp=timestamp),
        references=updated_refs,
        diagnostics=(f"Кривая удалена из рабочей копии: {curve}.",),
    )


def reorder_curves(
    df: pd.DataFrame,
    order: Iterable[str],
    *,
    metadata: dict[str, Any] | None = None,
    history: Sequence[CurveManagerHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor.curve_manager",
    timestamp: str | None = None,
) -> CurveManagerResult:
    current = list(_columns(df))
    requested = [normalize_las_mnemonic(item) for item in order]
    current_normalized = [normalize_las_mnemonic(item) for item in current]
    missing = [item for item in requested if item not in current_normalized]
    if missing:
        raise ValueError(f"Unknown curves in requested order: {', '.join(missing)}")
    new_order = requested + [item for item in current_normalized if item not in requested]
    if "DEPT" in current_normalized and new_order[0] != "DEPT":
        new_order = ["DEPT"] + [item for item in new_order if item != "DEPT"]
    column_by_normalized = {normalize_las_mnemonic(column): column for column in current}
    updated_df = df[[column_by_normalized[item] for item in new_order]].copy()
    updated_df = _copy_attrs(df, updated_df)
    manifest = build_curve_manifest(updated_df, metadata=metadata)
    updated_refs = dict(references or {})
    updated_refs[CURVE_MANAGER_STORAGE_KEY] = {"manifest": manifest, "metadata": normalize_curve_manager_metadata(metadata)}
    return CurveManagerResult(
        data=updated_df,
        manifest=manifest,
        history=_history(history, action="reorder_curves", curve_name="*", details={"order": new_order}, reason=reason, source=source, timestamp=timestamp),
        references=updated_refs,
        diagnostics=("Порядок кривых обновлен; глубинная кривая сохранена первой.",),
    )


def update_curve_manifest_entry(
    df: pd.DataFrame,
    curve_name: str,
    *,
    field: str,
    value: Any,
    metadata: dict[str, Any] | None = None,
    history: Sequence[CurveManagerHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor.curve_manager",
    timestamp: str | None = None,
) -> CurveManagerResult:
    curve = normalize_las_mnemonic(curve_name)
    if curve not in [normalize_las_mnemonic(column) for column in _columns(df)]:
        raise ValueError(f"Curve {curve!r} was not found.")
    field_key = str(field).strip().lower().replace("-", "_").replace(" ", "_")
    allowed = {"description", "alias", "group", "category", "unit", "quality", "status", "source", "comment"}
    if field_key not in allowed:
        raise ValueError(f"Unsupported Curve Manager field: {field_key}")
    metadata_map = normalize_curve_manager_metadata(metadata)
    row = dict(metadata_map.get(curve, {}))
    if field_key in {"alias"}:
        row[field_key] = normalize_las_mnemonic(str(value), fallback="") if str(value).strip() else ""
    elif field_key == "unit":
        row[field_key] = normalize_curve_unit(value)
    else:
        row[field_key] = str(value or "").strip()
    metadata_map[curve] = row
    manifest = build_curve_manifest(df, metadata=metadata_map)
    updated_refs = dict(references or {})
    updated_refs[CURVE_MANAGER_STORAGE_KEY] = {"manifest": manifest, "metadata": metadata_map}
    return CurveManagerResult(
        data=df.copy(),
        manifest=manifest,
        history=_history(history, action="update_manifest", curve_name=curve, details={"field": field_key, "value": row[field_key]}, reason=reason, source=source, timestamp=timestamp),
        references=updated_refs,
        diagnostics=(f"Metadata обновлена: {curve}.{field_key}.", "Значения LAS-кривой не изменялись."),
    )
