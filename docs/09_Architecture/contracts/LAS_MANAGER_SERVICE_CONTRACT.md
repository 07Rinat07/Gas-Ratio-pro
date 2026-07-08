# LAS Manager Service Contract

## Назначение

`LasManagerService` является единственной UI-facing точкой для управления LAS-файлами проекта.
Интерфейс приложения не должен напрямую вызывать `projects.las_files` для операций сохранения,
архивирования, восстановления, удаления, очистки, чтения и ZIP-экспорта проектных LAS-версий.

## Архитектурные правила

- Физическое удаление LAS выполняется только через `DeleteEngine`.
- Перед удалением сервис освобождает file handles, resources и cache entries через Storage Lifecycle.
- После save/archive/restore/delete/clear сервис синхронизирует Project Database через `IndexManager`.
- Repository-функции отвечают за manifest/metadata, а не за lifecycle-managed delete.
- UI использует только публичный контракт сервиса и compatibility aliases из этого документа.

## Public API

### Listing

- `list_files(project_id, include_archived=False)`
- `list(project_id, include_archived=False)` — compatibility alias
- `list_las_files(project_id, include_archived=False)` — compatibility alias
- `list_wells(project_id, include_archived=False)`
- `list_las_wells(project_id, include_archived=False)` — compatibility alias

### Paths

- `projects_root`
- `export_formats`
- `las_dir(project_id, las_file_id)`
- `source_path(project_id, las_file_id)`

### Save / archive / restore

- `save_file(...) -> LasSaveResult`
- `save(...) -> LasSaveResult` — compatibility alias
- `create(...) -> LasSaveResult` — compatibility alias
- `archive_file(project_id, las_file_id) -> LasArchiveResult`
- `archive(project_id, las_file_id) -> LasArchiveResult` — compatibility alias
- `restore_file(project_id, las_file_id) -> LasArchiveResult`
- `restore(project_id, las_file_id) -> LasArchiveResult` — compatibility alias

### Delete / clear

- `delete_file(project_id, las_file_id) -> LasDeleteResult`
- `delete(project_id, las_file_id) -> LasDeleteResult` — compatibility alias
- `remove_file(project_id, las_file_id) -> LasDeleteResult` — compatibility alias
- `clear_files(project_id, include_archived=True) -> LasClearResult`
- `clear(project_id, include_archived=True) -> LasClearResult` — compatibility alias
- `clear_all(project_id, include_archived=True) -> LasClearResult` — compatibility alias

### Read / export

- `read_bytes(project_id, las_file_id) -> bytes`
- `read_dataframe(project_id, las_file_id)`
- `export_zip(project_id, las_file_ids, formats=PROJECT_LAS_EXPORT_FORMATS) -> bytes`
- `export(...) -> bytes` — compatibility alias

### Storage Lifecycle integration

- `register_las_file(project_id, las_file_id, owner="LAS Manager", description="")`
- `register_las_cache(cache_key, owner="LAS Manager", path=None, description="")`
- `release_las_resources(project_id, las_file_id) -> int`
- `rebuild_index(project_id) -> IndexSyncResult`
- `validate_index(project_id) -> IndexSyncResult`
- `health(project_id) -> LasManagerHealth`
- `diagnostics() -> dict[str, object]`

## Result DTOs

- `LasSaveResult(record, index_sync)`
- `LasDeleteResult(project_id, las_file_id, deleted, delete_result, released_resources, index_sync)`
- `LasArchiveResult(project_id, las_file_id, archived, record, index_sync)`
- `LasClearResult(project_id, deleted_count, released_resources, index_sync)`
- `LasManagerHealth(project_id, file_count, well_count, open_resources, cache_entries)`

## Sprint 1 acceptance criteria

- LAS delete removes the storage folder through `DeleteEngine`.
- LAS delete removes the manifest record only after lifecycle delete succeeds.
- Project Database index no longer shows deleted LAS source files after sync.
- Registered LAS preview resources/cache entries are released before delete.
- Old UI aliases remain available until Sprint 1.5 removes compatibility code.
