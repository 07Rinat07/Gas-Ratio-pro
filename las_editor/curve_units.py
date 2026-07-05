from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd

from las_editor.curve_categories import CURVE_CATEGORY_LABELS, suggest_curve_category
from las_editor.curve_grouping import normalize_curve_group, suggest_curve_group
from las_editor.curve_rename import normalize_curve_name

CURVE_UNIT_LABELS: dict[str, str] = {
    "m": "metre",
    "ft": "foot",
    "api": "API gamma ray",
    "ohmm": "ohm·m",
    "g_cm3": "g/cm³",
    "v_v": "v/v",
    "percent": "%",
    "ppm": "ppm",
    "unitless": "unitless",
    "m_h": "m/h",
    "unknown": "unknown",
}

GROUP_DEFAULT_UNIT: dict[str, str] = {
    "depth": "m",
    "gamma": "api",
    "resistivity": "ohmm",
    "density_neutron": "g_cm3",
    "lithology": "unitless",
    "total_gas": "percent",
    "gas_component": "percent",
    "gas_ratio": "unitless",
    "drilling": "m_h",
    "other": "unknown",
}

CATEGORY_DEFAULT_UNIT: dict[str, str] = {
    "depth_reference": "m",
    "petrophysics": "unitless",
    "mud_gas": "percent",
    "drilling": "m_h",
    "interpretation": "unitless",
    "uncategorized": "unknown",
}

UNIT_CONVERSIONS: dict[tuple[str, str], float] = {
    ("m", "ft"): 3.280839895,
    ("ft", "m"): 0.3048,
    ("v_v", "percent"): 100.0,
    ("percent", "v_v"): 0.01,
    ("percent", "ppm"): 10000.0,
    ("ppm", "percent"): 0.0001,
    ("v_v", "ppm"): 1_000_000.0,
    ("ppm", "v_v"): 0.000001,
}


@dataclass(frozen=True)
class CurveUnitHistoryEntry:
    curve_name: str
    unit: str
    previous_unit: str
    timestamp: str
    reason: str = "manual"
    source: str = "las_editor"


@dataclass(frozen=True)
class CurveUnitResult:
    units: dict[str, str]
    overrides: dict[str, str]
    history: tuple[CurveUnitHistoryEntry, ...]
    references: dict[str, Any]
    diagnostics: tuple[str, ...] = ()
    assigned: bool = False
    curve_name: str = ""
    unit: str = ""


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def available_curve_units() -> tuple[str, ...]:
    """Return supported unit identifiers in stable UI order."""

    return tuple(CURVE_UNIT_LABELS.keys())


def normalize_curve_unit(unit: object) -> str:
    """Normalize a LAS unit to a safe project key."""

    value = str(unit).strip().lower().replace("-", "_").replace("/", "_")
    value = value.replace("%", "percent").replace(".", "")
    value = value.replace(" ", "_")
    aliases = {
        "": "unknown",
        "meter": "m",
        "metre": "m",
        "meters": "m",
        "metres": "m",
        "feet": "ft",
        "foot": "ft",
        "ohm_m": "ohmm",
        "ohm·m": "ohmm",
        "g_cm³": "g_cm3",
        "g_cc": "g_cm3",
        "fraction": "v_v",
        "decimal": "v_v",
        "pct": "percent",
        "perc": "percent",
        "%": "percent",
        "none": "unitless",
        "dimensionless": "unitless",
    }
    return aliases.get(value, "_".join(value.split()))


def curve_unit_label(unit: object) -> str:
    normalized = normalize_curve_unit(unit)
    return CURVE_UNIT_LABELS.get(normalized, normalized)


def suggest_curve_unit(curve_name: object, *, group: str | None = None, category: str | None = None) -> str:
    """Suggest a default LAS unit from curve group/category rules."""

    if group:
        normalized_group = normalize_curve_group(group)
        if normalized_group in GROUP_DEFAULT_UNIT:
            return GROUP_DEFAULT_UNIT[normalized_group]
    if category:
        normalized_category = str(category).strip().lower().replace("-", "_")
        if normalized_category in CATEGORY_DEFAULT_UNIT:
            return CATEGORY_DEFAULT_UNIT[normalized_category]
    detected_group = suggest_curve_group(curve_name)
    detected_category = suggest_curve_category(curve_name, group=detected_group)
    return GROUP_DEFAULT_UNIT.get(detected_group, CATEGORY_DEFAULT_UNIT.get(detected_category, "unknown"))


