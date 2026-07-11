# Visualization Interactive Layer — Viewport Commands and Controller (v95)

## Назначение

Версия v95 добавляет renderer-neutral слой команд управления viewport и
детерминированный контроллер состояния. UI-адаптеры не вычисляют глубинные
диапазоны: они формируют `ViewportCommand`, передают его контроллеру и получают
новое состояние `InteractiveViewport`.

## Архитектурное положение

```text
Mouse / Touch / Keyboard Adapter
              ↓
       ViewportCommand
              ↓
      ViewportController
              ↓
      InteractiveViewport
              ↓
   Scene / Render Model rebuild
```

Модуль не зависит от Streamlit, SVG, PDF, matplotlib или браузерного Canvas.

## Команды

Поддерживаются операции:

- `pan_domain` — смещение в единицах глубины;
- `pan_pixels` — смещение по экранному drag-жесту;
- `zoom` — масштабирование относительно центра или глубинного anchor;
- `zoom_at_screen` — масштабирование относительно курсора;
- `fit` — вписать заданный диапазон;
- `set_range` — явно установить видимый диапазон;
- `reset` — восстановить исходный viewport.

Каждая команда сериализуется в JSON-совместимый контракт
`visualization.interactive.viewport-command` версии `1.0`.

## Контроллер

`ViewportController` хранит:

- исходный viewport;
- текущий viewport;
- ограниченную undo-историю;
- redo-ветку;
- диагностические глубины истории.

Новая команда после `undo()` очищает redo-ветку. Команды, не изменившие
состояние из-за ограничений viewport, не загрязняют историю.

## Практическая ценность

Контракт готов для последующего подключения:

- Event Bus;
- Workspace Session;
- клавиатурных команд;
- мыши и touch-жестов;
- синхронизации нескольких LAS-треков;
- Undo/Redo в Workbench;
- журналирования действий пользователя.

## Следующий этап

v96: renderer-neutral hit testing — пространственный индекс примитивов,
поиск ближайшей кривой/точки и нормализованный результат попадания.
