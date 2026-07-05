from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from mapping.curve_aliases import CURVE_ALIASES
from mapping.mapper import detect_standard_field


@dataclass(frozen=True)
class CurveAliasHistoryEntry:
    curve_name: str
    alias: str
    previous_alias: str
    timestamp: str
    reason: str = "manual"
    source: str = "las_editor"


@dataclass(frozen=True)
class CurveAliasResult:
    aliases: dict[str, str]
    history: tuple[CurveAliasHistoryEntry, ...]
    references: dict[str, Any]
    diagnostics: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    assigned: bool = False
    curve_name: str = ""
    alias: str = ""


def available_aliases() -> tuple[str, ...]:
    """Return supported canonical aliases for LAS curve classification."""

    return tuple(CURVE_ALIASES.keys())


def normalize_alias_name(alias: object) -> str:
    """Normalize a user-selected alias to the project's canonical lowercase key."""

    return "_".join(str(alias).strip().lower().split())


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _column_names(df: pd.DataFrame) -> tuple[str, ...]:
    return tuple(str(column) for column in df.columns)


def suggest_curve_alias(curve_name: object) -> str:
    """Suggest a canonical alias using the existing auto-mapping dictionary."""

    return detect_standard_field(curve_name) or ""


def suggest_curve_aliases(columns) -> dict[str, str]:
    """Suggest aliases for every column where the project can detect a standard field."""

    suggestions: dict[str, str] = {}
    for column in columns:
        name = str(column)
        alias = suggest_curve_alias(name)
        if alias:
            suggestions[name] = alias
    return suggestions


def validate_curve_alias(
    df: pd.DataFrame,
    curve_name: str,
    alias: str,
    *,
    aliases: dict[str, str] | None = None,
) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
    """Validate alias assignment and return normalized curve/alias plus messages."""

    columns = _column_names(df)
    normalized_curve = str(curve_name).strip()
    normalized_alias = normalize_alias_name(alias)
    diagnostics: list[str] = []
    warnings: list[str] = []

    if not normalized_curve:
        raise ValueError("Кривая для alias не указана.")
    if normalized_curve not in columns:
        raise ValueError(f"Кривая {normalized_curve!r} не найдена.")
    diagnostics.append(f"Кривая найдена: {normalized_curve}.")

    if not normalized_alias:
        raise ValueError("Alias не может быть пустым.")
    if normalized_alias not in available_aliases():
        allowed = ", ".join(available_aliases())
        raise ValueError(f"Alias {normalized_alias!r} не поддерживается. Доступно: {allowed}.")
    diagnostics.append(f"Alias нормализован: {normalized_alias}.")

    current_aliases = dict(aliases or {})
    for other_curve, other_alias in current_aliases.items():
        if str(other_curve) != normalized_curve and other_alias == normalized_alias:
            warnings.append(
                f"Alias {normalized_alias} уже назначен кривой {other_curve}; "
                "будет отмечен конфликт классификации."
            )
            break

    suggested = suggest_curve_alias(normalized_curve)
    if suggested and suggested != normalized_alias:
        warnings.append(f"Автоопределение предлагает alias {suggested}, выбран {normalized_alias}.")

    return normalized_curve, normalized_alias, tuple(diagnostics), tuple(warnings)


def _update_alias_references(references: dict[str, Any], curve_name: str, alias: str) -> dict[str, Any]:
    updated = dict(references or {})
    manifest = updated.get("manifest")
    if isinstance(manifest, dict):
        curve_manifest = dict(manifest.get(curve_name, {})) if isinstance(manifest.get(curve_name), dict) else {}
        curve_manifest["alias"] = alias
        manifest = dict(manifest)
        manifest[curve_name] = curve_manifest
        updated["manifest"] = manifest

    alias_map = dict(updated.get("curve_aliases", {})) if isinstance(updated.get("curve_aliases"), dict) else {}
    alias_map[curve_name] = alias
    updated["curve_aliases"] = alias_map
    return updated


