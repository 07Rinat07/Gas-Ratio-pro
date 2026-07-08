# ProjectManagerService Contract

Sprint 1 Service Compatibility Pass fixes the public Project Manager service contract used by the existing Streamlit UI.

## Responsibility

`ProjectManagerService` is the only supported application-level entry point for project lifecycle operations. UI code must not delete project folders directly and must not call low-level project repository delete helpers.

## Public methods and properties

The UI and manager layer may use only these project service members:

- `projects_root`
- `project_dir(project_id)`
- `ensure_default()`
- `ensure_default_project()` compatibility alias
- `list_projects(include_archived=False)`
- `list()` compatibility alias
- `count_projects(include_archived=False)`
- `load_project(project_id)`
- `load(project_id)` compatibility alias
- `open_project(project_id)` compatibility alias
- `create_project(name, description="", project_id=None)`
- `create(name, description="", project_id=None)` compatibility alias
- `touch_recent(project)`
- `list_recent(include_missing=True)`
- `clear_recent_history()`
- `remove_recent_entry(project_id)`
- `set_recent_flags(project_id, pinned=None, favorite=None)`
- `list_project_exports(project_id)` transitional diagnostic helper
- `delete_project_complete(project_id)`
- `delete_project(project_id)` compatibility alias
- `delete(project_id)` compatibility alias
- `remove_project(project_id)` compatibility alias
- `rebuild_index(project_id)`
- `validate_index(project_id)`
- `sync_indexes(project_ids=None)`
- `health()`

## Lifecycle requirements

Any destructive Project operation must:

1. reject deletion of the default project;
2. count related managed records before deletion when needed for UI feedback;
3. release file handles through Storage Lifecycle;
4. clear registered cache/resource entries through Storage Lifecycle;
5. delete the project directory through `DeleteEngine`;
6. remove the project from recent history;
7. ensure the default project exists;
8. rebuild the fallback project index through `IndexManager`.

## Compatibility rule

During Sprint 1 and Sprint 1.5 the service must not remove public properties or methods used by `app/streamlit_app.py`. Internal implementation may change, but public API compatibility must be preserved until the UI has been fully migrated to the final Unified Manager Framework.
