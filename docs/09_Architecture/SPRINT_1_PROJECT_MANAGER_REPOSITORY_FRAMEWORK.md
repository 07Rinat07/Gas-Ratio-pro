# Sprint 1 — Project Manager & Repository Framework

## Status

Started.

## Implemented in this iteration

- Recent Projects history is separated from physical project storage.
- Recent Projects now supports clearing only the history without deleting projects.
- Recent Projects supports removing a single history entry.
- Recent Projects supports pin/favorite flags.
- Project exports now support deleting a selected export from both manifest and disk.
- Project exports now support clearing all exports from both manifest and disk.
- Dashboard receives a real Streamlit control panel for Recent Projects instead of a read-only HTML-only list.
- Saved project exports panel receives a real management toolbar.

## Architecture rule

UI must not treat a read-only list as a storage manager. Every persistent list must have explicit actions and must call repository functions for physical changes.

## Next items

- Project Manager full-screen workspace.
- Project rename/clone/archive/import/export flow.
- Unified table toolbar component.
- Central physical cleanup engine for projects, wells, LAS, reports, exports and cache.
