from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd

from las_correlation.core import CURVE_GROUP_LABELS
from las_editor.curve_grouping import build_curve_groups, normalize_curve_group, suggest_curve_group
from las_editor.curve_rename import normalize_curve_name

CURVE_CATEGORY_LABELS: dict[str, str] = {
    "depth_reference": "Depth reference",
    "petrophysics": "Petrophysics",
    "mud_gas": "Mud gas",
    "drilling": "Drilling",
    "interpretation": "Interpretation",
    "uncategorized": "Uncategorized",
}

CATEGORY_GROUP_RULES: dict[str, tuple[str, ...]] = {
    "depth_reference": ("depth",),
    "petrophysics": ("gamma", "resistivity", "density_neutron", "lithology"),
    "mud_gas": ("total_gas", "gas_component", "gas_ratio"),
    "drilling": ("drilling",),
    "interpretation": (),
    "uncategorized": ("other",),
}

GROUP_DEFAULT_CATEGORY: dict[str, str] = {
    group: category
    for category, groups in CATEGORY_GROUP_RULES.items()
    for group in groups
}


@dataclass(frozen=True)
class CurveCategoryHistoryEntry:
    curve_name: str
    category: str
    previous_category: str
    timestamp: str
    reason: str = "manual"
    source: str = "las_editor"


@dataclass(frozen=True)
class CurveCategoryResult:
    categories: dict[str, tuple[str, ...]]
    overrides: dict[str, str]
    history: tuple[CurveCategoryHistoryEntry, ...]
    references: dict[str, Any]
    diagnostics: tuple[str, ...] = ()
    assigned: bool = False
    curve_name: str = ""
    category: str = ""


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def available_curve_categories() -> tuple[str, ...]:
    """Return supported Curve Manager categories in deterministic UI order."""

    return tuple(CURVE_CATEGORY_LABELS.keys())


def normalize_curve_category(category: object) -> str:
    """Normalize a category name to a safe project key."""

    return "_".join(str(category).strip().lower().replace("-", "_").split())


def curve_category_label(category: object) -> str:
    """Return a human-readable label for a curve category key."""

    normalized = normalize_curve_category(category)
    return CURVE_CATEGORY_LABELS.get(normalized, normalized)


def suggest_curve_category(curve_name: object, *, group: str | None = None) -> str:
    """Suggest a business/engineering category for a LAS curve."""

    active_group = normalize_curve_group(group) if group else suggest_curve_group(curve_name)
    return GROUP_DEFAULT_CATEGORY.get(active_group, "uncategorized")


def suggest_curve_categories(columns: Iterable[object], *, group_overrides: dict[str, str] | None = None) -> dict[str, str]:
    """Suggest categories for every LAS curve using active group overrides."""

    overrides = {str(curve): normalize_curve_group(group) for curve, group in dict(group_overrides or {}).items()}
    return {
        str(column): suggest_curve_category(column, group=overrides.get(str(column)))
        for column in columns
    }


def _empty_categories() -> dict[str, list[str]]:
    return {category: [] for category in available_curve_categories()}


def build_curve_categories(
    columns: Iterable[object],
    *,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
) -> dict[str, tuple[str, ...]]:
    """Build deterministic curve categories with optional manual overrides."""

    categories = _empty_categories()
    group_map = {str(curve): normalize_curve_group(group) for curve, group in dict(group_overrides or {}).items()}
    category_map = {str(curve): normalize_curve_category(category) for curve, category in dict(category_overrides or {}).items()}
    for column in columns:
        curve_name = str(column)
        category = category_map.get(curve_name, suggest_curve_category(curve_name, group=group_map.get(curve_name)))
        if category not in CURVE_CATEGORY_LABELS:
            category = "uncategorized"
        categories[category].append(curve_name)
    return {category: tuple(values) for category, values in categories.items() if values}


