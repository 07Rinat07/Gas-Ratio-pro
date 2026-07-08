# Storage Lifecycle Framework

## Статус

Sprint 1 — обязательный блок перед Sprint 1.5 Integration & Stabilization.

## Цель

Сделать платформу надежной при работе с файлами проекта: Dataset, LAS, Export, Report, Cache и временные файлы должны удаляться только после освобождения ресурсов и через единый механизм.

## Реализованный первый блок

### ResourceManager

`core/storage_lifecycle.py`

Отвечает за регистрацию и освобождение ресурсов:

- файлов;
- DataFrame;
- preview-объектов;
- временных объектов;
- будущих Plotly/Matplotlib ресурсов.

Ключевые методы:

- `register_file(...)`
- `register_dataframe(...)`
- `release_path(...)`
- `release_owner(...)`
- `release_all()`
- `diagnostics()`

### DeleteEngine

`core/storage_lifecycle.py`

Единая точка физического удаления файлов и каталогов.

Алгоритм:

1. освободить ресурсы через `ResourceManager.release_path(...)`;
2. вызвать `gc.collect()`;
3. выполнить `unlink()` или `rmtree()`;
4. при `PermissionError`/`OSError` повторить попытку;
5. при неудаче вернуть диагностическую ошибку `StorageDeleteError`.

### DatasetManagerService

`services/dataset_manager_service.py`

Dataset Manager больше не должен удалять папки напрямую. Очистка разделов и удаление Dataset проходят через:

```text
DatasetManagerService
    ↓
DeleteEngine
    ↓
ResourceManager
    ↓
Filesystem
    ↓
Manifest update
```

Поддержанные разделы:

- CSV;
- Excel;
- Core;
- Mud Log;
- Production.

LAS очищается через `LasManagerService` и будет подключен к общему DeleteEngine отдельным проходом.

## Архитектурное правило

Запрещено выполнять прямое удаление файлов из UI:

```python
shutil.rmtree(...)
Path.unlink()
os.remove(...)
```

Все разрушительные операции должны проходить через Storage Lifecycle Framework.

## Следующий блок

- IndexManager: автоматическая синхронизация Project Storage Index после удаления/импорта/переименования.
- CacheManager: единая очистка preview/cache/table/plot объектов.
- Integration with LAS/Export/Report managers.

## Реализованный блок IndexManager

### IndexManager

`core/storage_lifecycle.py`

Project Database больше не рассматривается как отдельный экран. Это часть Storage Lifecycle Framework, которая должна автоматически синхронизироваться после операций с файловой системой.

Ключевые методы:

- `rebuild_project_index(project_id)` — полностью перестраивает индекс по фактическим файлам проекта;
- `validate_project_index(project_id)` — проверяет сохраненный индекс на отсутствующие/измененные файлы;
- `sync_after_delete(project_id)` — используется после удаления Dataset/LAS/Export/Report.

### Интеграция с DatasetManagerService

После операций:

- `delete_dataset(...)`;
- `delete_selected(...)`;
- `clear_section(...)`;
- `clear_all(...)`;

сервис автоматически вызывает `IndexManager.sync_after_delete(...)`. Это устраняет ситуацию, когда файл уже удален из `datasets/...`, но таблица **Project Database · Индексация файлов** продолжает показывать старую запись.

### Интеграция с Project Database UI

Экран **Project Database · Индексация файлов** теперь использует `IndexManager`, а не прямые функции индекса. Добавлена отдельная команда:

- `🧹 Перестроить индекс` — удаляет из индекса мертвые записи и пересобирает список файлов по фактическому состоянию проекта.

## Обязательное правило индексации

После любой операции, которая меняет файловую систему проекта, должен выполняться один из сценариев:

```text
create/import/rename/delete/restore
    ↓
Storage Lifecycle Framework
    ↓
IndexManager.rebuild_project_index(project_id)
    ↓
UI Refresh
```

Пользователь не должен вручную чистить Project Database после удаления Dataset. Ручная кнопка перестроения индекса остается только как диагностическая/service-команда.
