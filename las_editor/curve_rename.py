from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CurveRenameHistoryEntry:
    old_name: str
    new_name: str
    timestamp: str
    reason: str = "manual"
    source: str = "las_editor"


@dataclass(frozen=True)
class CurveRenameResult:
    data: pd.DataFrame
    history: tuple[CurveRenameHistoryEntry, ...]
    references: dict[str, Any]
    diagnostics: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    renamed: bool = False
    old_name: str = ""
    new_name: str = ""


def normalize_curve_name(name: object) -> str:
    """Normalize a LAS curve name entered by a user.

    LAS curve mnemonics are usually short identifiers. The editor keeps the
    user's case, but trims surrounding whitespace and collapses internal
    whitespace to underscores so references remain safe for tables, templates,
    exports and manifests.
    """

    normalized = "_".join(str(name).strip().split())
    return normalized


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _column_names(df: pd.DataFrame) -> tuple[str, ...]:
    return tuple(str(column) for column in df.columns)


def _validate_rename(df: pd.DataFrame, old_name: str, new_name: str) -> tuple[str, tuple[str, ...]]:
    columns = _column_names(df)
    normalized_old = normalize_curve_name(old_name)
    normalized_new = normalize_curve_name(new_name)
    diagnostics: list[str] = []

    if not normalized_old:
        raise ValueError("Старая кривая не указана.")
    if normalized_old not in columns:
        raise ValueError(f"Кривая {normalized_old!r} не найдена.")
    diagnostics.append(f"Исходная кривая найдена: {normalized_old}.")

    if not normalized_new:
        raise ValueError("Новое имя кривой не может быть пустым.")
    diagnostics.append(f"Новое имя нормализовано: {normalized_new}.")

    if normalized_new != normalized_old and normalized_new in columns:
        raise ValueError(f"Кривая {normalized_new!r} уже существует.")
    if normalized_new == normalized_old:
        diagnostics.append("Новое имя совпадает с исходным: данные не изменены.")
    return normalized_new, tuple(diagnostics)


def update_curve_references(value: Any, old_name: str, new_name: str) -> Any:
    """Recursively update saved curve references in metadata-like objects.

    The project stores several user-facing structures as dictionaries/lists in
    session state or JSON metadata: tablet tracks, templates, presets, saved
    calculations, export metadata and manifests. This function intentionally
    works with generic Python containers so the same safe rename rule can be
    reused for all currently existing structures without binding to one storage
    schema.
    """

    if isinstance(value, str):
        return new_name if value == old_name else value
    if isinstance(value, list):
        return [update_curve_references(item, old_name, new_name) for item in value]
    if isinstance(value, tuple):
        return tuple(update_curve_references(item, old_name, new_name) for item in value)
    if isinstance(value, set):
        return {update_curve_references(item, old_name, new_name) for item in value}
    if isinstance(value, dict):
        updated: dict[Any, Any] = {}
        for key, item in value.items():
            updated_key = update_curve_references(key, old_name, new_name)
            updated[updated_key] = update_curve_references(item, old_name, new_name)
        return updated
    return value


def rename_curve(
    df: pd.DataFrame,
    old_name: str,
    new_name: str,
    *,
    history: tuple[CurveRenameHistoryEntry, ...] | list[CurveRenameHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor",
    timestamp: str | None = None,
) -> CurveRenameResult:
    """Safely rename one LAS curve and update known references."""

    normalized_old = normalize_curve_name(old_name)
    normalized_new, diagnostics = _validate_rename(df, normalized_old, new_name)
    references = dict(references or {})

    if normalized_new == normalized_old:
        return CurveRenameResult(
            data=df.copy(),
            history=tuple(history),
            references=references,
            diagnostics=diagnostics,
            renamed=False,
            old_name=normalized_old,
            new_name=normalized_new,
        )

    renamed_df = df.copy().rename(columns={normalized_old: normalized_new})
    updated_references = update_curve_references(references, normalized_old, normalized_new)
    entry = CurveRenameHistoryEntry(
        old_name=normalized_old,
        new_name=normalized_new,
        timestamp=timestamp or _timestamp_utc(),
        reason=reason or "manual",
        source=source or "las_editor",
    )
    updated_history = tuple(history) + (entry,)
    updated_diagnostics = diagnostics + (
        f"Кривая переименована: {normalized_old} → {normalized_new}.",
        "Ссылки на кривую обновлены в переданных tablet tracks/templates/presets/calculations/exports/manifest.",
    )

    return CurveRenameResult(
        data=renamed_df,
        history=updated_history,
        references=updated_references,
        diagnostics=updated_diagnostics,
        renamed=True,
        old_name=normalized_old,
        new_name=normalized_new,
    )


def undo_last_rename(
    df: pd.DataFrame,
    *,
    history: tuple[CurveRenameHistoryEntry, ...] | list[CurveRenameHistoryEntry],
    references: dict[str, Any] | None = None,
) -> CurveRenameResult:
    """Undo the latest curve rename if the original name is currently free."""

    current_history = tuple(history)
    if not current_history:
        raise ValueError("История переименований пуста: отменять нечего.")

    last = current_history[-1]
    columns = _column_names(df)
    if last.new_name not in columns:
        raise ValueError(f"Текущая кривая {last.new_name!r} не найдена.")
    if last.old_name in columns and last.old_name != last.new_name:
        raise ValueError(f"Нельзя отменить rename: имя {last.old_name!r} уже занято.")

    restored_df = df.copy().rename(columns={last.new_name: last.old_name})
    updated_references = update_curve_references(dict(references or {}), last.new_name, last.old_name)
    diagnostics = (
        f"Отменено последнее переименование: {last.new_name} → {last.old_name}.",
        "Ссылки на кривую восстановлены в переданных metadata-структурах.",
    )
    return CurveRenameResult(
        data=restored_df,
        history=current_history[:-1],
        references=updated_references,
        diagnostics=diagnostics,
        renamed=True,
        old_name=last.new_name,
        new_name=last.old_name,
    )
