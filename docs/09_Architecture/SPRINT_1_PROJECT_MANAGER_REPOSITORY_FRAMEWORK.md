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

---

## Продолжение Sprint 1 — Well Manager Service Layer

### 9. Service Layer для сохраненных скважин

Добавлен модуль:

```text
services/well_manager_service.py
```

Сервис стал единым уровнем для операций с локально сохраненными скважинами:

```text
UI
  ↓
WellManagerService
  ↓
wells.repository
  ↓
data/wells
```

### 10. Централизованные операции скважин

`WellManagerService` отвечает за:

- получение списка сохраненных скважин;
- подсчет скважин для Dashboard;
- сохранение новой версии скважины;
- чтение CSV/XLSX/LAS файлов версии;
- удаление выбранной версии;
- автоматическое удаление скважины, если удалена последняя версия;
- полное удаление скважины с диска.

### 11. Интеграция в реальный UI

Обновлен существующий файл:

```text
app/streamlit_app.py
```

Точки интеграции:

- `_render_saved_wells_panel()`;
- `_dashboard_project_statistics()`;
- блок сохранения подготовленной версии в LAS Editor.

Панель "Сохраненные скважины" теперь вызывает `WellManagerService`, а не работает напрямую с функциями `wells.repository`.

### 12. Тесты сервисного слоя скважин

Добавлены тесты:

```text
tests/test_well_manager_service.py
```

Проверяют:

- сохранение версии скважины через сервис;
- чтение файлов версии;
- удаление выбранной версии без восстановления после перезапуска;
- удаление скважины после удаления последней версии;
- полное физическое удаление папки скважины.

## Обновленная проверка

```text
10 passed
```

Команда:

```bash
pytest -q tests/test_well_manager_service.py tests/test_export_manager_service.py tests/test_project_manager_service.py
```

## Следующий шаг

Продолжить Sprint 1:

1. `LasManagerService` — управление LAS-файлами активного проекта;
2. `WorkspaceDataService` — единые операции очистки таблиц, архивов и временного состояния;
3. дальнейшее уменьшение прямых вызовов репозиториев из `streamlit_app.py`.

---

## Продолжение Sprint 1 — LAS Manager Service Layer

### 13. Service Layer для LAS-файлов активного проекта

Добавлен модуль:

```text
services/las_manager_service.py
```

Сервис стал единым уровнем для операций с LAS-версиями проекта:

```text
UI
  ↓
LasManagerService
  ↓
projects.las_files
  ↓
data/projects/<project_id>/wells
```

### 14. Централизованные операции LAS

`LasManagerService` отвечает за:

- получение списка LAS-файлов проекта;
- получение карточек скважин и версий LAS;
- подсчет LAS-файлов для Dashboard;
- сохранение загруженного LAS в активный проект;
- сохранение подготовленного LAS из LAS Editor;
- архивирование LAS-версии;
- восстановление LAS-версии из архива;
- физическое удаление LAS-версии с диска;
- чтение LAS как bytes;
- чтение LAS как DataFrame;
- экспорт выбранных LAS-версий в ZIP.

### 15. Интеграция в реальный UI

Обновлен существующий файл:

```text
app/streamlit_app.py
```

Точки интеграции:

- `_dashboard_project_statistics()`;
- `_dashboard_news_items()`;
- `_render_project_las_zip_download()`;
- `_render_project_workspace_loader()`;
- `_project_las_records_to_raw_sheets()`;
- `_render_project_las_files_panel()`;
- блок сохранения подготовленного LAS в LAS Editor.

Панель `LAS-файлы проекта` теперь вызывает `LasManagerService`, а не работает напрямую с функциями `projects.las_files`.

### 16. Тесты сервисного слоя LAS

Добавлены тесты:

```text
tests/test_las_manager_service.py
```

Проверяют:

- сохранение LAS в проект через сервис;
- чтение LAS как bytes;
- чтение LAS как DataFrame;
- архивирование;
- восстановление;
- ZIP-экспорт;
- физическое удаление LAS-папки;
- корректный результат при удалении отсутствующей LAS-версии.

## Обновленная проверка

```text
12 passed
```

Команда:

```bash
pytest -q tests/test_las_manager_service.py tests/test_well_manager_service.py tests/test_export_manager_service.py tests/test_project_manager_service.py
```

## Следующий шаг

Продолжить Sprint 1:

1. `WorkspaceDataService` — единые операции очистки таблиц, архивов и временного состояния;
2. дальнейшее уменьшение прямых вызовов репозиториев из `streamlit_app.py`;
3. подготовка к выносу UI Project Manager из `streamlit_app.py` в отдельный workspace-модуль.
