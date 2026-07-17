# Latest implementation — Page Chrome & Print Center Contract v225.3

Status: COMPLETED

Implemented:
- `VisualizationPrintLayout` v2.1 reserves physical header, footer and repeated-legend regions;
- page title, subtitle, classification, document code, footer, page number and legend are serialized once as `page_pt` chrome primitives;
- SVG and PDF consume the same page primitives, while PNG is rasterized from the same SVG page set;
- geometry signature v3 includes physical page regions and page chrome;
- `VisualizationPageAwarePackage` v1.1 exposes chrome metadata and primitive counts;
- `VisualizationPrintCenterService` provides exact profile, orientation, DPI and page count in ru/kk/en;
- LAS Viewer export now consumes one page-aware SVG/PDF/PNG package rather than coordinating renderers independently;
- user and developer documentation, implementation plans, status, changelog and README files are synchronized in Russian, Kazakh and English.

Validation:
- focused visualization, renderer, package, Print Center and LAS Viewer checks pass;
- Python syntax compilation passes for all changed modules;
- the complete regression suite must still be run before deleting remaining legacy static-export branches.

Next priority: surface the localized physical-package summary in the visible Professional Print Center and pass the existing page-aware preview contract directly into DOCX/HTML.

# Latest implementation — Physical A4/A3 Page-Aware Rendering

Status: COMPLETED

Implemented:
- `core/physical_print_profiles.py` defines explicit A4/A3 portrait/landscape readability floors;
- `visualization.print.layout` v2 paginates ordered track slices and records per-page `track_ids` and source bounds;
- later pages repeat depth labels while retaining the same curves, scales, overlays and renderer-neutral primitives;
- PDF and SVG consume every physical page, clamp final font/stroke sizes, and apply source-offset transforms and page clips;
- PNG pages are rasterized from the same SVG page set at explicit DPI;
- report HTML/PDF/DOCX render every visualization page; asset registries and bundle manifests retain every page;
- renderer parity signature v2 covers the full page list, and export QA aggregates primitive/clip coverage across SVG pages.

Validation:
- syntax compilation passed for all changed modules;
- 34 focused automated checks passed through the lightweight harness;
- 3 multi-format embedding smoke checks passed for HTML, PDF flowables and DOCX images;
- the supplied runtime still lacks `pytest`, `plotly` and `streamlit`, so the complete suite cannot run here.

Next priority: wire the page-aware asset registry into the one-click Print Center, add shared page chrome/legend primitives and retire single-page fallbacks only after parity verification.

# Previous implementation — Forward-Compatible Report Preview Snapshot Migration

Status: COMPLETED

Implemented:
- report document-count snapshots now use schema v2 with a stable payload kind and explicit renderer-neutral marker;
- schema-v1 snapshots are upgraded without mutating the supplied mapping;
- durable loads preserve the exact pre-migration payload as a rollback backup and atomically replace the primary file;
- snapshots from a newer application schema are never downcast, quarantined as corruption or overwritten by an older build;
- storage health reports active/backup schema versions, migration requirements and backup-only recovery;
- Streamlit exposes migration and unsupported-schema diagnostics through the existing application-service boundary.

Validation:
- syntax compilation passed for all modified Python modules;
- 31 focused snapshot, persistence and application-service checks passed through a lightweight harness;
- the supplied runtime does not contain `pytest`, `plotly` or `streamlit`, so the complete project suite was not executable in this container.

Next priority: separate physical A4/A3 print profiles with minimum readable typography and page-aware track splitting.

# Latest implementation — Bounded Report Preview Quarantine Maintenance

Status: COMPLETED

Implemented:
- `ReportPreviewCountsMaintenanceResult`;
- configurable `max_quarantine_files` retention, defaulting to three files per project;
- `quarantine_paths()`, `maintain_quarantine()` and `purge_quarantine()` APIs;
- pruning on primary load, missing-state load and recovery paths;
- optional quarantine removal from `delete(..., include_quarantine=True)`;
- Streamlit reset removes all preview persistence artifacts.

Validation:
- syntax compilation passed;
- `104 passed` in focused reporting/background-export coverage.

Next priority: persistence health diagnostics and forward-compatible snapshot migrations.

# Latest implementation — Report Preview Snapshot Validation Diagnostics

Status: COMPLETED

Implemented:
- `build_report_document_counts_snapshot()` creates a JSON-safe schema-v1 payload with signature, timestamp and counts;
- `resolve_report_document_counts_snapshot()` validates compatibility and returns a renderer-neutral resolution state;
- stale, legacy, unsupported and corrupt snapshots are ignored with an explicit UI explanation;
- current snapshots are normalized to non-negative integer counters before use;
- Streamlit now stores and reads counts through the shared validation API instead of directly inspecting dictionaries.

Validation:
- syntax compilation passed;
- `78 passed` in focused reporting/export regression coverage;
- no runtime application log was available in the supplied archive.

Next priority: project-scoped durable persistence for the compact snapshot metadata.

# Latest implementation — Renderer Capability Diagnostics

Status: COMPLETED

Implemented:
- `ReportFormatCapability` and renderer-neutral capability matrices in `reports/report_designer.py`;
- capability reporting for PDF, DOCX, bundle, PNG, SVG and XLSX;
- bundle bookmark scope diagnostics and specialized static/tabular export notices;
- unknown-format fallback that preserves preview readiness while exposing a warning;
- Streamlit expander showing supported and unsupported features before rendering.