def curve_category_table_rows(
    columns: Iterable[object],
    *,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    aliases: dict[str, str] | None = None,
) -> tuple[dict[str, str], ...]:
    """Return UI/report rows for curve category review."""

    group_map = {str(curve): normalize_curve_group(group) for curve, group in dict(group_overrides or {}).items()}
    category_map = {str(curve): normalize_curve_category(category) for curve, category in dict(category_overrides or {}).items()}
    alias_map = {str(curve): str(alias) for curve, alias in dict(aliases or {}).items()}
    rows: list[dict[str, str]] = []
    for column in columns:
        curve_name = str(column)
        active_group = group_map.get(curve_name, suggest_curve_group(curve_name))
        if active_group not in CURVE_GROUP_LABELS:
            active_group = "other"
        auto_category = suggest_curve_category(curve_name, group=active_group)
        active_category = category_map.get(curve_name, auto_category)
        if active_category not in CURVE_CATEGORY_LABELS:
            active_category = "uncategorized"
        rows.append(
            {
                "curve_name": curve_name,
                "alias": alias_map.get(curve_name, ""),
                "group": active_group,
                "group_label": CURVE_GROUP_LABELS.get(active_group, active_group),
                "auto_category": auto_category,
                "auto_category_label": CURVE_CATEGORY_LABELS.get(auto_category, auto_category),
                "category": active_category,
                "category_label": CURVE_CATEGORY_LABELS.get(active_category, active_category),
                "manual_override": "yes" if curve_name in category_map else "no",
            }
        )
    return tuple(rows)


