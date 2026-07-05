from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd

from las_editor.curve_rename import normalize_curve_name, update_curve_references

MERGE_STRATEGIES: tuple[str, ...] = ("coalesce_first", "coalesce_last", "mean", "sum")


@dataclass(frozen=True)
class CurveMergeHistoryEntry:
    source_names: tuple[str, ...]
    target_name: str
    strategy: str
    timestamp: str
    reason: str = "manual"
    source: str = "las_editor"
    keep_sources: bool = True


@dataclass(frozen=True)
class CurveMergeResult:
    data: pd.DataFrame
    history: tuple[CurveMergeHistoryEntry, ...]
    references: dict[str, Any]
    diagnostics: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    merged: bool = False
    source_names: tuple[str, ...] = ()
    target_name: str = ""
    strategy: str = ""


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_merge_strategy(strategy: object) -> str:
    normalized = str(strategy).strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in MERGE_STRATEGIES:
        allowed = ", ".join(MERGE_STRATEGIES)
        raise ValueError(f"Стратегия merge {normalized!r} не поддерживается. Доступно: {allowed}.")
    return normalized


def _column_names(df: pd.DataFrame) -> tuple[str, ...]:
    return tuple(str(column) for column in df.columns)


def normalize_source_names(source_names: Iterable[object]) -> tuple[str, ...]:
    normalized: list[str] = []
    for name in source_names:
        curve_name = normalize_curve_name(name)
        if curve_name and curve_name not in normalized:
            normalized.append(curve_name)
    return tuple(normalized)


def validate_curve_merge(
    df: pd.DataFrame,
    source_names: Iterable[object],
    target_name: object,
    strategy: object,
    *,
    keep_sources: bool = True,
) -> tuple[tuple[str, ...], str, str, tuple[str, ...], tuple[str, ...]]:
    columns = _column_names(df)
    normalized_sources = normalize_source_names(source_names)
    normalized_target = normalize_curve_name(target_name)
    normalized_strategy = normalize_merge_strategy(strategy)
    diagnostics: list[str] = []
    warnings: list[str] = []

    if len(normalized_sources) < 2:
        raise ValueError("Для merge нужно выбрать минимум две исходные кривые.")

    missing = [name for name in normalized_sources if name not in columns]
    if missing:
        raise ValueError("Не найдены исходные кривые: " + ", ".join(missing) + ".")
    diagnostics.append("Исходные кривые найдены: " + ", ".join(normalized_sources) + ".")

    if not normalized_target:
        raise ValueError("Имя результирующей кривой не может быть пустым.")
    diagnostics.append(f"Имя результирующей кривой нормализовано: {normalized_target}.")

    if normalized_target in columns and (keep_sources or normalized_target not in normalized_sources):
        raise ValueError(f"Кривая {normalized_target!r} уже существует.")

    if normalized_strategy in {"mean", "sum"}:
        non_numeric = [name for name in normalized_sources if not pd.api.types.is_numeric_dtype(df[name])]
        if non_numeric:
            raise ValueError(
                "Для стратегии "
                + normalized_strategy
                + " все исходные кривые должны быть числовыми. Нечисловые: "
                + ", ".join(non_numeric)
                + "."
            )

    if not keep_sources:
        warnings.append("Исходные кривые будут удалены после создания результирующей кривой.")
    diagnostics.append(f"Стратегия merge: {normalized_strategy}.")
    return normalized_sources, normalized_target, normalized_strategy, tuple(diagnostics), tuple(warnings)


def _build_merged_series(df: pd.DataFrame, source_names: tuple[str, ...], strategy: str) -> pd.Series:
    values = df.loc[:, list(source_names)]
    if strategy == "coalesce_first":
        return values.bfill(axis=1).iloc[:, 0]
    if strategy == "coalesce_last":
        return values.ffill(axis=1).iloc[:, -1]
    if strategy == "mean":
        return values.mean(axis=1, skipna=True)
    if strategy == "sum":
        return values.sum(axis=1, skipna=True)
    raise ValueError(f"Стратегия merge {strategy!r} не поддерживается.")


