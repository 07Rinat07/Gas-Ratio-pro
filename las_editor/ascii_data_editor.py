from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import math
import pandas as pd

from las_editor.las_creator import DEFAULT_NULL_VALUE, normalize_las_mnemonic

ASCII_EDITOR_STORAGE_KEY = "las_ascii_editor"
DEFAULT_DEPTH_MNEMONICS: tuple[str, ...] = ("DEPT", "DEPTH", "MD", "TVD")


@dataclass(frozen=True)
class AsciiEditorHistoryEntry:
    """One safe edit operation in the LAS ~ASCII table."""

    action: str
    timestamp: str
    details: dict[str, Any]
    reason: str = "manual"
    source: str = "las_editor.ascii_data_editor"


@dataclass(frozen=True)
class AsciiEditorIssue:
    severity: str
    code: str
    message: str
    row: int | None = None
    column: str = ""


@dataclass(frozen=True)
class AsciiEditorResult:
    data: pd.DataFrame
    history: tuple[AsciiEditorHistoryEntry, ...]
    issues: tuple[AsciiEditorIssue, ...] = ()
    diagnostics: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _copy_attrs(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    target.attrs.update(source.attrs)
    return target


def _history(
    history: Sequence[AsciiEditorHistoryEntry],
    *,
    action: str,
    details: Mapping[str, Any],
    reason: str = "manual",
    source: str = "las_editor.ascii_data_editor",
    timestamp: str | None = None,
) -> tuple[AsciiEditorHistoryEntry, ...]:
    return tuple(history) + (
        AsciiEditorHistoryEntry(
            action=action,
            timestamp=timestamp or _timestamp_utc(),
            details=dict(details),
            reason=reason or "manual",
            source=source or "las_editor.ascii_data_editor",
        ),
    )


def normalize_ascii_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a working copy with LAS-safe curve names.

    The function is intentionally conservative: it does not mutate values and
    preserves DataFrame attrs. Duplicate normalized names receive a numeric
    suffix so table operations remain deterministic.
    """

    result = df.copy()
    used: dict[str, int] = {}
    columns: list[str] = []
    for column in result.columns:
        base = normalize_las_mnemonic(str(column), fallback="CURVE")
        count = used.get(base, 0)
        used[base] = count + 1
        columns.append(base if count == 0 else f"{base}_{count + 1}")
    result.columns = columns
    return _copy_attrs(df, result)


def find_depth_column(df: pd.DataFrame, *, candidates: Iterable[str] = DEFAULT_DEPTH_MNEMONICS) -> str:
    normalized = {normalize_las_mnemonic(column): str(column) for column in df.columns}
    for candidate in candidates:
        key = normalize_las_mnemonic(candidate)
        if key in normalized:
            return normalized[key]
    raise ValueError("Depth column was not found. Expected DEPT, DEPTH, MD or TVD.")


def build_ascii_table(df: pd.DataFrame, *, max_rows: int | None = None) -> tuple[dict[str, Any], ...]:
    """Convert ASCII values to UI-ready row dictionaries."""

    source = df.head(max_rows) if max_rows is not None else df
    rows: list[dict[str, Any]] = []
    for index, row in source.iterrows():
        item = {"row": int(index) if isinstance(index, int) else str(index)}
        for column in source.columns:
            value = row[column]
            item[str(column)] = None if pd.isna(value) else value
        rows.append(item)
    return tuple(rows)


def edit_ascii_cell(
    df: pd.DataFrame,
    *,
    row_index: int,
    column: str,
    value: Any,
    history: Sequence[AsciiEditorHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.ascii_data_editor",
) -> AsciiEditorResult:
    result = df.copy()
    if column not in result.columns:
        raise ValueError(f"Column {column!r} was not found.")
    if row_index < 0 or row_index >= len(result):
        raise IndexError(f"Row index out of range: {row_index}.")
    old_value = result.iloc[row_index][column]
    result.iat[row_index, result.columns.get_loc(column)] = value
    result = _copy_attrs(df, result)
    return AsciiEditorResult(
        data=result,
        history=_history(history, action="edit_cell", details={"row_index": row_index, "column": column, "old_value": old_value, "new_value": value}, reason=reason, source=source),
        diagnostics=("Ячейка ASCII-таблицы изменена в рабочей копии.", "Исходный LAS-файл не перезаписывается."),
    )


def edit_ascii_range(
    df: pd.DataFrame,
    *,
    row_start: int,
    row_stop: int,
    columns: Iterable[str],
    value: Any,
    history: Sequence[AsciiEditorHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.ascii_data_editor",
) -> AsciiEditorResult:
    result = df.copy()
    selected_columns = tuple(str(column) for column in columns)
    missing = [column for column in selected_columns if column not in result.columns]
    if missing:
        raise ValueError(f"Columns were not found: {missing!r}")
    start = max(0, int(row_start))
    stop = min(len(result) - 1, int(row_stop))
    if stop < start:
        raise ValueError("Invalid row range.")
    result.loc[result.index[start: stop + 1], list(selected_columns)] = value
    result = _copy_attrs(df, result)
    return AsciiEditorResult(
        data=result,
        history=_history(history, action="edit_range", details={"row_start": start, "row_stop": stop, "columns": selected_columns, "new_value": value}, reason=reason, source=source),
        diagnostics=("Диапазон ASCII-таблицы изменен в рабочей копии.",),
    )


def insert_ascii_rows(
    df: pd.DataFrame,
    rows: Iterable[Mapping[str, Any]],
    *,
    position: int | None = None,
    history: Sequence[AsciiEditorHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.ascii_data_editor",
) -> AsciiEditorResult:
    incoming = pd.DataFrame(list(rows), columns=list(df.columns))
    if incoming.empty:
        return AsciiEditorResult(data=df.copy(), history=tuple(history), diagnostics=("Нет строк для вставки.",))
    for column in df.columns:
        if column not in incoming.columns:
            incoming[column] = math.nan
    incoming = incoming[list(df.columns)]
    pos = len(df) if position is None else max(0, min(int(position), len(df)))
    result = pd.concat([df.iloc[:pos], incoming, df.iloc[pos:]], ignore_index=True)
    result = _copy_attrs(df, result)
    return AsciiEditorResult(
        data=result,
        history=_history(history, action="insert_rows", details={"position": pos, "row_count": int(len(incoming))}, reason=reason, source=source),
        diagnostics=(f"Вставлено строк: {len(incoming)}.",),
    )


def delete_ascii_rows(
    df: pd.DataFrame,
    row_indices: Iterable[int],
    *,
    history: Sequence[AsciiEditorHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.ascii_data_editor",
) -> AsciiEditorResult:
    indices = sorted({int(index) for index in row_indices if 0 <= int(index) < len(df)})
    result = df.drop(df.index[indices]).reset_index(drop=True)
    result = _copy_attrs(df, result)
    return AsciiEditorResult(
        data=result,
        history=_history(history, action="delete_rows", details={"row_indices": indices, "row_count": len(indices)}, reason=reason, source=source),
        diagnostics=(f"Удалено строк: {len(indices)}.",),
    )


def sort_ascii_by_depth(
    df: pd.DataFrame,
    *,
    depth_column: str | None = None,
    ascending: bool = True,
    history: Sequence[AsciiEditorHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.ascii_data_editor",
) -> AsciiEditorResult:
    column = depth_column or find_depth_column(df)
    result = df.copy()
    result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.sort_values(column, ascending=ascending, kind="mergesort").reset_index(drop=True)
    result = _copy_attrs(df, result)
    return AsciiEditorResult(
        data=result,
        history=_history(history, action="sort_by_depth", details={"depth_column": column, "ascending": ascending}, reason=reason, source=source),
        diagnostics=("ASCII-таблица отсортирована по глубине.",),
    )


def find_replace_ascii_values(
    df: pd.DataFrame,
    *,
    find_value: Any,
    replace_value: Any,
    columns: Iterable[str] | None = None,
    history: Sequence[AsciiEditorHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.ascii_data_editor",
) -> AsciiEditorResult:
    result = df.copy()
    selected_columns = tuple(columns or result.columns)
    missing = [column for column in selected_columns if column not in result.columns]
    if missing:
        raise ValueError(f"Columns were not found: {missing!r}")
    replacements = 0
    for column in selected_columns:
        mask = result[column] == find_value
        replacements += int(mask.sum())
        result.loc[mask, column] = replace_value
    result = _copy_attrs(df, result)
    return AsciiEditorResult(
        data=result,
        history=_history(history, action="find_replace", details={"find_value": find_value, "replace_value": replace_value, "columns": selected_columns, "replacement_count": replacements}, reason=reason, source=source),
        diagnostics=(f"Выполнено замен: {replacements}.",),
    )


def validate_ascii_data(
    df: pd.DataFrame,
    *,
    depth_column: str | None = None,
    expected_step: float | None = None,
    null_value: float = DEFAULT_NULL_VALUE,
) -> tuple[AsciiEditorIssue, ...]:
    issues: list[AsciiEditorIssue] = []
    if df.empty:
        issues.append(AsciiEditorIssue("error", "ASCII_EMPTY", "Секция ~ASCII не содержит строк."))
        return tuple(issues)
    try:
        column = depth_column or find_depth_column(df)
    except ValueError as exc:
        return (AsciiEditorIssue("error", "DEPTH_COLUMN_MISSING", str(exc)),)
    depths = pd.to_numeric(df[column], errors="coerce")
    for idx in depths[depths.isna()].index:
        issues.append(AsciiEditorIssue("error", "DEPTH_NOT_NUMERIC", "Глубина должна быть числовой.", row=int(idx), column=column))
    duplicated = depths[depths.duplicated(keep=False) & depths.notna()]
    for idx, value in duplicated.items():
        issues.append(AsciiEditorIssue("error", "DUPLICATE_DEPTH", f"Дублирующаяся глубина: {value}.", row=int(idx), column=column))
    clean = depths.dropna().reset_index(drop=True)
    if len(clean) > 1:
        diffs = clean.diff().dropna()
        if (diffs <= 0).any():
            issues.append(AsciiEditorIssue("warning", "DEPTH_NOT_INCREASING", "Глубина не является строго возрастающей.", column=column))
        if expected_step is not None and float(expected_step) != 0:
            tolerance = abs(float(expected_step)) * 1e-6 + 1e-9
            bad_steps = diffs[(diffs - float(expected_step)).abs() > tolerance]
            for idx, value in bad_steps.items():
                issues.append(AsciiEditorIssue("warning", "DEPTH_STEP_MISMATCH", f"Нарушение шага глубины: {value:g} вместо {float(expected_step):g}.", row=int(idx), column=column))
    null_hits = int((df == null_value).sum(numeric_only=False).sum())
    if null_hits:
        issues.append(AsciiEditorIssue("info", "NULL_VALUES_FOUND", f"Найдено NULL-значений LAS: {null_hits}."))
    return tuple(issues)


def ascii_editor_summary(df: pd.DataFrame, *, depth_column: str | None = None) -> dict[str, Any]:
    column = None
    try:
        column = depth_column or find_depth_column(df)
    except ValueError:
        pass
    summary: dict[str, Any] = {
        "row_count": int(len(df)),
        "curve_count": int(len(df.columns)),
        "columns": tuple(str(column) for column in df.columns),
        "depth_column": column or "",
    }
    if column:
        depths = pd.to_numeric(df[column], errors="coerce").dropna()
        if not depths.empty:
            summary.update({"start_depth": float(depths.min()), "stop_depth": float(depths.max())})
            if len(depths) > 1:
                summary["median_step"] = float(depths.diff().dropna().median())
    return summary


def render_ascii_section(df: pd.DataFrame, *, null_value: float = DEFAULT_NULL_VALUE, precision: int = 6) -> str:
    """Render only LAS ASCII body lines, ready to append after ``~ASCII``."""

    def fmt(value: Any) -> str:
        if value is None or pd.isna(value):
            return f"{null_value:.10g}"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f"{float(value):.{precision}g}"
        text = str(value).strip()
        return text if text else f"{null_value:.10g}"

    return "\n".join(" ".join(fmt(value) for value in row) for row in df.itertuples(index=False, name=None))


def preview_ascii_changes(before: pd.DataFrame, after: pd.DataFrame, *, max_changes: int = 50) -> tuple[dict[str, Any], ...]:
    """Return compact row/column diff records for UI preview."""

    changes: list[dict[str, Any]] = []
    common_rows = min(len(before), len(after))
    common_columns = [column for column in before.columns if column in after.columns]
    for row_index in range(common_rows):
        for column in common_columns:
            old = before.iloc[row_index][column]
            new = after.iloc[row_index][column]
            if (pd.isna(old) and pd.isna(new)) or old == new:
                continue
            changes.append({"row": row_index, "column": column, "old_value": None if pd.isna(old) else old, "new_value": None if pd.isna(new) else new})
            if len(changes) >= max_changes:
                return tuple(changes)
    if len(before) != len(after):
        changes.append({"row": "*", "column": "*", "old_value": len(before), "new_value": len(after), "change": "row_count"})
    return tuple(changes[:max_changes])