Validation:
- syntax compilation passed for the modified modules;
- `52 passed` in focused report/export regression coverage;
- `logs/app.log` is not present in the supplied archive.

Next priority: reuse the preflight-built EngineeringDocument in the structure preview and surface live document counts without rebuilding engineering content.

# Latest implementation — Document-Model Page Estimate Refinement and Format Readiness



Status: COMPLETED



Implemented:

- page estimation can consume an existing EngineeringDocument without recalculating engineering data;

- table-row, plot, visualization and notice counts refine component page ranges;

- target-format diagnostics distinguish PDF and DOCX limitations;

- Professional Export structure preview forwards the currently selected format;

- legacy callers remain compatible because document and target_format are optional.



Next priority: connect the preview to the preflight-built document model and expand capability diagnostics to all export formats.



# Latest increment — Report Structure Page Estimate and Export Readiness

Status: COMPLETED

The report structure preview now exposes a lightweight estimated page range and a component breakdown. Estimates are based only on resolved design composition and remain safe for every Streamlit rerun. Readiness diagnostics identify blocking design errors, disabled graphical sections and reports large enough to benefit from background export.

Next priority: refine estimates with prepared EngineeringDocument counts while keeping the preview renderer-neutral.

# Latest implementation — Background Export Runtime Performance Summary

Status: COMPLETED

Implemented:
- `BackgroundExportPerformanceSummary` and renderer-neutral aggregation in `reports/background_export_ui.py`;
- terminal-only success-rate and duration calculations;
- completed-artifact-only average size calculation;
- four compact Streamlit metrics plus explicit non-success counters;
- safe empty-history and active-only behavior.

Validation:
- syntax compilation passed;
- `37 passed` in focused background-export tests;
- no `logs/app.log` was available in the supplied archive.

Next priority: estimated report page composition and export-readiness diagnostics in the existing structure preview.

# Latest implementation — Automatic Export Polling and Cancellable Report Rendering

Status: COMPLETED

Implemented:
- Professional Export uses an isolated Streamlit fragment with a two-second refresh interval;
- active job progress updates without a manual refresh button;
- PDF/DOCX/bundle rendering accepts optional progress and cooperative cancellation callbacks;
- cancellation is checked between report sections and document blocks;
- progress remains monotonic through the existing BackgroundExportManager.

Next priority: validate cancellation against large field datasets and add slow-job diagnostics.

# Latest implementation — Streamlit Background Export Integration

Status: COMPLETED

Implemented:
- connected the recoverable background export manager to Professional Export;
- added project-scoped queue state, progress display, manual polling and Cancel;
- completed artifacts are transferred to the existing download cache and metadata-only history;
- background workers receive immutable request/configuration snapshots and never render Streamlit UI.

Next priority: automatic active-job polling and field acceptance for cancellation/recovery.

# Latest implementation — Recoverable Background Export Foundation

Status: COMPLETED

Implemented:
- added `reports/background_export.py` with a single-worker background queue;
- added metadata-only recoverable snapshots and orphan detection after restart;
- added cooperative cancellation and monotonic progress callbacks;
- added duplicate request protection and bounded snapshot retention;
- extended `ExportController.prepare()` with optional progress/cancellation hooks;
- synchronous export behavior remains backward compatible.

Next priority: Streamlit polling UI, Cancel action and completed-artifact handoff.

# Latest implementation — Confirmed Stale Export Rebuild

Status: COMPLETED

Implemented:
- stale export-history entries use a dedicated confirmation preflight;
- the confirmation summarizes the exact historical export request before reuse;
- confirmation restores the complete configuration and triggers a fresh render against current project data;
- cancellation is side-effect free;
- focused and extended reporting regression tests pass.

Next priority: cancellable long-running export execution with recoverable progress state.

# Latest implementation — Repeat Export Revision Preflight

Status: COMPLETED

Implemented:
- export history schema upgraded to v3 with a project-data revision fingerprint;
- active export data revision is derived from project id, source signature and calculation revision;
- history UI marks current, stale and legacy entries before repeat export;
- stale entries show an advisory warning and require a new render;
- v1/v2 history files remain backward-compatible.

Next priority: one-click confirmed re-render from a stale history entry.

# Latest implementation — Full-Fidelity Repeat Export

Status: COMPLETED

Implemented:
- export history schema upgraded to v2 with complete report-design metadata;
- repeat action restores mode, template, title, sections, appendix, page chrome, print scope, profile, format and depth range;
- legacy v1 export-history files migrate in memory through safe defaults;
- no rendered binaries or engineering datasets are persisted.

Next priority: compare historical request metadata with the current project revision before repeat export and surface stale-configuration warnings.

# Latest implementation — Export History Filtering and Repeat Action

Status: COMPLETED

Implemented:
- search plus format/profile filtering for project export history;
- repeat action restores profile, format and custom depth interval;
- pending-state application avoids modifying Streamlit widget keys after instantiation;
- metadata-only history remains bounded and project-scoped;
- focused and extended reporting regression tests pass.

Next priority: store report mode/template metadata for full-fidelity repeat export.

# Latest implementation — Export Draft Reset and Successful Export History

Status: COMPLETED

Implemented:
- explicit reset of project-scoped Export Wizard draft and related UI state;
- compact bounded history for successful exports;
- atomic metadata-only persistence without binaries, dataframes or credentials;
- separate history clear action and Streamlit history preview;
- regression tests for normalization, retention, deduplication and project isolation.

Next priority: history filtering and repeat-export action from a previous successful configuration.

