# LAS Viewer Overlay Presets v127

Version 127 adds persistent renderer-neutral presets for cursor and selection overlay styles.

## Scope

- immutable named presets;
- built-in Default, High Contrast and Presentation profiles;
- custom preset create, replace, lookup and delete operations;
- protection of built-in profiles;
- deterministic JSON contract;
- atomic UTF-8 file persistence.

The module does not contain UI logic. A future LAS Viewer adapter may expose these presets without duplicating style validation or persistence rules.
