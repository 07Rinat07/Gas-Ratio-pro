from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd

from las_correlation.core import CURVE_GROUP_LABELS, classify_curve_name
from las_editor.curve_rename import normalize_curve_name


@dataclass(frozen=True)
class CurveGroupingHistoryEntry:
    curve_name: str
    group: str
    previous_group: str
    timestamp: str
    reason: str = "manual"
    source: str = "las_editor"


@dataclass(frozen=True)
class CurveGroupingResult:
    groups: dict[str, tuple[str, ...]]
    overrides: dict[str, str]
    history: tuple[CurveGroupingHistoryEntry, ...]
    references: dict[str, Any]
    diagnostics: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    assigned: bool = False
    curve_name: str = ""
    group: str = ""


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def available_curve_groups() -> tuple[str, ...]:
    """Return supported Curve Manager group identifiers in UI order."""

    return tuple(CURVE_GROUP_LABELS.keys())


def curve_group_label(group: object) -> str:
    """Return a human-readable label for a curve group identifier."""

    normalized = normalize_curve_group(group)
    return CURVE_GROUP_LABELS.get(normalized, normalized)


def normalize_curve_group(group: object) -> str:
    """Normalize a manually selected curve group to a safe project key."""

    return "_".join(str(group).strip().lower().replace("-", "_").split())


def _column_names(df: pd.DataFrame) -> tuple[str, ...]:
    return tuple(str(column) for column in df.columns)


def _empty_groups() -> dict[str, list[str]]:
    return {group: [] for group in available_curve_groups()}


def suggest_curve_group(curve_name: object) -> str:
    """Suggest a Curve Manager group using existing LAS correlation classification rules."""

    return classify_curve_name(curve_name)


def suggest_curve_groups(columns: Iterable[object]) -> dict[str, str]:
    """Suggest groups for every curve in a LAS dataframe."""

    return {str(column): suggest_curve_group(column) for column in columns}


def build_curve_groups(
    columns: Iterable[object],
    *,
    overrides: dict[str, str] | None = None,
) -> dict[str, tuple[str, ...]]:
    """Build deterministic curve groups for LAS columns with optional manual overrides."""

    groups = _empty_groups()
    normalized_overrides = {str(curve): normalize_curve_group(group) for curve, group in dict(overrides or {}).items()}
    for column in columns:
        curve_name = str(column)
        group = normalized_overrides.get(curve_name, suggest_curve_group(curve_name))
        if group not in CURVE_GROUP_LABELS:
            group = "other"
        groups[group].append(curve_name)
    return {group: tuple(values) for group, values in groups.items() if values}


def curve_group_table_rows(
    columns: Iterable[object],
    *,
    overrides: dict[str, str] | None = None,
    aliases: dict[str, str] | None = None,
) -> tuple[dict[str, str], ...]:
    """Return UI/report rows that show automatic group, active group and alias per curve."""

    override_map = {str(curve): normalize_curve_group(group) for curve, group in dict(overrides or {}).items()}
    alias_map = {str(curve): str(alias) for curve, alias in dict(aliases or {}).items()}
    rows: list[dict[str, str]] = []
    for column in columns:
        curve_name = str(column)
        automatic_group = suggest_curve_group(curve_name)
        active_group = override_map.get(curve_name, automatic_group)
        if active_group not in CURVE_GROUP_LABELS:
            active_group = "other"
        rows.append(
            {
                "curve_name": curve_name,
                "alias": alias_map.get(curve_name, ""),
                "auto_group": automatic_group,
                "auto_group_label": CURVE_GROUP_LABELS.get(automatic_group, automatic_group),
                "group": active_group,
                "group_label": CURVE_GROUP_LABELS.get(active_group, active_group),
                "manual_override": "yes" if curve_name in override_map else "no",
            }
        )
    return tuple(rows)


