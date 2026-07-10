# Visualization Interaction Checkpoint Backup v108

Version 108 adds validated ZIP backup and restore for checkpoint repositories.

The backup contains only compatible checkpoint files and a deterministic manifest with file sizes and SHA-256 checksums. Restore validates the archive, blocks unsafe paths, verifies every file before writing, and uses atomic replacement. Existing files are skipped by default and can be explicitly overwritten.
