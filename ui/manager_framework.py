from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import pandas as pd


@dataclass(frozen=True)
class ManagerAction:
    """One action displayed in a unified manager toolbar.

    The class is UI-framework neutral on purpose. Streamlit renderers can use
    these descriptors, while tests and non-UI services can validate the same
    action contract without importing Streamlit.
    """

    id: str
    label: str
    icon: str = ""
    danger: bool = False
    enabled: bool = True
    help: str = ""

    @property
    def caption(self) -> str:
        return f"{self.icon} {self.label}".strip()


@dataclass(frozen=True)
class ManagerToolbar:
    """Unified toolbar descriptor for all data managers."""

    manager_id: str
    title: str
    actions: tuple[ManagerAction, ...] = field(default_factory=tuple)
    description: str = ""

    def action_ids(self) -> tuple[str, ...]:
        return tuple(action.id for action in self.actions)

    def has_action(self, action_id: str) -> bool:
        return action_id in self.action_ids()


@dataclass(frozen=True)
class ManagerTableColumn:
    """Column contract used by all manager tables."""

    key: str
    label: str
    visible: bool = True
    width: str = "medium"


@dataclass(frozen=True)
class ManagerTable:
    """UI-neutral table descriptor for manager screens."""

    manager_id: str
    rows: tuple[dict[str, Any], ...]
    columns: tuple[ManagerTableColumn, ...]
    selection_key: str = "id"
    empty_message: str = "Нет данных."

    def to_dataframe(self) -> pd.DataFrame:
        visible_columns = [column for column in self.columns if column.visible]
        ordered_rows: list[dict[str, Any]] = []
        for row in self.rows:
            ordered_rows.append({column.label: row.get(column.key, "") for column in visible_columns})
        return pd.DataFrame(ordered_rows)

    def row_ids(self) -> tuple[str, ...]:
        return tuple(str(row.get(self.selection_key, "")) for row in self.rows if str(row.get(self.selection_key, "")))


DEFAULT_MANAGER_ACTIONS: tuple[ManagerAction, ...] = (
    ManagerAction("import", "Импорт", "➕"),
    ManagerAction("open", "Открыть", "📂"),
    ManagerAction("refresh", "Обновить", "🔄"),
    ManagerAction("edit", "Редактировать", "✏"),
    ManagerAction("duplicate", "Дублировать", "📋"),
    ManagerAction("delete_selected", "Удалить выбранный", "🗑", danger=True),
    ManagerAction("clear_section", "Очистить раздел", "🧹", danger=True),
    ManagerAction("clear_all", "Очистить всё", "🗑", danger=True),
    ManagerAction("export", "Экспорт", "📤"),
    ManagerAction("settings", "Настройки", "⚙"),
)


def build_manager_toolbar(
    manager_id: str,
    title: str,
    *,
    action_ids: Sequence[str] | None = None,
    description: str = "",
) -> ManagerToolbar:
    """Build a standard toolbar filtered by supported action ids."""

    allowed = set(action_ids or (action.id for action in DEFAULT_MANAGER_ACTIONS))
    actions = tuple(action for action in DEFAULT_MANAGER_ACTIONS if action.id in allowed)
    return ManagerToolbar(manager_id=manager_id, title=title, actions=actions, description=description)


def build_records_table(
    manager_id: str,
    rows: Iterable[dict[str, Any]],
    columns: Sequence[tuple[str, str] | ManagerTableColumn],
    *,
    selection_key: str = "id",
    empty_message: str = "Нет данных.",
) -> ManagerTable:
    normalized_columns: list[ManagerTableColumn] = []
    for column in columns:
        if isinstance(column, ManagerTableColumn):
            normalized_columns.append(column)
        else:
            key, label = column
            normalized_columns.append(ManagerTableColumn(key=key, label=label))
    return ManagerTable(
        manager_id=manager_id,
        rows=tuple(dict(row) for row in rows),
        columns=tuple(normalized_columns),
        selection_key=selection_key,
        empty_message=empty_message,
    )