def _update_group_references(references: dict[str, Any], curve_name: str, group: str, groups: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    updated = dict(references or {})
    updated["curve_groups"] = {key: list(values) for key, values in groups.items()}

    overrides = dict(updated.get("curve_group_overrides", {})) if isinstance(updated.get("curve_group_overrides"), dict) else {}
    overrides[curve_name] = group
    updated["curve_group_overrides"] = overrides

    manifest = updated.get("manifest")
    if isinstance(manifest, dict):
        manifest = dict(manifest)
        curve_manifest = dict(manifest.get(curve_name, {})) if isinstance(manifest.get(curve_name), dict) else {}
        curve_manifest["group"] = group
        curve_manifest["group_label"] = CURVE_GROUP_LABELS.get(group, group)
        manifest[curve_name] = curve_manifest
        updated["manifest"] = manifest

    return updated


def assign_curve_group(
    df: pd.DataFrame,
    curve_name: str,
    group: str,
    *,
    overrides: dict[str, str] | None = None,
    history: tuple[CurveGroupingHistoryEntry, ...] | list[CurveGroupingHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor",
    timestamp: str | None = None,
) -> CurveGroupingResult:
    """Assign one LAS curve to a Curve Manager group without changing the dataframe."""

    columns = _column_names(df)
    normalized_curve = normalize_curve_name(curve_name)
    normalized_group = normalize_curve_group(group)
    diagnostics: list[str] = []

    if not normalized_curve:
        raise ValueError("Кривая для группировки не указана.")
    if normalized_curve not in columns:
        raise ValueError(f"Кривая {normalized_curve!r} не найдена.")
    diagnostics.append(f"Кривая найдена: {normalized_curve}.")

    if not normalized_group:
        raise ValueError("Группа кривой не может быть пустой.")
    if normalized_group not in CURVE_GROUP_LABELS:
        allowed = ", ".join(available_curve_groups())
        raise ValueError(f"Группа {normalized_group!r} не поддерживается. Доступно: {allowed}.")
    diagnostics.append(f"Группа нормализована: {normalized_group}.")

    current_overrides = {str(curve): normalize_curve_group(value) for curve, value in dict(overrides or {}).items()}
    previous_group = current_overrides.get(normalized_curve, suggest_curve_group(normalized_curve))
    if previous_group == normalized_group and normalized_curve in current_overrides:
        groups = build_curve_groups(columns, overrides=current_overrides)
        return CurveGroupingResult(
            groups=groups,
            overrides=current_overrides,
            history=tuple(history),
            references=_update_group_references(dict(references or {}), normalized_curve, normalized_group, groups),
            diagnostics=tuple(diagnostics) + ("Группа уже была назначена: изменения не применены.",),
            assigned=False,
            curve_name=normalized_curve,
            group=normalized_group,
        )

    updated_overrides = dict(current_overrides)
    updated_overrides[normalized_curve] = normalized_group
    groups = build_curve_groups(columns, overrides=updated_overrides)
    entry = CurveGroupingHistoryEntry(
        curve_name=normalized_curve,
        group=normalized_group,
        previous_group=previous_group,
        timestamp=timestamp or _timestamp_utc(),
        reason=reason or "manual",
        source=source or "las_editor",
    )
    return CurveGroupingResult(
        groups=groups,
        overrides=updated_overrides,
        history=tuple(history) + (entry,),
        references=_update_group_references(dict(references or {}), normalized_curve, normalized_group, groups),
        diagnostics=tuple(diagnostics) + (f"Группа назначена: {normalized_curve} → {curve_group_label(normalized_group)}.",),
        assigned=True,
        curve_name=normalized_curve,
        group=normalized_group,
    )


def undo_last_group_assignment(
    df: pd.DataFrame,
    *,
    overrides: dict[str, str] | None,
    history: tuple[CurveGroupingHistoryEntry, ...] | list[CurveGroupingHistoryEntry],
    references: dict[str, Any] | None = None,
) -> CurveGroupingResult:
    """Undo the latest manual curve grouping assignment."""

    current_history = tuple(history)
    if not current_history:
        raise ValueError("История группировки пуста: отменять нечего.")

    last = current_history[-1]
    current_overrides = {str(curve): normalize_curve_group(value) for curve, value in dict(overrides or {}).items()}
    if current_overrides.get(last.curve_name) != last.group:
        raise ValueError("Нельзя отменить группировку: текущее назначение уже изменено.")

    automatic_group = suggest_curve_group(last.curve_name)
    if last.previous_group and last.previous_group != automatic_group:
        current_overrides[last.curve_name] = last.previous_group
        restored_group = last.previous_group
    else:
        current_overrides.pop(last.curve_name, None)
        restored_group = automatic_group

    columns = _column_names(df)
    groups = build_curve_groups(columns, overrides=current_overrides)
    updated_references = _update_group_references(dict(references or {}), last.curve_name, restored_group, groups)
    updated_references["curve_group_overrides"] = current_overrides

    return CurveGroupingResult(
        groups=groups,
        overrides=current_overrides,
        history=current_history[:-1],
        references=updated_references,
        diagnostics=(f"Отменена последняя группировка для {last.curve_name}.",),
        assigned=True,
        curve_name=last.curve_name,
        group=restored_group,
    )
