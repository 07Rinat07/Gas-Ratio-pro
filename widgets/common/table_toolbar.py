from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableToolbarAction:
    key: str
    label: str
    destructive: bool = False


DEFAULT_TABLE_TOOLBAR_ACTIONS: tuple[TableToolbarAction, ...] = (
    TableToolbarAction("refresh", "Обновить"),
    TableToolbarAction("delete_selected", "Удалить выбранное", destructive=True),
    TableToolbarAction("clear_all", "Очистить список", destructive=True),
)


def table_toolbar_labels(actions: tuple[TableToolbarAction, ...] = DEFAULT_TABLE_TOOLBAR_ACTIONS) -> tuple[str, ...]:
    return tuple(action.label for action in actions)