# Latest implementation — Export Wizard Draft Persistence

Status: COMPLETED

Implemented:
- project-scoped unfinished export draft repository;
- automatic restore into Streamlit session state on first panel render;
- automatic save of profile, format, report design and print range;
- schema validation, atomic writes and project-boundary protection;
- no raw engineering payload or rendered artifact persistence.

Next priority: reset/clear draft control and compact history of successful exports.

# Latest implementation — Visual Export Wizard Review

Status: COMPLETED

Implemented:
- renderer-neutral five-step navigation model for the professional export workflow;
- final review contract with source, project, profile, format, destination and file name;
- Streamlit step indicator and review screen before binary rendering;
- submit button is disabled when preflight has a blocking issue;
- focused and extended reporting regression tests pass.

Next priority: project-scoped persistence and recovery of unfinished Export Wizard settings.

# Latest implementation — Interactive Report Structure Preview

Status: COMPLETED

Implemented:
- lightweight `ReportStructurePreview` built from the existing Report Designer contract;
- live preview of resolved mode, template, section order and export navigation options;
- blocking design issues are shown before rendering starts;
- no engineering calculations or binary files are generated by the preview;
- Streamlit integration and regression tests added.

Next priority: complete the visual Export Wizard step navigation and final review screen.

# Latest implementation — PDF Table of Contents and Bookmarks

Status: COMPLETED

Implemented:
- multi-pass PDF table of contents with resolved page numbers;
- PDF outline bookmarks for report title and engineering headings;
- automatic navigation policy for Brief, Standard and Full Engineering modes;
- renderer-only implementation without repeated engineering calculations;
- regression coverage using real PDF parsing.

Next priority: interactive report structure preview in Export Wizard.

## Latest implementation — Report Output Modes

- Added user-selectable Brief, Standard and Full Engineering report modes.
- Added Custom mode for manual template and section control.
- Report modes resolve through the existing renderer-neutral Report Designer.
- Export cache signatures now include the selected report mode.
- Next priority: table of contents and PDF bookmarks.

## Latest implementation — Export Performance and Memory Guard

- ExportController now limits artifact cache by count and actual binary payload size.
- Default artifact memory budget: 64 MiB per application session.
- Oversized artifacts are returned to the user but are not retained in cache.
- cache_metrics() exposes model entries, artifact entries and retained bytes.
- Next priority: large-LAS rendering benchmarks and selective dataframe downsampling.

# Latest implementation increment — Unified Chart Theme Engine

Completed:
- centralized Plotly visual profiles for screen, print and presentation;
- standardized typography, grids, axes, margins, legend surfaces, line widths and markers;
- added deterministic theme signatures for renderer/export cache invalidation;
- kept scientific data and axis ranges unchanged during visual styling;
- added regression tests for profile selection, immutability and export behavior.

Next priority: optimize large-LAS visualization and export performance.

# Latest increment — Unified Tooltip and Operation Feedback Layer

Status: COMPLETED

Implemented:
- centralized tooltip registry in `ui/ux_feedback.py`;
- validated progress plan for professional report export;
- Report Designer UI uses shared tooltip keys instead of duplicated text;
- progress stages are deterministic and covered by tests.

Next priority: expand tooltip coverage and start unified chart theme integration.

# GAS RATIO PRO — AI HANDOFF

## Текущее состояние

Готово:

- импорт LAS;
- автоматический и ручной mapping;
- расчет коэффициентов и интерпретация;
- инженерные планшеты;
- экспорт DOCX и PNG;
- Industrial PDF Layout;
- Professional Export Wizard;
- preflight-проверка экспорта;
- Professional Report Designer foundation;
- Streamlit Report Designer integration;
- designed PDF/DOCX/bundle export with cache-safe settings.

## Последний реализованный инкремент

Professional Report Designer UI Integration:

- шаблоны Engineering, Corporate и Minimal подключены к Streamlit;
- добавлены настройки заголовка, состава разделов, технического приложения и колонтитулов;
- PDF, DOCX и bundle строятся из одного designed EngineeringDocument;
- параметры дизайна включены в сигнатуру export cache;
- PNG, SVG и XLSX сохранены как отдельные специализированные каналы;
- добавлены интеграционные тесты.

## Следующий этап

1. Интерактивный preview структуры отчета.
2. Единый tooltip/help layer для Report Designer и Export Wizard.
3. Индикаторы выполнения операций.
4. Унификация графиков.
5. Оптимизация производительности.

## Архитектурные правила

- Не выполнять повторные инженерные расчеты в UI и renderers.
- Использовать PresentationModel и EngineeringDocument как единые источники данных.
- Не ухудшать производительность.
- Не ломать существующие export contracts.
- PDF должен выглядеть как промышленный инженерный отчет.

# Latest increment — Large-LAS Performance Acceptance Gates

Status: COMPLETED

Implemented:
- deterministic large-LAS benchmark payloads;
- cold/warm visualization pipeline measurements;
- acceptance gates for latency, memory, cache reuse and downsampling reduction;
- JSON CLI report via `scripts/run_large_las_benchmark.py`;
- regression tests for gate evaluation and real pipeline behavior.

Next priority: CI integration and runtime performance summary UI.

## 2026-07-13 runtime hotfix

Fixed the interpretation workspace crash `NameError: active_project is not defined` in the PNG/PDF/SVG controls. Static export no longer depends on workspace-local variables. `current_data_revision` is now built in the professional report export scope where export history consumes it. Direct Streamlit session-state access introduced by export persistence was replaced with the application state boundary. Regression test: `tests/test_static_export_scope_regression_v222_15.py`.

