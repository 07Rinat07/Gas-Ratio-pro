# LAS Viewer Workspace Autosave v135

Adds renderer-neutral autosave and crash recovery for the compact LAS Viewer state.

- Atomic UTF-8 JSON writes.
- SHA-256 integrity verification.
- Deduplication of unchanged states.
- One previous autosave retained as a backup.
- Automatic fallback to the backup when the primary file is corrupt.
- Optional project and LAS context validation during recovery.
- Raw LAS samples, render models, and caches are not persisted.
