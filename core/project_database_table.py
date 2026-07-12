"""Reusable table view model for Project Database workspaces.

The module is deliberately UI-framework agnostic.  It normalizes filtering,
sorting, pagination and technical-column visibility before Streamlit renders a
DataFrame.  Keeping this logic outside the page renderer makes behaviour
predictable and easy to regression-test.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Iterable, Sequence

import pandas as pd


@dataclass(frozen=True, slots=True)
class ProjectDatabaseTableView:
    dataframe: pd.DataFrame
    total_rows: int
    filtered_rows: int
    page: int
    page_count: int
    page_size: int


DEFAULT_TECHNICAL_COLUMNS = (
    "UUID",
    "SHA-256",
    "Ключ",
    "Object ID",
    "Скважина ID",
    "Путь",
    "Относительный путь",
)


def compact_path(value: object, *, max_length: int = 72) -> str:
    """Return a readable compact path while preserving both ends."""

    text = str(value or "")
    if len(text) <= max_length:
        return text
    left = max(16, (max_length - 3) // 2)
    right = max(16, max_length - 3 - left)
    return f"{text[:left]}...{text[-right:]}"


def _contains_search(row: pd.Series, search: str) -> bool:
    if not search:
        return True
    needle = search.casefold().strip()
    return any(needle in str(value).casefold() for value in row.values)


def build_project_database_table_view(
    dataframe: pd.DataFrame,
    *,
    search: str = "",
    type_column: str | None = "Тип",
    selected_types: Sequence[str] | None = None,
    status_column: str | None = "Статус",
    selected_statuses: Sequence[str] | None = None,
    sort_column: str | None = None,
    ascending: bool = True,
    page: int = 1,
    page_size: int = 25,
    show_technical: bool = False,
    technical_columns: Iterable[str] = DEFAULT_TECHNICAL_COLUMNS,
    compact_path_columns: Iterable[str] = ("Путь", "Относительный путь", "Файлы"),
) -> ProjectDatabaseTableView:
    """Build a filtered and paginated Project Database table view."""

    frame = dataframe.copy()
    total_rows = len(frame)

    if search.strip() and not frame.empty:
        mask = frame.apply(lambda row: _contains_search(row, search), axis=1)
        frame = frame.loc[mask]

    if type_column and type_column in frame.columns and selected_types:
        frame = frame[frame[type_column].astype(str).isin(tuple(selected_types))]

    if status_column and status_column in frame.columns and selected_statuses:
        frame = frame[frame[status_column].astype(str).isin(tuple(selected_statuses))]

    if sort_column and sort_column in frame.columns and not frame.empty:
        frame = frame.sort_values(
            by=sort_column,
            ascending=ascending,
            kind="stable",
            na_position="last",
        )

    filtered_rows = len(frame)
    normalized_page_size = max(1, int(page_size))
    page_count = max(1, ceil(filtered_rows / normalized_page_size))
    normalized_page = min(max(1, int(page)), page_count)
    start = (normalized_page - 1) * normalized_page_size
    end = start + normalized_page_size
    frame = frame.iloc[start:end].copy()

    for column in compact_path_columns:
        if column in frame.columns:
            frame[column] = frame[column].map(compact_path)

    if not show_technical:
        hidden = {column for column in technical_columns if column in frame.columns}
        frame = frame.drop(columns=list(hidden), errors="ignore")

    return ProjectDatabaseTableView(
        dataframe=frame.reset_index(drop=True),
        total_rows=total_rows,
        filtered_rows=filtered_rows,
        page=normalized_page,
        page_count=page_count,
        page_size=normalized_page_size,
    )