def _update_category_references(
    references: dict[str, Any],
    curve_name: str,
    category: str,
    categories: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    updated = dict(references or {})
    updated["curve_categories"] = {key: list(values) for key, values in categories.items()}

    overrides = dict(updated.get("curve_category_overrides", {})) if isinstance(updated.get("curve_category_overrides"), dict) else {}
    overrides[curve_name] = category
    updated["curve_category_overrides"] = overrides

    manifest = updated.get("manifest")
    if isinstance(manifest, dict):
        manifest = dict(manifest)
        curve_manifest = dict(manifest.get(curve_name, {})) if isinstance(manifest.get(curve_name), dict) else {}
        curve_manifest["category"] = category
        curve_manifest["category_label"] = CURVE_CATEGORY_LABELS.get(category, category)
        manifest[curve_name] = curve_manifest
        updated["manifest"] = manifest

    return updated


def assign_curve_category(
    df: pd.DataFrame,
    curve_name: str,
    category: str,
    *,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None = None,
    history: tuple[CurveCategoryHistoryEntry, ...] | list[CurveCategoryHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor",
    timestamp: str | None = None,
) -> CurveCategoryResult:
    """Assign one LAS curve to a category without changing the dataframe."""

    columns = tuple(str(column) for column in df.columns)
    normalized_curve = normalize_curve_name(curve_name)
    normalized_category = normalize_curve_category(category)
    diagnostics: list[str] = []

    if not normalized_curve:
        raise ValueError("Кривая для категории не указана.")
    if normalized_curve not in columns:
        raise ValueError(f"Кривая {normalized_curve!r} не найдена.")
    diagnostics.append(f"Кривая найдена: {normalized_curve}.")

    if not normalized_category:
        raise ValueError("Категория кривой не может быть пустой.")
    if normalized_category not in CURVE_CATEGORY_LABELS:
        allowed = ", ".join(available_curve_categories())
        raise ValueError(f"Категория {normalized_category!r} не поддерживается. Доступно: {allowed}.")
    diagnostics.append(f"Категория нормализована: {normalized_category}.")

    group_map = {str(curve): normalize_curve_group(value) for curve, value in dict(group_overrides or {}).items()}
    current_overrides = {str(curve): normalize_curve_category(value) for curve, value in dict(category_overrides or {}).items()}
    previous_category = current_overrides.get(
        normalized_curve,
        suggest_curve_category(normalized_curve, group=group_map.get(normalized_curve)),
    )

    if previous_category == normalized_category and normalized_curve in current_overrides:
        categories = build_curve_categories(columns, group_overrides=group_map, category_overrides=current_overrides)
        return CurveCategoryResult(
            categories=categories,
            overrides=current_overrides,
            history=tuple(history),
            references=_update_category_references(dict(references or {}), normalized_curve, normalized_category, categories),
            diagnostics=tuple(diagnostics) + ("Категория уже была назначена: изменения не применены.",),
            assigned=False,
            curve_name=normalized_curve,
            category=normalized_category,
        )

    updated_overrides = dict(current_overrides)
    updated_overrides[normalized_curve] = normalized_category
    categories = build_curve_categories(columns, group_overrides=group_map, category_overrides=updated_overrides)
    entry = CurveCategoryHistoryEntry(
        curve_name=normalized_curve,
        category=normalized_category,
        previous_category=previous_category,
        timestamp=timestamp or _timestamp_utc(),
        reason=reason or "manual",
        source=source or "las_editor",
    )
    return CurveCategoryResult(
        categories=categories,
        overrides=updated_overrides,
        history=tuple(history) + (entry,),
        references=_update_category_references(dict(references or {}), normalized_curve, normalized_category, categories),
        diagnostics=tuple(diagnostics) + (f"Категория назначена: {normalized_curve} → {curve_category_label(normalized_category)}.",),
        assigned=True,
        curve_name=normalized_curve,
        category=normalized_category,
    )


def undo_last_category_assignment(
    df: pd.DataFrame,
    *,
    group_overrides: dict[str, str] | None = None,
    category_overrides: dict[str, str] | None,
    history: tuple[CurveCategoryHistoryEntry, ...] | list[CurveCategoryHistoryEntry],
    references: dict[str, Any] | None = None,
) -> CurveCategoryResult:
    """Undo the latest manual curve category assignment."""

    current_history = tuple(history)
    if not current_history:
        raise ValueError("История категорий пуста: отменять нечего.")

    last = current_history[-1]
    group_map = {str(curve): normalize_curve_group(value) for curve, value in dict(group_overrides or {}).items()}
    current_overrides = {str(curve): normalize_curve_category(value) for curve, value in dict(category_overrides or {}).items()}
    if current_overrides.get(last.curve_name) != last.category:
        raise ValueError("Нельзя отменить категорию: текущее назначение уже изменено.")

    automatic_category = suggest_curve_category(last.curve_name, group=group_map.get(last.curve_name))
    if last.previous_category and last.previous_category != automatic_category:
        current_overrides[last.curve_name] = last.previous_category
        restored_category = last.previous_category
    else:
        current_overrides.pop(last.curve_name, None)
        restored_category = automatic_category

    columns = tuple(str(column) for column in df.columns)
    categories = build_curve_categories(columns, group_overrides=group_map, category_overrides=current_overrides)
    updated_references = _update_category_references(dict(references or {}), last.curve_name, restored_category, categories)
    updated_references["curve_category_overrides"] = current_overrides

    return CurveCategoryResult(
        categories=categories,
        overrides=current_overrides,
        history=current_history[:-1],
        references=updated_references,
        diagnostics=(f"Отменена последняя категория для {last.curve_name}.",),
        assigned=True,
        curve_name=last.curve_name,
        category=restored_category,
    )


def category_summary_rows(categories: dict[str, tuple[str, ...]]) -> tuple[dict[str, str], ...]:
    """Return compact summary rows for UI cards and reports."""

    rows: list[dict[str, str]] = []
    for category in available_curve_categories():
        curves = tuple(categories.get(category, ()))
        rows.append(
            {
                "category": category,
                "category_label": curve_category_label(category),
                "curve_count": str(len(curves)),
                "curves": ", ".join(curves),
            }
        )
    return tuple(rows)