# Latest implementation — Recoverable Background Export Retry

Status: COMPLETED

Implemented:
- completed background jobs now distinguish between a live process-local artifact and metadata restored after restart;
- unavailable completed artifacts are shown as recoverable instead of downloadable;
- failed, cancelled, orphaned and artifact-lost jobs expose a one-click retry action;
- retry dismisses only the terminal snapshot and reuses the current validated Export Wizard state;
- active-job cancellation and duplicate-signature protection remain unchanged;
- focused and extended reporting regression tests pass.

Validation:
- `python -m py_compile reports/background_export_ui.py app/streamlit_app.py`;
- `65 passed` in the extended reporting/background-export regression set;
- `logs/app.log` was not present in the supplied archive, so no runtime log errors were available for review.

Next priority: bounded recent-background-jobs UI with retry diagnostics and manual large-LAS acceptance testing.

# Latest implementation — Bounded Background Export History and Retry Diagnostics

Status: COMPLETED

Implemented:
- compact newest-first UI for the five latest project-scoped background export jobs;
- persisted `retry_of_job_id` and `retry_reason` metadata on replacement jobs;
- retry diagnostics for failed, cancelled, orphaned and completed-with-lost-artifact jobs;
- safe Streamlit fragment compatibility fallback for mocked/older runtimes;
- focused background-export and Streamlit regression coverage.

Validation:
- `python -m py_compile reports/background_export.py reports/background_export_ui.py app/streamlit_app.py`;
- `78 passed` in focused background-export, dashboard-shell and Streamlit compatibility tests;
- full test suite was started but did not finish within 240 seconds and showed unrelated failures before timeout, so no full-suite pass is claimed;
- `logs/app.log` is not present in the supplied project archive.

Next priority: manual large-LAS cancel/retry acceptance test and terminal-job cleanup controls.

# Latest implementation — Terminal Background Export History Cleanup

Status: COMPLETED

Implemented:
- individual removal controls for terminal records in the recent background-export history;
- project-scoped bulk cleanup through `BackgroundExportManager.dismiss_terminal()`;
- preservation of completed jobs whose process-local result has not yet been handed to the UI;
- active jobs remain non-dismissible;
- null-safe completed-result handoff when no job matches the current export request signature;
- regression coverage for project scoping, result preservation, explicit destructive cleanup and Streamlit controls.

Validation:
- `python -m py_compile reports/background_export.py reports/background_export_ui.py app/streamlit_app.py`;
- `29 passed` in focused background-export and dashboard regression tests;
- `logs/app.log` is not present in the supplied project archive.

Next priority: manual large-LAS cancel/retry/cleanup acceptance test and runtime performance summary UI.

# Latest implementation — Background Export History Filters

Status: COMPLETED

Implemented:
- project-scoped recent export history can be filtered by status and export format;
- `ExportJobSnapshot` persists normalized `export_format` metadata;
- filtering is renderer-neutral, stable-order and backward compatible with old snapshots;
- empty status/format selections mean all records;
- the UI shows an explicit empty state when no history item matches;
- focused unit and Streamlit integration tests pass.

Next priority: expose job duration and artifact size, then connect runtime performance summary to diagnostics.

# Latest implementation — Background Export Duration and Artifact Size

Status: COMPLETED

Implemented:
- persisted terminal job duration in `ExportJobSnapshot`;
- persisted completed artifact size with renderer-neutral recursive size extraction;
- compact Russian duration and binary-size formatting for recent export history;
- duration, artifact size and export format are displayed together in the Streamlit history UI;
- backward-compatible loading of snapshots created before these metadata fields existed;
- focused unit and Streamlit regression coverage.

Validation:
- `python -m py_compile reports/background_export.py reports/background_export_ui.py app/streamlit_app.py`;
- `49 passed` in the focused background-export and export-history regression set;
- `logs/app.log` is not present in the supplied project archive.

Next priority: runtime performance summary UI, then optional history sorting by time/duration/size.

# Latest implementation — Background Export History Sorting

Status: COMPLETED

Implemented:
- post-filter sorting of recent background-export history by update time, duration and artifact size;
- ascending and descending modes for every supported metric;
- deterministic stable tie ordering across Streamlit reruns;
- safe fallback to newest-first for unknown or stale persisted sort values;
- project-scoped Streamlit sort selector and focused regression coverage.

Validation:
- `python -m py_compile reports/background_export.py reports/background_export_ui.py app/streamlit_app.py`;
- `34 passed` in focused background-export and Streamlit integration tests;
- `logs/app.log` was not present in the supplied archive.

Next priority: runtime performance summary UI, then interactive report-structure preview.

# Latest implementation — Actual EngineeringDocument Counts in Preview

Status: COMPLETED

Implemented:
- public renderer-neutral `report_document_counts()` aggregation;
- `build_report_structure_preview(..., document_counts=...)` for lightweight persisted counts;
- designed PDF/DOCX/bundle artifacts expose the counts from the exact document they rendered;
- background export returns counts to the Streamlit UI thread without mutating session state from the worker;
- the UI persists and displays actual section/table/row/plot/visualization counts on subsequent reruns;
- reset clears the persisted count snapshot;
- an explicit document overrides persisted counts.

Validation:
- syntax compilation for report designer, export adapter, background UI and Streamlit application;
- focused report designer/export/Streamlit tests pass;
- `logs/app.log` is not present in the supplied archive.