def _update_merge_references(
    references: dict[str, Any],
    source_names: tuple[str, ...],
    target_name: str,
    *,
    strategy: str,
    keep_sources: bool,
) -> dict[str, Any]:
    updated = dict(references or {})
    if not keep_sources:
        for container_name in ("tablet_tracks", "templates", "presets", "saved_calculations"):
            if container_name in updated:
                container_value = updated[container_name]
                for name in source_names:
                    container_value = update_curve_references(container_value, name, target_name)
                updated[container_name] = container_value

    manifest = updated.get("manifest")
    if isinstance(manifest, dict):
        manifest = dict(manifest)
        manifest[target_name] = {
            "source": "curve_merge",
            "source_curves": list(source_names),
            "strategy": strategy,
            "keep_sources": keep_sources,
        }
        if not keep_sources:
            for name in source_names:
                manifest.pop(name, None)
        updated["manifest"] = manifest

    exports = updated.get("exports")
    if isinstance(exports, dict):
        exports = dict(exports)
        columns = list(exports.get("columns", [])) if isinstance(exports.get("columns"), list) else []
        if not keep_sources:
            columns = [column for column in columns if column not in source_names]
        if target_name not in columns:
            columns.append(target_name)
        exports["columns"] = columns
        updated["exports"] = exports

    return updated


def merge_curves(
    df: pd.DataFrame,
    source_names: Iterable[object],
    target_name: object,
    *,
    strategy: object = "coalesce_first",
    keep_sources: bool = True,
    history: tuple[CurveMergeHistoryEntry, ...] | list[CurveMergeHistoryEntry] = (),
    references: dict[str, Any] | None = None,
    reason: str = "manual",
    source: str = "las_editor",
    timestamp: str | None = None,
) -> CurveMergeResult:
    """Merge several LAS curves into one derived curve with audit metadata."""

    normalized_sources, normalized_target, normalized_strategy, diagnostics, warnings = validate_curve_merge(
        df,
        source_names,
        target_name,
        strategy,
        keep_sources=keep_sources,
    )

    merged_df = df.copy()
    merged_df[normalized_target] = _build_merged_series(merged_df, normalized_sources, normalized_strategy)
    if not keep_sources:
        drop_names = [name for name in normalized_sources if name != normalized_target]
        merged_df = merged_df.drop(columns=drop_names)

    entry = CurveMergeHistoryEntry(
        source_names=normalized_sources,
        target_name=normalized_target,
        strategy=normalized_strategy,
        timestamp=timestamp or _timestamp_utc(),
        reason=reason or "manual",
        source=source or "las_editor",
        keep_sources=keep_sources,
    )
    updated_references = _update_merge_references(
        dict(references or {}),
        normalized_sources,
        normalized_target,
        strategy=normalized_strategy,
        keep_sources=keep_sources,
    )
    return CurveMergeResult(
        data=merged_df,
        history=tuple(history) + (entry,),
        references=updated_references,
        diagnostics=diagnostics
        + (
            "Создана результирующая кривая: "
            + f"{normalized_target} из {', '.join(normalized_sources)}.",
            "Manifest/export references обновлены для результирующей кривой.",
        ),
        warnings=warnings,
        merged=True,
        source_names=normalized_sources,
        target_name=normalized_target,
        strategy=normalized_strategy,
    )


def undo_last_merge(
    df: pd.DataFrame,
    *,
    history: tuple[CurveMergeHistoryEntry, ...] | list[CurveMergeHistoryEntry],
    references: dict[str, Any] | None = None,
) -> CurveMergeResult:
    """Undo the latest merge by removing the last generated target curve."""

    current_history = tuple(history)
    if not current_history:
        raise ValueError("История merge пуста: отменять нечего.")

    last = current_history[-1]
    columns = _column_names(df)
    if last.target_name not in columns:
        raise ValueError(f"Результирующая кривая {last.target_name!r} не найдена.")

    restored_df = df.copy().drop(columns=[last.target_name])
    updated_references = dict(references or {})
    manifest = updated_references.get("manifest")
    if isinstance(manifest, dict):
        manifest = dict(manifest)
        manifest.pop(last.target_name, None)
        updated_references["manifest"] = manifest
    exports = updated_references.get("exports")
    if isinstance(exports, dict):
        exports = dict(exports)
        if isinstance(exports.get("columns"), list):
            exports["columns"] = [column for column in exports["columns"] if column != last.target_name]
        updated_references["exports"] = exports

    return CurveMergeResult(
        data=restored_df,
        history=current_history[:-1],
        references=updated_references,
        diagnostics=(f"Отменен последний merge: удалена кривая {last.target_name}.",),
        merged=True,
        source_names=last.source_names,
        target_name=last.target_name,
        strategy=last.strategy,
    )
