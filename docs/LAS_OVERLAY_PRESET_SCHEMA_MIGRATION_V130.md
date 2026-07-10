# LAS Overlay Preset Schema Migration v130

Version v130 adds backward-compatible migration for overlay preset exchange packages.

Supported exchange versions:

- 1.0 current format
- 0.9 legacy format migrated automatically to 1.0

Legacy aliases are normalized before validation and import. Migration does not mutate the caller payload. Unsupported repository and exchange versions are rejected explicitly.
