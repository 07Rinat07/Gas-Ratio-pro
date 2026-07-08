# Storage Lifecycle Framework

Sprint 1 freezes feature development until file/resource lifecycle is stable.

## Goal

Every destructive storage operation must release runtime resources, clear Python-owned handles and retry Windows-sensitive deletion before reporting an error to the UI.

## Components

- `core/storage_lifecycle.py`
  - `ResourceManager`
  - `DeleteEngine`
  - `StorageDeleteError`
- `services/dataset_manager_service.py`
  - service-layer Dataset Manager facade
  - routes Dataset delete/clear operations through `DeleteEngine`
- `projects/datasets.py`
  - repository-level Dataset delete/clear functions

## Architectural rules

- UI must not call `shutil.rmtree`, `Path.unlink`, or `Path.rmdir` directly.
- Dataset Manager deletion goes through `DatasetManagerService`.
- Repository functions decide which paths belong to entities.
- `DeleteEngine` is the only component responsible for physical path deletion.
- Locked file errors must show diagnostic messages instead of generic failure text.

## First covered scenario

`Dataset Manager · Mud Log` can now clear a section that contains saved Excel source files using lifecycle deletion and retry behavior.