Next priority: bind persisted counts to the export request/design signature and suppress stale counts after control changes, then implement PDF page thumbnails.

# Latest implementation — Signature-bound Report Preview Counts

Status: COMPLETED

Implemented:
- public `build_report_document_counts_signature()` helper with canonical resolved design serialization;
- persisted count snapshots now store `{signature, counts}` instead of unscoped counters;
- preview reuses counts only when design, target format, normalized depth range, source signature and calculation/presentation revisions match;
- stale and legacy snapshots are ignored without breaking the export form;
- completion writes the signature from the exact request/design context that produced the artifact.

Validation:
- syntax compilation for report designer and Streamlit application;
- focused report designer, structure-preview, export and Streamlit integration tests pass;
- `logs/app.log` is not present in the supplied archive.

Next priority: add timestamp/source metadata to the count snapshot, then implement PDF page thumbnails.

## Persisted report preview counts
The last successful report's compact count snapshot is now stored at
`data/projects/<project_id>/report_preview_counts.json` through
`ReportPreviewCountsRepository`. The repository performs atomic writes and only
accepts a valid schema snapshot. Streamlit restores the raw snapshot once per
project/session; `resolve_report_document_counts_snapshot()` still performs the
context-signature check before the counts affect page estimates. Resetting the
export wizard deletes both session and project-persisted preview metadata.

# Latest implementation — Report Preview Persistence Recovery

Status: COMPLETED

Implemented:
- durable primary/backup storage for compact report-preview count snapshots;
- automatic fallback to the previous valid snapshot after primary corruption;
- damaged files are renamed with a `.corrupt-<UTC timestamp>` suffix;
- unrecoverable metadata is ignored safely and the UI falls back to heuristic page estimates;
- recovery is visible in Streamlit and recorded in application logs;
- repository API remains backward compatible through `load()` while exposing `load_with_recovery()` diagnostics.

Next priority: bounded quarantine retention and storage-health reporting.

# Latest implementation — Report Preview Storage Health Diagnostics

Status: COMPLETED

Implemented:
- read-only `storage_health(project_id)` inspection for preview metadata;
- primary/backup existence and schema validity reporting;
- quarantine count, quarantine bytes and total storage usage;
- explicit healthy/recoverable/degraded/quarantined/empty states;
- Streamlit diagnostics expander without triggering recovery or mutation;
- focused repository and UI integration coverage.

Next priority: PDF page-thumbnail preview, then an explicit quarantine-cleanup control in diagnostics.

## Repository hygiene rule

Keep all plans, handoff notes, roadmaps, and progress documents in `docs/`. Do not create additional Markdown planning files at repository root. The checked-in `data/` tree must contain only bootstrap placeholders and an empty recent-projects registry; never bundle a developer's local project state.

## PDF Preview foundation

- Added bounded raster preview generation for already-rendered PDF artifacts.
- The service prefers PyMuPDF and falls back to local `pdftoppm`.
- Preview rendering is limited to 1–12 pages and 72–180 DPI.
- Temporary source and page files are isolated outside project `data/` and removed automatically.
- Next step: connect the service to the Report Designer UI and cache previews by report signature.


## Latest increment: PDF Preview UI integration

The Professional Export panel now imports `reports.pdf_preview` and renders on-demand thumbnails only for a completed PDF whose request signature still matches the current controls. Cache key: `presentation_pdf_preview_<project_id>`. The cached payload stores `{signature, result}` and is invalidated on export completion and settings reset. Do not create planning Markdown files in the repository root; keep them under `docs/`.

## Latest increment: PDF Preview compact layout and metrics

The PDF preview UI now supports one-column and two-column layouts. `PdfPreviewResult` carries render duration, source byte size, total PNG byte size and computed average page size. Keep the layout outside the preview signature because it does not change raster output. All planning documentation remains under `docs/`.

## Latest increment: selective PDF page range and cache cleanup

`build_pdf_preview()` and `build_pdf_preview_signature()` now accept `start_page`. The value is normalized to at least page 1 and is included in the cache digest. Both raster backends render a bounded range and return actual PDF page numbers. The Streamlit Professional Export panel contains the `С первой страницы` control and the explicit `Очистить кэш предпросмотра` action. Cache cleanup removes only `presentation_pdf_preview_<project_id>` from application state and does not touch the exported PDF or project data. Keep all planning documentation under `docs/`.

## Latest increment: PDF Preview navigation and bounded DPI

The PDF preview panel now exposes `← Предыдущие` and `Следующие →` controls. Navigation advances by the currently selected page limit and is clamped through `shift_pdf_preview_window()`. Raster quality is selected from 72/90/110/144/180 DPI; the chosen DPI is passed to both `build_pdf_preview_signature()` and `build_pdf_preview()`. Keep all planning documentation under `docs/` and do not add Markdown files at repository root.

## Latest increment: PDF Preview direct page-jump validation

Implemented `PdfPreviewPageJumpValidation` and `validate_pdf_preview_page_jump()` in `reports/pdf_preview.py`. The Professional Export UI resolves a normalized `effective_preview_start` after the exact page count becomes known, displays adjustment feedback, and uses the normalized value for signature generation, rendering, and previous/next navigation. Keep all project documentation under `docs/`; do not add new root-level Markdown files.

## Последнее исправление: Professional Export runtime

Критический сбой `UnboundLocalError: print_top` устранён: блок предпросмотра структуры перенесён после вычисления интервала печати. Для keyed-виджетов значения по умолчанию передаются только при отсутствии ключа в Session State. Не возвращать построение preview signature выше блока `print_mode`.

