# Current increment: v222.26 — Data Platform Foundation II

## Completed

- Added project-scoped duplicate detection by streaming SHA-256.
- Added immutable Dataset lineage with `lineage_id`, `previous_dataset_id` and sequential versions.
- Prevented existing manifest mutation and source-artifact overwrite.
- Added a lightweight metadata-scanner protocol.
- Added the first bounded LAS header-only scanner that stops at `~ASCII`.
- Added JSON-safe registration results and scanner inventory diagnostics.

## Next

- Add localized dataset import outcomes for `ru`/`kk`/`en`.
- Add validation/error codes for malformed LAS headers.
- Add a SQLite metadata catalog projection without moving large artifacts into SQL.
- Connect dataset registration to the import workflow behind the application-service boundary.
