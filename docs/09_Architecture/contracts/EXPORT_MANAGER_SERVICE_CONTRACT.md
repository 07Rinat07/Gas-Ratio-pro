# ExportManagerService Contract

## Purpose

`ExportManagerService` is the single public service boundary for project export storage.
UI code must not call export repository functions or delete export files directly.

## Public API

### Read/list

- `list_exports(project_id)`
- `list(project_id)` compatibility alias
- `count_exports(project_id)`
- `count(project_id)` compatibility alias
- `read_export_bytes(project_id, export_id)`
- `read_bytes(project_id, export_id)` compatibility alias
- `refresh(project_id)`

### Write/delete

- `save_export(...)`
- `delete_export(project_id, export_id)`
- `delete(project_id, export_id)` compatibility alias
- `clear_exports(project_id)`
- `clear(project_id)` compatibility alias

### Storage Lifecycle

Export deletion must go through:

1. `FileHandleManager.release_path(...)`
2. `ResourceManager.release_path(...)`
3. `CacheManager.clear_path(...)`
4. `DeleteEngine.delete_path(...)`
5. manifest rewrite
6. `IndexManager.sync_after_delete(...)`

## Architecture Rules

- UI must use this service only.
- UI must not call `shutil.rmtree`, `Path.unlink`, `os.remove`, or low-level export repository delete functions.
- Export cleanup must synchronize the project index after physical deletion.
- Export preview/cache/file handles must be released before deletion.
