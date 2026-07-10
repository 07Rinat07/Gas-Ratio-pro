# LAS Recent Session Group Collapse v146

Добавлено renderer-neutral состояние раскрытия и сворачивания групп recent LAS sessions.

## Возможности

- сохранение collapsed state по паре `group_by + group_key`;
- восстановление состояния между запусками;
- методы `set_group_collapsed()` и `toggle_group_collapsed()`;
- поля `collapsed` и `expanded` в сериализованном контракте группы;
- совместное хранение с pinned sessions без потери существующих настроек.
