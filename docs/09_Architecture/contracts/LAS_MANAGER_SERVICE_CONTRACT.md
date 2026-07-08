# LAS Manager Service Contract

`LasManagerService` is the public service boundary for project LAS files.
The Streamlit UI and Dataset Manager must not call `projects.las_files.delete_project_las_file()` directly.

## Public methods

- `list_files(project_id, include_archived=False)`
- `list_wells(project_id, include_archived=False)`
- `save_file(...)`
- `archive_file(project_id, las_file_id)`
- `restore_file(project_id, las_file_id)`
- `delete_file(project_id, las_file_id)`
- `delete(project_id, las_file_id)` compatibility alias
- `clear_files(project_id, include_archived=True)`
- `clear(project_id, include_archived=True)` compatibility alias
- `read_bytes(project_id, las_file_id)`
- `read_dataframe(project_id, las_file_id)`
- `export_zip(project_id, las_file_ids, formats)`
- `refresh(project_id)`

## Delete behavior

Deletion must:

1. release LAS resources and file handles;
2. clear LAS-related cache entries;
3. delete files via `DeleteEngine`;
4. update the LAS manifest;
5. synchronize the project index via `IndexManager`.
