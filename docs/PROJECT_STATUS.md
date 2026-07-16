# Current increment: v222.28 — Production LAS Dataset registration and metadata catalog

Implemented:
- production LAS Viewer open workflow registers an immutable Data Platform Dataset Manifest;
- SHA-256 duplicate information and stable validation codes are returned with the viewer result;
- project-scoped SQLite metadata catalog projection is maintained beside JSON manifests;
- LAS 1.x and tolerant legacy imports remain explicitly classified and queryable;
- validation includes legacy format, missing version, incomplete header, WRAP=YES, missing curves/depth/NULL/STEP and bounded-header conditions;
- import result messages are localized independently for Russian, Kazakh and English;
- machine-readable codes remain language-independent.

Next:
- expose localized import summary in the Streamlit LAS upload surface;
- add reconciliation/rebuild of SQLite projection from immutable manifests;
- add encoding and delimiter diagnostics for archival LAS;
- migrate remaining LAS save/import entry points to the Dataset registration boundary.

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

### v222.29 — LAS import reconciliation and legacy diagnostics
Implemented localized import feedback, SQLite reconciliation from immutable manifests, and encoding/delimiter diagnostics for archival LAS.


## v222.30 — Legacy LAS UI and catalog operations
- Added manual SQLite metadata-catalog reconciliation in Workbench Diagnostics Center.
- Added bounded decimal-comma and fixed-width legacy LAS diagnostics.
- Added stable validation codes and synchronized ru/kk/en messages.


## v222.31 — LAS Editor Dataset lineage
- LAS Editor uploads are registered once per session/checksum and show localized import findings.
- Edited LAS exports become immutable Dataset versions linked to the uploaded source.
- Header scanner compares Curve Information count with the first bounded data-row column count.


## v222.32 — Dataset lineage explorer and LAS import modes

- Project Explorer has a lazy Dataset history branch with immutable lineage/version nodes.
- LAS Editor exposes tolerant and strict import modes on ru/kk/en.
- Strict mode performs pre-persistence blocking; tolerant mode keeps archival compatibility.
- Header scanner samples several bounded rows and detects unstable column counts.
- Profile regression: 60 tests passed.


### v222.33 — Dataset Version Properties and bounded LAS depth QC

- Dataset version selection exposes SHA-256, provenance, artifact reference and previous-version metadata without reading LAS payloads.
- Application service can compare two immutable versions from one lineage using manifest metadata only.
- LAS scanner validates monotonic depth and STEP stability over the bounded sample rows.

## v222.34 — LAS QC Platform Foundation

- Added `core/qc` as a stable, format-independent QC boundary over the professional LAS QC implementation.
- Added language-independent `QC-*` finding codes and JSON-safe curve statistics.
- Added `QCApplicationService` and lazy application-service-container integration.
- Added synchronized ru/kk/en QC messages, terminology, user guidance, developer guidance and documentation manifest revision checks.
- Source LAS data remains immutable; QC is analytical and non-destructive.

Next: persist QC reports as derived Dataset artifacts and expose a localized QC summary in Workbench.

## v222.35 status

QC Platform Phase II started. QC reports are now persistable as derived Dataset artifacts linked to the source Dataset through provenance. A JSON-safe filtered projection and lazy PDF/DOCX export boundary are available. Native Workbench panel wiring remains the next UI increment.
