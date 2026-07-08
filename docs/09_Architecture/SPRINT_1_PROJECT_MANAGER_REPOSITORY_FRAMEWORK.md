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
