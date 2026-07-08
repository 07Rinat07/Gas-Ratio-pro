# Well Manager Service Contract

## Назначение

`WellManagerService` является единственной UI-facing точкой для управления сохраненными скважинами и их версиями.
Интерфейс приложения не должен напрямую вызывать `wells.repository` для сохранения, удаления, очистки или чтения версий скважин.

## Архитектурные правила

- Физическое удаление скважины или версии выполняется только через `DeleteEngine`.
- Перед удалением сервис освобождает file handles, resources и cache entries через Storage Lifecycle.
- Repository-функции отвечают за manifest/metadata и файловое чтение/запись, а не за lifecycle-managed delete.
- Скважина без версий удаляется полностью, чтобы она не появлялась снова после rerun/restart.
- UI использует только публичный контракт сервиса и compatibility aliases из этого документа.

## Public API

### Listing / loading

- `wells_root`
- `well_dir(well_id)`
- `version_dir(well_id, version_id)`
- `list_wells()`
- `list()` — compatibility alias
- `list_records()` — compatibility alias
- `count_wells()`
- `load_well(well_id)`
- `load(well_id)` — compatibility alias
- `get(well_id)` — compatibility alias

### Save / read

- `save_version(...) -> WellSaveResult`
- `save(...) -> WellSaveResult` — compatibility alias
- `create_version(...) -> WellSaveResult` — compatibility alias
- `read_file_bytes(well_id, version_id, file_key) -> bytes`
- `read_bytes(...) -> bytes` — compatibility alias

### Delete / clear

- `delete_well(well_id) -> WellDeleteResult`
- `delete(well_id) -> WellDeleteResult` — compatibility alias
- `remove_well(well_id) -> WellDeleteResult` — compatibility alias
- `delete_record(well_id) -> WellDeleteResult` — compatibility alias
- `delete_version(well_id, version_id) -> WellVersionDeleteResult`
- `delete_well_version(well_id, version_id) -> WellVersionDeleteResult` — compatibility alias
- `remove_version(well_id, version_id) -> WellVersionDeleteResult` — compatibility alias
- `delete_version_record(well_id, version_id) -> WellVersionDeleteResult` — compatibility alias
- `clear_wells() -> WellClearResult`
- `clear() -> WellClearResult` — compatibility alias
- `clear_all() -> WellClearResult` — compatibility alias

### Storage Lifecycle integration

- `register_well_file(well_id, version_id, file_key, owner="Well Manager", description="")`
- `register_well_cache(cache_key, owner="Well Manager", well_id=None, version_id=None, description="")`
- `release_well_resources(well_id, version_id=None) -> int`
- `refresh() -> tuple[WellRecord, ...]`
- `health() -> WellManagerHealth`
- `diagnostics() -> dict[str, object]`

## Result DTOs

- `WellSaveResult(record)`
- `WellDeleteResult(well_id, deleted, delete_result, released_resources)`
- `WellVersionDeleteResult(well_id, version_id, deleted, well_deleted, remaining_versions, record, delete_result, released_resources)`
- `WellClearResult(deleted_count, released_resources)`
- `WellManagerHealth(well_count, version_count, open_resources, cache_entries)`

## Sprint 1 acceptance criteria

- Well delete removes the storage folder through `DeleteEngine`.
- Well version delete removes the version folder through `DeleteEngine`.
- Last-version delete removes the complete well folder so empty wells do not reappear.
- Registered preview resources/cache entries are released before delete.
- Old UI aliases remain available until Sprint 1.5 removes compatibility code.