## Workbench runtime-state deepcopy fix

`core/workbench_dispatcher.py` uses a per-key rollback snapshot. Do not restore the former `deepcopy(dict(self.state))`: Streamlit state may contain live background-export services backed by `ThreadPoolExecutor`/`queue.SimpleQueue`, which are not pickleable. Copyable values retain deep rollback semantics; runtime services are preserved by reference.

## Runtime service registry

Live services now belong in `core.runtime_service_registry.RuntimeServiceRegistry`, accessed through `ApplicationStateController.ensure_runtime_service()`. Do not place `ThreadPoolExecutor`, queue, lock, manager or mutable runtime-cache instances directly under normal Session State keys. The registry itself is stored under `runtime::services` and is intentionally preserved by reference during Workbench rollback. Ordinary project and UI data must continue to use `get_value()`/`set_value()` and remains deeply copyable. Keep all planning and handoff Markdown files under `docs/`.

## Runtime service lifecycle shutdown

`RuntimeServiceRegistry.shutdown()` is now the canonical cleanup boundary for process-local services. It invokes `close()` when available, otherwise `shutdown(wait=False)` (falling back to `shutdown()` for incompatible signatures), records a serializable `RuntimeServiceShutdownResult`, and continues after individual cleanup failures. `ApplicationStateController.shutdown_runtime_services()` exposes this boundary, and `WorkbenchLifecycleManager.close_workspace()` invokes it before marking the workspace closed. Do not reintroduce direct executor/cache shutdown calls into shell state code; register new live services and let the lifecycle boundary own their disposal.

## Runtime shutdown telemetry and registry disposal

`WorkbenchLifecycleManager.close_workspace()` now publishes `workbench.runtime_services.shutdown` with a serializable aggregate produced by `summarize_runtime_service_shutdown()`. The payload contains totals and failure diagnostics only; never place service instances, executors, queues or locks in event history. `ApplicationStateController.shutdown_runtime_services(remove=True)` also detaches the disposed `runtime::services` registry from state, so future runtime access receives a fresh registry. Keep cleanup best-effort and preserve lifecycle completion even when an individual service fails to close.

## Latest increment: bounded PDF adjacent-range prefetch

The Professional Export PDF preview now supports an opt-in "Предзагрузить следующую группу страниц" action. The current range is rendered first; when the exact page count shows that another range exists, only the immediately adjacent bounded group is rendered and cached. The Session State cache is newest-first and limited to three entries. Use `resolve_pdf_preview_cache()` and `store_pdf_preview_cache()` rather than reading `signature`/`result` directly because both legacy and multi-entry payloads are supported.

Validation completed:
- `python -m py_compile reports/pdf_preview.py app/streamlit_app.py`;
- focused PDF Preview tests: 23 passed;
- report/export regression selection: 89 passed.

## Latest increment: PDF Preview cache/prefetch telemetry

`reports.pdf_preview.inspect_pdf_preview_cache()` returns a compact `PdfPreviewCacheLookup` with result, hit flag, source (`legacy`, `entries`, `miss`) and bounded entry index. The Professional Export UI logs `pdf_preview_cache_lookup`, `pdf_preview_prefetched`, and `pdf_preview_prefetch_cache_hit` events. No PDF or PNG bytes are included in telemetry. Acceptance coverage uses a generated 24-page PDF and verifies reuse of pages 6–10 from the bounded cache.

## Latest increment: PDF Preview cache memory diagnostics

The PDF preview cache now exposes `summarize_pdf_preview_cache()` and `PdfPreviewCacheStats`. The UI can optionally show range count, rendered page count, aggregate PNG bytes, largest entry and pressure status. Diagnostics inspect metadata only and do not duplicate PDF or PNG bytes. Keep all future planning documents under `docs/`; do not create Markdown planning files at repository root.

## Latest increment: PDF Preview cache memory budget

The PDF thumbnail cache is now bounded by both number of ranges and total PNG bytes. Use `store_pdf_preview_cache_with_diagnostics()` when UI or telemetry needs eviction details. The compatibility wrapper `store_pdf_preview_cache()` still returns only the payload. The newest range is never evicted during the same insertion, even when it exceeds the selected budget. All new documentation remains under `docs/`; do not add Markdown files to the repository root except `README.md`.

## Interpretation interval repository foundation

Implemented the first interpretation-module increment in `projects/interpretation_intervals.py`.

- Storage hierarchy: `data/projects/<project_id>/wells/<well_id>/interpretations/<interpretation_id>/intervals.json`.
- Every manually managed interval has a stable UUID.
- The serializable model contains label, top/base, type, color, comment, source and timestamps.
- Thickness and middle depth are derived properties and are not duplicated in persisted state.
- CRUD operations use validation and atomic JSON replacement.
- This repository is intentionally separate from the existing automatic hydrocarbon and pay-zone interval engines; later UI integration may import or reference their results without changing their models.
- Runtime services and UI objects must not be attached to `InterpretationInterval` or `InterpretationIntervalSet`.

Validation: focused interpretation repository tests plus the existing professional well-interval manager tests pass (11 tests).

Next priority: add a service/command layer with undo/redo snapshots, then connect the interval manager UI to that layer.

## Latest increment: interpretation interval Undo/Redo

