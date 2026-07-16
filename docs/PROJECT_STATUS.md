# Current increment: v222.27 — Legacy LAS compatibility foundation

## Completed

- Added explicit support policy for LAS files older than 2.0, including LAS 1.x archives.
- Added tolerant metadata classification for files with missing or non-standard version headers.
- Added stable compatibility warning codes without rewriting source data.
- Preserved bounded header-only scanning and immutable source artifacts.

## Compatibility contract

- LAS 1.x is accepted in `legacy-pre-2.0` mode.
- Files without a parseable `VERS` value are accepted in `legacy-tolerant` mode when recognizable LAS sections are present.
- Original bytes, mnemonics, units and project/well names are never translated or silently normalized.
- Compatibility warnings are stored as stable machine-readable codes.

## Next

- Localize import outcomes for `ru`/`kk`/`en`.
- Add detailed legacy LAS validation codes for WRAP, delimiters, malformed parameter cards and encoding anomalies.
- Add SQLite metadata catalog projection.
- Connect Dataset registration to the production LAS import workflow.
