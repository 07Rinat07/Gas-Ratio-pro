# Visualization Interaction Checkpoint Migration v106

Version 2.0 of the checkpoint file envelope adds explicit content metadata and preserves deterministic, atomic JSON persistence.

The loader accepts current 2.0 files and legacy 1.0 files. Legacy files are normalized in memory after checksum validation. `migrate_file()` rewrites a supported legacy file in the current format.

Unsupported future versions are rejected instead of being guessed. Metadata reports the current format and the source version when an in-memory migration occurred.