def assign_curve_alias(
    df: pd.DataFrame,
    curve_name: str,
    alias: str,
    *,
    aliases: dict[str, str] | None = None,
    history: tuple[CurveAliasHistoryEntry, ...] | list[CurveAliasHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor",
    timestamp: str | None = None,
) -> CurveAliasResult:
    """Assign a canonical alias to an existing LAS curve without renaming data."""

    current_aliases = dict(aliases or {})
    normalized_curve, normalized_alias, diagnostics, warnings = validate_curve_alias(
        df,
        curve_name,
        alias,
        aliases=current_aliases,
    )
    previous_alias = current_aliases.get(normalized_curve, "")

    if previous_alias == normalized_alias:
        return CurveAliasResult(
            aliases=current_aliases,
            history=tuple(history),
            references=_update_alias_references(dict(references or {}), normalized_curve, normalized_alias),
            diagnostics=diagnostics + ("Alias уже был назначен: изменения не применены.",),
            warnings=warnings,
            assigned=False,
            curve_name=normalized_curve,
            alias=normalized_alias,
        )

    updated_aliases = dict(current_aliases)
    updated_aliases[normalized_curve] = normalized_alias
    entry = CurveAliasHistoryEntry(
        curve_name=normalized_curve,
        alias=normalized_alias,
        previous_alias=previous_alias,
        timestamp=timestamp or _timestamp_utc(),
        reason=reason or "manual",
        source=source or "las_editor",
    )
    updated_references = _update_alias_references(dict(references or {}), normalized_curve, normalized_alias)
    return CurveAliasResult(
        aliases=updated_aliases,
        history=tuple(history) + (entry,),
        references=updated_references,
        diagnostics=diagnostics + (f"Alias назначен: {normalized_curve} → {normalized_alias}.",),
        warnings=warnings,
        assigned=True,
        curve_name=normalized_curve,
        alias=normalized_alias,
    )


def undo_last_alias(
    *,
    aliases: dict[str, str] | None,
    history: tuple[CurveAliasHistoryEntry, ...] | list[CurveAliasHistoryEntry],
    references: dict[str, Any] | None = None,
) -> CurveAliasResult:
    """Undo the latest alias assignment and restore the previous alias state."""

    current_history = tuple(history)
    if not current_history:
        raise ValueError("История alias пуста: отменять нечего.")

    current_aliases = dict(aliases or {})
    last = current_history[-1]
    if current_aliases.get(last.curve_name) != last.alias:
        raise ValueError("Нельзя отменить alias: текущее назначение уже изменено.")

    if last.previous_alias:
        current_aliases[last.curve_name] = last.previous_alias
        restored_alias = last.previous_alias
    else:
        current_aliases.pop(last.curve_name, None)
        restored_alias = ""

    updated_references = dict(references or {})
    alias_map = dict(updated_references.get("curve_aliases", {})) if isinstance(updated_references.get("curve_aliases"), dict) else {}
    if restored_alias:
        alias_map[last.curve_name] = restored_alias
    else:
        alias_map.pop(last.curve_name, None)
    updated_references["curve_aliases"] = alias_map

    manifest = updated_references.get("manifest")
    if isinstance(manifest, dict) and isinstance(manifest.get(last.curve_name), dict):
        manifest = dict(manifest)
        curve_manifest = dict(manifest[last.curve_name])
        if restored_alias:
            curve_manifest["alias"] = restored_alias
        else:
            curve_manifest.pop("alias", None)
        manifest[last.curve_name] = curve_manifest
        updated_references["manifest"] = manifest

    return CurveAliasResult(
        aliases=current_aliases,
        history=current_history[:-1],
        references=updated_references,
        diagnostics=(f"Отменено последнее alias-назначение для {last.curve_name}.",),
        assigned=True,
        curve_name=last.curve_name,
        alias=restored_alias,
    )
