# LAS Viewer Workspace Autosave Repository v136

Adds multiple autosave management on top of the atomic LAS Viewer autosave store.

Capabilities:

- deterministic per-project/per-LAS autosave filenames;
- recovery of the newest compatible valid session;
- corrupted autosaves are skipped safely;
- project and LAS context filtering;
- bounded retention and pruning;
- repository inspection and full cleanup.

The repository persists compact `LasViewerState` only. Raw LAS samples, render models,
and caches remain outside the persistence contract.
