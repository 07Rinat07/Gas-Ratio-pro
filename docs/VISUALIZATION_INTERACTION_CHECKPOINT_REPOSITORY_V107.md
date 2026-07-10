# Visualization Interaction Checkpoint Repository v107

This increment adds directory-level management for multiple interaction checkpoint files.

Capabilities:

- deterministic checkpoint file naming;
- listing only compatible and valid checkpoint files;
- restoring the newest compatible state;
- ignoring corrupted or unrelated files;
- pruning old checkpoint files by retention count;
- renderer-neutral metadata for repository entries.

The repository delegates serialization, migration, checksums and atomic writes to the existing checkpoint file store.