def suggest_curve_units(
    columns: Iterable[object],
    *,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    group_map = {str(curve): normalize_curve_group(group) for curve, group in dict(group_overrides or {}).items()}
    category_map = {str(curve): str(category).strip().lower().replace("-", "_") for curve, category in dict(category_overrides or {}).items()}
    return {
        str(column): suggest_curve_unit(column, group=group_map.get(str(column)), category=category_map.get(str(column)))
        for column in columns
    }


def build_curve_units(
    columns: Iterable[object],
    *,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    unit_overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    unit_map = {str(curve): normalize_curve_unit(unit) for curve, unit in dict(unit_overrides or {}).items()}
    suggested = suggest_curve_units(columns, group_overrides=group_overrides, category_overrides=category_overrides)
    units: dict[str, str] = {}
    for column in columns:
        curve_name = str(column)
        unit = unit_map.get(curve_name, suggested.get(curve_name, "unknown"))
        if unit not in CURVE_UNIT_LABELS:
            unit = "unknown"
        units[curve_name] = unit
    return units


def curve_unit_table_rows(
    columns: Iterable[object],
    *,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    unit_overrides: dict[str, str] | None = None,
    aliases: dict[str, str] | None = None,
) -> tuple[dict[str, str], ...]:
    group_map = {str(curve): normalize_curve_group(group) for curve, group in dict(group_overrides or {}).items()}
    category_map = {str(curve): str(category).strip().lower().replace("-", "_") for curve, category in dict(category_overrides or {}).items()}
    unit_map = {str(curve): normalize_curve_unit(unit) for curve, unit in dict(unit_overrides or {}).items()}
    alias_map = {str(curve): str(alias) for curve, alias in dict(aliases or {}).items()}
    rows: list[dict[str, str]] = []
    for column in columns:
        curve_name = str(column)
        group = group_map.get(curve_name, suggest_curve_group(curve_name))
        category = category_map.get(curve_name, suggest_curve_category(curve_name, group=group))
        if category not in CURVE_CATEGORY_LABELS:
            category = "uncategorized"
        auto_unit = suggest_curve_unit(curve_name, group=group, category=category)
        unit = unit_map.get(curve_name, auto_unit)
        if unit not in CURVE_UNIT_LABELS:
            unit = "unknown"
        rows.append({
            "curve_name": curve_name,
            "alias": alias_map.get(curve_name, ""),
            "group": group,
            "category": category,
            "category_label": CURVE_CATEGORY_LABELS.get(category, category),
            "auto_unit": auto_unit,
            "auto_unit_label": curve_unit_label(auto_unit),
            "unit": unit,
            "unit_label": curve_unit_label(unit),
            "manual_override": "yes" if curve_name in unit_map else "no",
            "convertible_targets": ", ".join(target for source, target in UNIT_CONVERSIONS if source == unit),
        })
    return tuple(rows)


def _update_unit_references(references: dict[str, Any], curve_name: str, unit: str, units: dict[str, str]) -> dict[str, Any]:
    updated = dict(references or {})
    updated["curve_units"] = dict(units)
    overrides = dict(updated.get("curve_unit_overrides", {})) if isinstance(updated.get("curve_unit_overrides"), dict) else {}
    overrides[curve_name] = unit
    updated["curve_unit_overrides"] = overrides
    manifest = updated.get("manifest")
    if isinstance(manifest, dict):
        manifest = dict(manifest)
        curve_manifest = dict(manifest.get(curve_name, {})) if isinstance(manifest.get(curve_name), dict) else {}
        curve_manifest["unit"] = unit
        curve_manifest["unit_label"] = curve_unit_label(unit)
        manifest[curve_name] = curve_manifest
        updated["manifest"] = manifest
    return updated


def assign_curve_unit(
    df: pd.DataFrame,
    curve_name: str,
    unit: str,
    *,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    unit_overrides: dict[str, str] | None = None,
    history: tuple[CurveUnitHistoryEntry, ...] | list[CurveUnitHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor",
    timestamp: str | None = None,
) -> CurveUnitResult:
    columns = tuple(str(column) for column in df.columns)
    normalized_curve = normalize_curve_name(curve_name)
    normalized_unit = normalize_curve_unit(unit)
    diagnostics: list[str] = []
    if not normalized_curve:
        raise ValueError("Кривая для единиц измерения не указана.")
    if normalized_curve not in columns:
        raise ValueError(f"Кривая {normalized_curve!r} не найдена.")
    diagnostics.append(f"Кривая найдена: {normalized_curve}.")
    if normalized_unit not in CURVE_UNIT_LABELS:
        allowed = ", ".join(available_curve_units())
        raise ValueError(f"Единица {normalized_unit!r} не поддерживается. Доступно: {allowed}.")
    diagnostics.append(f"Единица нормализована: {normalized_unit}.")
    current_overrides = {str(curve): normalize_curve_unit(value) for curve, value in dict(unit_overrides or {}).items()}
    previous_unit = current_overrides.get(
        normalized_curve,
        suggest_curve_unit(
            normalized_curve,
            group=dict(group_overrides or {}).get(normalized_curve),
            category=dict(category_overrides or {}).get(normalized_curve),
        ),
    )
    if previous_unit == normalized_unit and normalized_curve in current_overrides:
        units = build_curve_units(columns, group_overrides=group_overrides, category_overrides=category_overrides, unit_overrides=current_overrides)
        return CurveUnitResult(units, current_overrides, tuple(history), _update_unit_references(dict(references or {}), normalized_curve, normalized_unit, units), tuple(diagnostics) + ("Единица уже была назначена: изменения не применены.",), False, normalized_curve, normalized_unit)
    updated_overrides = dict(current_overrides)
    updated_overrides[normalized_curve] = normalized_unit
    units = build_curve_units(columns, group_overrides=group_overrides, category_overrides=category_overrides, unit_overrides=updated_overrides)
    entry = CurveUnitHistoryEntry(normalized_curve, normalized_unit, previous_unit, timestamp or _timestamp_utc(), reason or "manual", source or "las_editor")
    return CurveUnitResult(units, updated_overrides, tuple(history) + (entry,), _update_unit_references(dict(references or {}), normalized_curve, normalized_unit, units), tuple(diagnostics) + (f"Единица назначена: {normalized_curve} → {curve_unit_label(normalized_unit)}.",), True, normalized_curve, normalized_unit)


def undo_last_unit_assignment(
    df: pd.DataFrame,
    *,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    unit_overrides: dict[str, str] | None,
    history: tuple[CurveUnitHistoryEntry, ...] | list[CurveUnitHistoryEntry],
    references: dict[str, Any] | None = None,
) -> CurveUnitResult:
    current_history = tuple(history)
    if not current_history:
        raise ValueError("История единиц пуста: отменять нечего.")
    last = current_history[-1]
    current_overrides = {str(curve): normalize_curve_unit(value) for curve, value in dict(unit_overrides or {}).items()}
    if current_overrides.get(last.curve_name) != last.unit:
        raise ValueError("Нельзя отменить единицу: текущее назначение уже изменено.")
    automatic_unit = suggest_curve_unit(last.curve_name, group=dict(group_overrides or {}).get(last.curve_name), category=dict(category_overrides or {}).get(last.curve_name))
    if last.previous_unit and last.previous_unit != automatic_unit:
        current_overrides[last.curve_name] = last.previous_unit
        restored_unit = last.previous_unit
    else:
        current_overrides.pop(last.curve_name, None)
        restored_unit = automatic_unit
    columns = tuple(str(column) for column in df.columns)
    units = build_curve_units(columns, group_overrides=group_overrides, category_overrides=category_overrides, unit_overrides=current_overrides)
    refs = _update_unit_references(dict(references or {}), last.curve_name, restored_unit, units)
    refs["curve_unit_overrides"] = current_overrides
    return CurveUnitResult(units, current_overrides, current_history[:-1], refs, (f"Отменена последняя единица для {last.curve_name}.",), True, last.curve_name, restored_unit)


def unit_summary_rows(units: dict[str, str]) -> tuple[dict[str, str], ...]:
    buckets: dict[str, list[str]] = {unit: [] for unit in available_curve_units()}
    for curve, unit in units.items():
        buckets.setdefault(normalize_curve_unit(unit), []).append(curve)
    return tuple({"unit": unit, "unit_label": curve_unit_label(unit), "curve_count": str(len(curves)), "curves": ", ".join(curves)} for unit, curves in buckets.items())


def conversion_factor(source_unit: object, target_unit: object) -> float:
    source = normalize_curve_unit(source_unit)
    target = normalize_curve_unit(target_unit)
    if source == target:
        return 1.0
    try:
        return UNIT_CONVERSIONS[(source, target)]
    except KeyError as exc:
        raise ValueError(f"Нет безопасного коэффициента пересчета {source} → {target}.") from exc
