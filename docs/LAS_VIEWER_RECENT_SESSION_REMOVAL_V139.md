# LAS Viewer recent session removal (v139)

Version 139 adds safe removal of one recent LAS Viewer session.

- Removal uses the stable public `session_key`; UI code never receives filesystem paths.
- Repository filenames are validated before any delete operation.
- The primary autosave and its `.bak` recovery copy are removed together.
- Missing or unsafe identifiers return deterministic renderer-neutral results.
- Other recent sessions remain untouched.
