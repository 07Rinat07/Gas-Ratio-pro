# LAS Viewer Overlay Preset Exchange v128

Adds renderer-neutral import and export of overlay style presets between projects.

- Portable UTF-8 JSON exchange schema.
- Custom presets exported by default; builtin presets remain application-owned.
- Optional selection by preset name.
- Explicit collision policies: `skip`, `replace`, `error`.
- Builtin presets cannot be replaced by imported data.
- Atomic file export and deterministic serialization.
