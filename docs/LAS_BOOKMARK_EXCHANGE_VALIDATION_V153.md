# LAS Bookmark Exchange Validation v153

Version 153 adds schema validation and migration for portable LAS Viewer bookmarks.

- Current exchange schema: `las.viewer.recent-session-bookmark-exchange` version `1.0`.
- Legacy version `0.9` is migrated in memory without mutating the source payload.
- Imported records are validated before repository changes are applied.
- Missing session identity, invalid positions, incompatible schemas and versions are rejected.
- Empty labels are reported through deterministic diagnostics and use the existing fallback during import.
