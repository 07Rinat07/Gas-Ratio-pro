# Workspace Framework Specification v5.0

## Назначение

Workspace Framework 2.0 — единый каркас приложения GAS RATIO PRO. Он отвечает за навигацию, видимость инструментов, регистрацию рабочих пространств и корректную очистку временного состояния.

## Главные правила интерфейса

1. Все ключевые инструменты рабочего пространства должны быть видны пользователю.
2. Инструменты, которые временно недоступны, должны отображаться как disabled, а не исчезать.
3. При смене проекта, скважины, LAS или workspace все временные таблицы и статистики должны сбрасываться.
4. Пользователь не должен видеть таблицы, графики или статистику от предыдущего файла.
5. Оригинальные LAS-файлы не изменяются.
6. Все опасные операции выполняются только над копиями.

## Application Shell

Application Shell содержит:

- Header;
- Ribbon;
- Project Explorer;
- Workspace Area;
- Inspector Panel;
- Status Bar.

## Workspace API

Каждое рабочее пространство должно иметь единые операции:

```python
open()
close()
save()
refresh()
activate()
deactivate()
clear_transient_state()
```

## Session State Reset

Очистка выполняется через `core.session_state_manager`.

События очистки:

- `project_changed`;
- `well_changed`;
- `las_changed`;
- `workspace_changed`.

Очищаются:

- таблицы;
- статистики;
- dashboard metrics;
- расчетные таблицы;
- validation/diagnostics tables;
- previews;
- annotations текущей сессии;
- temporary exports;
- локальные workspace-данные.

Сохраняются:

- тема;
- язык;
- лицензия;
- EULA;
- пользовательские настройки;
- глобальные настройки workspace.

## LAS Workspace Visibility

В LAS Workspace постоянно видны:

- Create LAS;
- Open LAS;
- Import CSV;
- Import Excel;
- Header;
- Curves;
- ASCII;
- Validator;
- Diagnostics;
- Cleanup;
- Merge;
- Append;
- Depth Repair;
- Curve Calculator;
- Processing Pipeline;
- Export;
- Reports;
- Operation Journal.

Если LAS не загружен, инструменты отображаются в disabled-состоянии.

## Home Workspace

Home Workspace содержит:

- последние проекты;
- последние LAS;
- быстрые действия;
- карточки состояния проекта;
- доступ к созданию нового LAS;
- доступ к открытию LAS;
- доступ к импорту CSV/Excel.

## Критерии приемки

- при смене LAS исчезают старые таблицы валидации;
- при смене проекта исчезают старые project session sheets;
- при смене workspace исчезают локальные preview-таблицы;
- тема и пользовательские настройки сохраняются;
- все LAS-инструменты видны в интерфейсе;
- тесты покрывают очистку таблиц и статистик.
