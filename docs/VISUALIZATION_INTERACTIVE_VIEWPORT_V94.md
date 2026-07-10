# Visualization Interactive Viewport v94

## Назначение

Первый инкремент Interactive Layer вводит независимый от UI и renderer контракт viewport. Модуль отвечает только за математическое преобразование координат и навигацию по глубине.

## Реализовано

- обратимые преобразования `domain ↔ screen`;
- поддержка обычной и инвертированной вертикальной оси;
- ограничение преобразований видимым диапазоном;
- pan в координатах глубины;
- pan в экранных пикселях;
- zoom относительно центра, значения глубины или позиции курсора;
- минимальный и максимальный масштаб;
- ограничение навигации полным диапазоном LAS;
- immutable API: каждая операция возвращает новый viewport;
- сериализуемый renderer-neutral контракт.

## Архитектурное положение

```text
LAS / Domain Model
        ↓
Visualization Scene / Layout
        ↓
InteractiveViewport
        ↓
Viewport Controller / Hit Testing / Cursor / Selection
        ↓
UI adapters and renderers
```

`InteractiveViewport` не импортирует Streamlit, SVG, PDF, matplotlib или browser API. UI передаёт только команды пользователя и получает новый рассчитанный viewport.

## Следующий этап

- viewport controller и нормализованные interaction commands;
- hit-testing index для render primitives;
- cursor state и selection contract;
- интеграция с LAS Viewer без изменения экспортных renderer.
