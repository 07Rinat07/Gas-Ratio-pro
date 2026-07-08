# Sprint 1 — Project Manager & Repository Framework

## Цель

Стабилизировать управление проектами и убрать прямую работу UI с низкоуровневыми операциями удаления/очистки.

## Выполнено

### 1. Service Layer для Project Manager

Добавлен модуль:

```text
services/project_manager_service.py
```

Сервис стал промежуточным уровнем между Streamlit UI и репозиториями:

```text
UI
  ↓
ProjectManagerService
  ↓
projects.repository / projects.recent_projects / projects.exports
  ↓
data/projects
```

### 2. Централизованные операции проекта

`ProjectManagerService` теперь отвечает за:

- создание проекта;
- добавление проекта в историю последних проектов;
- очистку истории последних проектов;
- удаление записи из истории без удаления проекта;
- удаление проекта с диска;
- очистку экспортов проекта перед удалением;
- защиту основного проекта от удаления.

### 3. Интеграция в реальный UI

Обновлен существующий файл:

```text
app/streamlit_app.py
```

Точки интеграции:

- `_load_project_records_for_ui()`;
- `_render_project_selector()`;
- `_render_recent_projects_manager()`.

Эти функции теперь используют `ProjectManagerService`, а не вызывают низкоуровневое удаление напрямую.

### 4. Тесты

Добавлены тесты:

```text
tests/test_project_manager_service.py
```

Проверяют:

- создание проекта через сервис;
- добавление проекта в историю;
- удаление записи из истории без удаления проекта;
- полное удаление проекта вместе с экспортами;
- запрет удаления основного проекта.

## Проверка

```text
9 passed
```

Команда:

```bash
pytest -q tests/test_project_manager_service.py tests/test_recent_projects_manager.py tests/test_project_exports_delete.py
```

## Архитектурное решение

Начиная с этого этапа UI не должен напрямую выполнять операции удаления проекта, истории и экспортов. Все такие операции должны проходить через сервисный слой.

## Следующий шаг

Продолжить вынос операций из `streamlit_app.py` в сервисы:

1. `WellManagerService`;
2. `LasManagerService`;
3. `ExportManagerService`;
4. единый `WorkspaceDataService` для таблиц и архивов.

---

## Продолжение Sprint 1 — Export Manager Service Layer

### 5. Service Layer для экспортов проекта

Добавлен модуль:

```text
services/export_manager_service.py
```

Сервис стал единым уровнем для операций с сохраненными экспортами проекта:

```text
UI
  ↓
ExportManagerService
  ↓
projects.exports
  ↓
data/projects/<project_id>/exports
```

### 6. Централизованные операции экспортов

`ExportManagerService` отвечает за:

- получение списка экспортов проекта;
- подсчет экспортов для Dashboard;
- сохранение экспорта;
- чтение файла экспорта для скачивания;
- удаление выбранного экспорта;
- очистку всех экспортов проекта.

### 7. Интеграция в реальный UI

Обновлен существующий файл:

```text
app/streamlit_app.py
```

Точки интеграции:

- `_dashboard_project_statistics()`;
- `_dashboard_news_items()`;
- `_dashboard_activity_items()`;
- `_render_dashboard_shell()`;
- `_render_project_exports_panel()`;
- `_save_project_export_with_feedback()`.

Панель "Сохраненные экспорты проекта" теперь вызывает `ExportManagerService`, а не работает напрямую с низкоуровневыми функциями манифеста экспортов.

### 8. Тесты экспортного сервисного слоя

Добавлены тесты:

```text
tests/test_export_manager_service.py
```

Проверяют:

- сохранение экспорта через сервис;
- чтение файла экспорта;
- удаление выбранного экспорта;
- очистку всех экспортов проекта.

## Обновленная проверка

```text
6 passed
```

Команда:

```bash
pytest -q tests/test_export_manager_service.py tests/test_project_manager_service.py
```

## Следующий шаг

Продолжить Sprint 1:

1. `WellManagerService` — управление сохраненными скважинами;
2. `LasManagerService` — управление LAS-версиями проекта;
3. `WorkspaceDataService` — единые операции очистки таблиц, архивов и временного состояния.
