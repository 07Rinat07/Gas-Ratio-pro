# LAS Recent Session Sorting v142

Добавлена renderer-neutral сортировка списка недавних LAS-сессий.

Поддерживаемые поля:

- `modified`
- `filename`
- `project`
- `las_id`

Параметры:

- `sort_order`: `asc` или `desc`
- `pinned_first`: сохранять закреплённые сессии выше остальных

Snapshot-контракт обновлён до версии `1.3` и содержит секцию `sorting`.