Use `projects.interpretation_interval_commands.InterpretationIntervalCommandService` for all future manual interval mutations from the UI. Its state contains only JSON-compatible snapshots, is isolated by project/well/interpretation and has a bounded history. Undo/Redo verifies that repository content still matches the expected command snapshot; an external change raises `InterpretationIntervalHistoryConflict` instead of overwriting data. Do not bypass this service from the future interval manager UI except for read-only loading.

Validation: repository, command history, professional interval manager and architecture freeze tests pass (19 tests).

## Latest increment: interpretation interval manager

`projects/interpretation_interval_manager.py` is now the preferred application-facing boundary for manual interval operations. It delegates persistence to the repository and reversible mutations to `InterpretationIntervalCommandService`. Overlap rejection is optional; do not change it to a mandatory repository rule without an explicit migration decision.

## Latest increment

The interpretation workspace now includes a thin Streamlit panel over the interval manager and properties service. UI code does not own persistence or business validation.

## Latest increment: interpretation interval export

Manual interpretation intervals now have a UI-independent export service and Streamlit download actions for JSON, CSV and Excel. The next recommended increment is tablet interaction synchronization: direct manual-interval selection, overlay visibility and hover/selection state coordination.

## Latest increment: interpretation interval import

Use `projects.interpretation_interval_imports` for parsing and applying manual interval imports. Parsing is UI-independent and supports versioned JSON exports, CSV and XLSX. Apply imports through `apply_interpretation_interval_import()` so append/upsert/replace changes are stored as one Undo/Redo-aware command. Do not loop through UI-level create/update calls for bulk imports because that fragments history. The next recommended increment is bidirectional selected-interval and hover synchronization between panel/table and tablet overlays.

## Latest increment: manual interval navigator

The interpretation workspace now renders a compact Plotly navigator after the manual interval panel. Selection events update `manual_interval_selected_<project>_<well>` using only the interval UUID, so the existing panel and tablet highlighting remain the source of truth. The helper lives in `ui/interpretation_interval_navigator.py` and is covered by `tests/test_interpretation_interval_navigator.py`.

# Latest implementation — Interpretation Interval Type Catalog

Status: COMPLETED

Implemented:
- project-scoped atomic JSON repository for interval types;
- default geological type presets;
- Streamlit management UI for create/update/delete/reset;
- catalog-backed type selection in interval create/edit forms;
- backward compatibility for intervals whose type is not present in the catalog.

Validation:
- syntax compilation passed;
- 34 focused interpretation interval tests passed.

Next priority: batch operations for manual intervals or direct selection on the engineering tablet interval track.

## Latest interpretation increment: reassignment confirmation

Project-wide interval type reassignment now requires an explicit UI confirmation and a current preview confirmation token. The token covers the project type catalog and all persisted interval files. Pass `expected_confirmation_token` to `reassign()` or `reassign_and_delete()` when applying a preview-backed operation; stale tokens fail before any mutation.

## Latest interpretation increment: project type reassignment undo

`InterpretationIntervalTypeRepository.undo_last_reassignment()` restores the catalog and only the interval files affected by the latest `reassign_and_delete` operation. The restore is rejected when any tracked file differs from the sealed post-operation checksum. Backups are stored under the project directory and removed after a successful undo; operation journal entries retain only serializable metadata.

## Interpretation interval type journal pagination

`InterpretationIntervalTypeRepository.list_operations()` now accepts a non-negative `offset` after filtering and newest-first ordering. `count_operations()` returns the filtered total for UI pagination, while `get_operation()` resolves a stable journal UUID. The Streamlit journal shows 10/25/50 rows per page and a serializable detail card; no Streamlit event or repository object is stored in project state.

## Batch interval workflow

- Групповые изменения типа, цвета, комментария, источника и удаление выполняются через подтверждённый preview.
- Preview содержит SHA-256 токен состояния выбранных интервалов и параметров операции.
- Устаревший preview блокируется до записи данных.
- Подтверждённые операции сохраняются в ограниченном сериализуемом журнале Session State.
- Каждая пакетная операция остаётся одним шагом Undo/Redo.


## Latest interpretation increment: version comparison and transfer

Use `projects.interpretation_interval_comparison` for UUID-based diff and transfer between interpretation workspaces of the same well. `compare_interpretation_intervals()` reports added, removed, modified and unchanged intervals while ignoring timestamps. `InterpretationIntervalTransferService` requires a fresh preview token, supports overwrite/skip/copy conflict policies, optional overlap rejection, and writes the target workspace through `InterpretationIntervalManager.replace_all()` as one Undo/Redo command. Do not transfer by directly writing `intervals.json` from UI code.

### Latest interpretation increment
Three-way manual interval merge is implemented in `projects/interpretation_interval_merge.py` and integrated into `ui/interpretation_interval_panel.py`. It requires three distinct interpretations, applies non-conflicting source changes automatically, supports source/target/skip conflict policies, stale-preview protection, optional overlap rejection and one-step target Undo/Redo.

### Latest increment: interpretation revisions

`projects/interpretation_revisions.py` provides persistent snapshots for one manual interpretation workspace. Revisions are stored under the interpretation `.revisions/` directory and are excluded from their own snapshots. Restore requires the state token returned by `compare()` and rolls back on write failure. Duplicating an interpretation copies current workspace data but not revision history.

## Latest increment: interpretation publication workflow

Interpretation workspaces now have persistent draft/review/approved/published states. Approved and published workspaces are read-only through `InterpretationIntervalManager`. Publication requires a revision whose state token matches current interpretation content. Workflow metadata lives under `.workflow/` and is excluded from revision snapshots and duplicated workspaces.

## Latest increment: role-aware interpretation publication

