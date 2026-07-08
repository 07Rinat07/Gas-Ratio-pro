# DatasetManagerService Contract

Sprint 1 Service Compatibility Pass fixes the public Dataset Manager service contract used by the existing Streamlit UI.

## Public sections

The service must expose a stable `section_specs` mapping and support these sections:

- `las`
- `csv`
- `excel`
- `core`
- `mud_log`
- `production`

The `las` section is included for UI compatibility because `Dataset Manager · LAS` is rendered together with CSV/Excel/Core/Mud Log/Production sections.

## Public methods

The UI and manager layer may use only these methods:

- `supported_sections()`
- `is_supported_section(section)`
- `section_label(section)`
- `datasets_root(project_id)`
- `section_dir(project_id, section)`
- `list_records(project_id, section, include_archived=True)`
- `delete_dataset(project_id, section, dataset_id)`
- `delete_selected(project_id, section, dataset_ids)`
- `clear_section(project_id, section)`
- `clear_all(project_id)`
- `sync_project_index(project_id)`
- `refresh(project_id)` compatibility alias
- `delete(project_id, section, dataset_id)` compatibility alias
- `clear(project_id, section)` compatibility alias
- `register_dataset_file(...)`
- `register_dataset_cache(...)`
- `release_dataset_resources(project_id, section, dataset_id)`
- `diagnostics()`

## Lifecycle requirements

Any destructive Dataset operation must:

1. release file handles through `FileHandleManager`;
2. release registered resources through `ResourceManager`;
3. clear cache entries through `CacheManager`;
4. delete files through `DeleteEngine`;
5. update the corresponding manifest;
6. rebuild the project index through `IndexManager`.

## Compatibility rule

During Sprint 1 and Sprint 1.5 the service must not remove public properties or methods used by `app/streamlit_app.py`. Internal implementation may change, but public API compatibility must be preserved until the UI has been fully migrated to the final manager framework.
