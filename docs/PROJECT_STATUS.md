# Current increment: v222.55 — Stabilization & Hardening I

Implemented:
- fixed the project-menu UnboundLocalError caused by a function-local import shadowing the module service-container factory;
- added a centralized Workbench incident boundary;
- added UI Platform ADR and platform-quality governance documents;
- synchronized runtime and launcher versions.

Next:
- full route/language smoke audit;
- localized empty states;
- renderer performance and UI consistency audit.

# Current increment: v222.51 — Recoverable import operations

Implemented:
- durable compact job snapshots in each project;
- restart recovery as `interrupted` without hidden re-execution;
- cancellation requests for active jobs;
- filtered history and JSON/CSV export;
- safe cleanup of unreferenced staging files;
- synchronized RU/KK/EN Import Wizard documentation.

Next:
- cooperative per-file cancellation inside batch runners;
- resumable jobs with explicit user confirmation;
- retention policy for history and staging;
- readiness dashboard and import-history navigation in Project Explorer.

# Current increment: v222.42 — Interpretation export project-root bugfix

- Interpretation Workspace export no longer references the undefined `PROJECTS_ROOT` global.
- PDF preview and background export now use `LAS_CORRELATION_PROJECTS_ROOT`, matching the active project repository boundary.
- Regression coverage verifies the export fragment and primary Workbench routes.

# Current increment: v222.41 — Industry import preview and optional trace inventory

Implemented:
- generated, legally redistributable conformance-fixture policy;
- optional `segyio` trace-header inventory with manual inline/crossline byte mapping;
- DLIS/LIS79 logical-file summaries through the lazy `dlisio` boundary;
- localized metadata-only import preview contracts for ru/kk/en;
- adapter/service regression tests without trace or curve-array materialization.

Next:
- wire the import preview into the production Data workspace;
- add legal CI fixtures for installed `dlisio` and `segyio`;
- add coordinate scalar/trace-coordinate inventory and geometry confidence diagnostics;
- add DLIS frame/channel selection before import.


# Current increment: v222.40 — DLIS/LIS79 and SEG-Y metadata adapter foundation

Implemented:
- mandatory policies for open standards, lawful research and third-party licensing;
- machine-readable component review registry;
- synchronized ru/kk/en user and developer instructions;
- documentation-manifest and release-gate coverage.

Next:
- evaluate the first concrete external candidates for DLIS/LIS79 and SEG-Y using primary specifications and the new registry;
- continue QC template profiles and Dataset comparison UI.
# Current increment: v222.37 — Workbench state-controller bugfix

Implemented:
- fixed `AttributeError: ApplicationStateController has no attribute get`;
- restored the shared project-navigation preparation path used by Dashboard, Data, LAS, Correlation and Reports;
- retained `get_value()` as the preferred API and added a read-only compatibility alias;
- added route/state regression tests.

Next:
- expose QC reports and registered exports in Project Explorer;
- add direct download actions for registered PDF/DOCX artifacts;
- add QC badges and summary data to Dataset version comparison.

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


## v222.36 status

QC Platform Phase III completed. The production LAS Editor now exposes localized QC status, filters, findings and curve statistics. QC reports can be persisted as derived Datasets and PDF/DOCX outputs are registered as immutable export artifacts linked by provenance.

Next: expose saved QC reports and exports in Project Explorer, add downloadable export actions, and attach QC summaries to Dataset version comparison.

## v222.38 — QC Explorer and downloads

QC reports and QC exports are now visible in dedicated lazy Project Explorer folders. Registered PDF/DOCX artifacts can be downloaded through a bounded Data Platform service, and Dataset version comparisons include the latest QC status/count summary for each side.

Next: add report-template profiles, localized QC history labels, and interactive rendering of the QC comparison summary.

### v222.40 — Subsurface binary metadata adapters

DLIS, LIS79, and SEG-Y now have explicit metadata-scanner boundaries. SEG-Y baseline scanning is dependency-free and bounded to 3600 bytes. `dlisio` and `segyio` are approved as optional lazy adapters after source/license review; neither is vendored or imported during application startup.


## v222.43 — Interpretation and export compatibility stabilization

The missing `resolve_interpretation_id` application-boundary contract has been restored and is now reused by the interval panel. Background export again accepts optional externally supplied compact metadata state while production callers continue to use the application-service container state. The focused interpretation, Workbench route, and background-export profile passes 223 tests.


## v222.44 — Production subsurface metadata preview

Data Workspace now contains a separate bounded preview surface for DLIS, LIS79 and SEG-Y. SEG-Y trace-header diagnostics support configurable inline/crossline and coordinate byte mappings, coordinate-scalar application, X/Y extents, valid-coordinate coverage and geometry confidence. Binary payloads and seismic amplitudes are not sent through the tabular calculation importer. Focused Data Platform, i18n and container regression: 67 tests passed.


## v222.45 — Localization consistency and preview persistence

The language selector is now a persistent website-style RU / ҚАЗ / EN control available throughout Workbench. Documentation Center reads the same locale and resolves only the matching manifest-backed documents, with an explicit fallback notice when a translation is absent. Data Workspace can persist bounded subsurface metadata previews as immutable preview Datasets and exposes DLIS/LIS79 logical-file/frame/channel choices through the optional adapter boundary.

## v222.46 — Unified Import Pipeline foundation

Implemented the lightweight plugin registry, capability matrix, preview cache, project-scoped import profiles and explainable readiness scoring. These contracts reuse the existing scanners and keep optional DLIS/SEG-Y dependencies behind adapter boundaries.

## v222.47 — Import Wizard and Batch Foundation

The production import backend now provides a JSON-safe wizard state machine, per-file batch failure isolation, metadata-only quick QC and persisted Dataset readiness. Project Explorer exposes readiness without opening source artifacts.

## v222.48 status
Multilingual README and documentation entry points are implemented and guarded by release tests.

## v222.49 status

The public README entry point now reflects the actual multi-format platform rather than the earlier LAS/Excel-only scope. Russian, Kazakh, and English overview files are synchronized and protected by a format-coverage release test.

## v222.50 status

Professional Import Wizard is now connected to Data Workspace. Multi-file imports run through a bounded background job manager, persist terminal history per project, expose per-file results, and can retry failed items without repeating successful files.


## v222.52 status

Import jobs now support cooperative cancellation checkpoints between batch items, explicit resume of interrupted jobs, and a project-scoped retention policy for history and stale staging files. No interrupted job is resumed implicitly.


## v222.53 status

Import History is now available as a lazy Project Explorer branch. The Professional Import Wizard exposes a project-level readiness dashboard built only from Dataset Manifest metadata. No source artifact, LAS table, DLIS frame, or SEG-Y trace sample is opened for these summaries.


## v222.54 — Readiness filters and correlation preparation

- Added manifest-only readiness filters by status and format.
- Import History jobs now expose links to datasets created by each job.
- Added project-level correlation-readiness analysis based on LAS manifests, shared curves and depth metadata.
- No LAS rows or SEG-Y/DLIS payloads are loaded by these projections.

## v222.56 — UI Platform Foundation

The first UI abstraction layer is operational. Design tokens, theme selection, JSON-safe component contracts and a thin Streamlit adapter are available. The global RU/ҚАЗ/EN switcher is the first production control migrated to this layer and no longer uses stretched full-width buttons.

## v222.57 — Report & Diagnostics UX Hardening

The report panel no longer occupies most of the page by default. Printed PDF and DOCX outputs use larger legends, larger supporting text, higher-resolution figures and a shared corporate plot theme. Developer diagnostics now show a concise health summary first; detailed lifecycle, cache, repository and session tables are opt-in.
