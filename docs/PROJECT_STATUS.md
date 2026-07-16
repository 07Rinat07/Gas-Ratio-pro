# Current increment: v222.25 — Data Platform Foundation I

## Completed

- Added an allow-listed Data Format Registry for LAS, DLIS, SEG-Y, RESQML, GRDECL, GIS, HDF5/NetCDF, tabular and report formats.
- Added versioned, JSON-safe Dataset Manifest and provenance contracts.
- Added streaming SHA-256 calculation and project-contained Artifact Store with atomic writes.
- Added atomic project-scoped Dataset Manifest Repository and payload-free summaries.
- Added a lazy workspace-scoped Data Platform Application Service and container boundary.
- Kept all heavy parser dependencies out of the foundation layer.

## Next

- Add duplicate detection and immutable dataset version lineage.
- Add metadata-scanner adapter contracts and implement the LAS header scanner first.
- Expose a localized dataset registration/import result without putting file payloads in session state.