The publication workflow now uses `InterpretationActor` and a centralized role policy. Authors submit drafts, reviewers return/approve, publishers publish/unpublish, and administrators may perform all transitions. Workflow events persist actor identity and role and can be exported to JSON, CSV or XLSX. No runtime authentication objects are stored in project state; a future identity provider should create the same serializable actor value.

## Current correlation stage

The project now contains `projects/interpretation_correlation.py` and `ui/interpretation_correlation_panel.py`.
Correlation inputs must come from published interpretation revisions. Correlation ties reference stable interval UUIDs and explicit anchor depths. The next recommended increment is a visual multi-well correlation canvas; do not bypass publication or copy mutable runtime objects into correlation state.

## Latest correlation increment: visual tablet

Use `projects.interpretation_correlation_chart.py` to build the multi-well visual model, Plotly figure and standalone SVG export. The chart resolves exact published revisions pinned by ties and rejects mixed revisions for the same well. UI controls are rendering-only and must not be persisted inside `CorrelationWorkspace`. The next recommended correlation stage is quality diagnostics and confidence scoring for ties.

## Latest increment: editable correlation workflow

The multi-well correlation workspace now supports validated tie editing, individual line styles, grouped deletion, serializable Undo/Redo and a persistent bounded operation journal. Published interpretation revisions remain immutable inputs. The next large stage should focus on correlation quality metrics and assisted tie suggestions rather than further storage infrastructure.

## Latest correlation increment

The multi-well correlation workspace now includes a renderer-neutral quality analyzer in `projects/interpretation_correlation_quality.py`. It reports unavailable published endpoints, duplicate endpoint pairs, crossing visible ties and isolated wells, calculates a bounded score, and exports JSON/CSV reports. The Streamlit panel only renders the serializable analysis result; no Plotly or runtime object is persisted.

## Automatic correlation candidate boundary

`projects/interpretation_correlation_suggestions.py` is a renderer-neutral deterministic suggestion service. It never mutates published inputs or the workspace. Preview payloads are serializable and contain both workspace and source tokens. Confirmation must call `validate_suggestion_preview()` immediately before `CorrelationWorkspaceCommandService.add_ties()`. Batch acceptance is one Undo/Redo command. Do not persist ML/runtime models in the correlation workspace.

### Latest correlation increment

Automatic tie suggestions are configurable through `CorrelationSuggestionSettings`. Project-scoped profiles
are stored under `correlations/suggestion_profiles.json`; accepted suggestion batches are audited per
workspace in `suggestion_acceptance.json`. UI supports baseline/current scenario comparison. Do not place
runtime Plotly or Streamlit objects in these files or Session State snapshots.

## Phase 2 lifecycle rule

Session State keys should be registered through `core/session_key_registry.py` ownership rules. New live services must be registered in `RuntimeServiceRegistry` with the narrowest valid scope (`session`, `project`, `well`, `las`, or `workspace`). Context cleanup may close scoped services, so session-wide metrics and diagnostics must remain `session` scoped.

## Phase 2 performance regression gate

Use `scripts/run_performance_regression.py` to compare a committed or release baseline with a new Diagnostics Center export. The gate is metadata-only and must never serialize Plotly figures, DataFrames, executors or repository payloads. Default policy allows 25%/250 ms stage growth, 10 percentage-point cache hit-rate loss and 20 additional Session State keys. Tune thresholds explicitly in CI rather than weakening runtime instrumentation.

## Phase 2 PDF Preview cache boundary

Heavy rendered PDF preview pages are owned by `PdfPreviewRuntimeCache`, registered in `RuntimeServiceRegistry` with project scope. Do not write `PdfPreviewResult` or PNG page bytes into ordinary Session State. UI code may retain only scalar widget settings and must use the runtime cache snapshot for diagnostics. Legacy `presentation_pdf_preview_<project>` payloads are migrated once and removed immediately.

### Phase 2 startup diagnostics

`core/startup_diagnostics.py` owns process-local startup timing history. The service is registered under `startup_diagnostics` with session scope. Do not move timers, module objects or callables into serializable state. Startup budgets are diagnostic thresholds, not functional timeouts.

### Route lifecycle contract
Use `core.workbench_route_lifecycle.route_scope(route_id)` for runtime services that belong only
to one Workbench route. The session-scoped `WorkbenchRouteLifecycle` disposes the previous route
scope on navigation changes and returns only serializable diagnostics.

### Phase 2 navigation-cache note

Workbench project navigation is cached by `ProjectNavigationRuntimeCache` in the runtime registry under `project_navigation_runtime_cache` with session scope. Cached values are primitive serialized rows only. Freshness comes from `project_navigation_token`; do not place repository objects or Streamlit values in this cache. Explicit repository invalidation hooks remain the next step.

## Repository transaction recovery

`core/repository_io.py` now owns durable multi-file transaction recovery. Transaction journals are stored temporarily under `.repository_transactions/` at the common transaction root and are removed after commit or successful recovery. Do not place business data in this directory and do not copy it into interpretation revisions.

## Phase 2 repository health contract

- `core/repository_health.py` performs bounded read-only scans by default.
- Invalid JSON and stale temporary files produce serializable issues and repair actions.
- Repair actions only quarantine files, require an explicit action ID and revalidate the
  file metadata token before applying.
- `scripts/repository_health_check.py` returns exit code 2 when errors are detected.
- Developer Diagnostics reads the project-scoped `repository_health_service`; no file
  payloads are stored in Session State.
