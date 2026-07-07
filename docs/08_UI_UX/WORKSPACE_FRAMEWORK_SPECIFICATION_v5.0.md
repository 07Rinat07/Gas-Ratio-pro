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

## Application Refactoring v5 — State and Persistence Rules

Streamlit-виджеты и бизнес-контекст приложения разделяются.

Запрещено:

```python
st.selectbox(..., key="active_project_id")
st.session_state["active_project_id"] = new_id
```

Разрешено:

```python
st.selectbox(..., key="active_project_select_ui")
ApplicationStateController(st.session_state).activate_project(new_id)
```

### Правило создания проекта

После создания проекта приложение не меняет widget-owned state напрямую. Вместо этого записывается pending-переключение:

```python
ApplicationStateController(st.session_state).request_project_activation(project.id)
st.rerun()
```

В следующем безопасном проходе pending-переключение применяется до построения project selector.

### Правило удаления

Удаление проекта или скважины обязано выполняться на двух уровнях:

1. Persistent storage:
   - `data/projects/<project_id>`;
   - `data/wells/<well_id>`;
   - `data/wells/<well_id>/versions/<version_id>`.

2. Derived session state:
   - таблицы;
   - статистики;
   - графики;
   - preview;
   - validation/diagnostics;
   - correlation/modeling/report workspace-local данные.

Очистка только `st.session_state` не считается удалением.
