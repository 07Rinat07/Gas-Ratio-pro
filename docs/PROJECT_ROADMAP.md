
### M3-S01.5 — Plot Header Separation & Cache Invalidation — завершено

- [x] Легенды depth-графиков перенесены ниже области построения.
- [x] Дублирующая легенда планшета скрыта.
- [x] Заголовки дорожек и заголовок планшета разведены.
- [x] Pixler/Ternary annotations перемещены внутрь карточки графика.
- [x] Экспортный кэш инвалидируется при смене версии приложения.

- [x] M3-S01.4: collision-free screen headers and grouped print tablets (v222.62).

## M3-S01.2 — Track Layout Engine Foundation — завершено

- [x] Семантические ширины дорожек.
- [x] Профили `screen` / `print`.
- [x] Адаптивная типографика заголовков.
- [x] Регрессионные тесты компоновки.
- [ ] Автоматическое разбиение плотного планшета на группы.
- [ ] Пользовательское изменение порядка и ширины треков.
- [ ] Сохранение layout-шаблонов в проекте.

# Current milestone — v222.55 Stabilization & Hardening

- [x] Fix Workbench project-menu `application_service_container` scope defect.
- [x] Introduce a centralized UI-neutral Workbench error-boundary contract.
- [x] Approve ADR-001 for a framework-independent UI Platform.
- [x] Add Platform, Engineering and UI/UX roadmaps.
- [x] Add API stability, production readiness and technical-debt policies.
- [ ] Complete route/language smoke regression and performance audit in v222.56.
- [ ] Complete production-readiness release audit in v222.57.

# Latest increment — Interpretation export project-root bugfix (v222.42)

- [x] Remove undefined `PROJECTS_ROOT` usage from the professional export fragment.
- [x] Use the shared Workbench project repository root for PDF preview and background export services.
- [x] Add regression coverage for the Interpretation export fragment and primary route declarations.
- [ ] Continue production Data Workspace import preview integration after the stability patch.

# Open Standards and Legal Research Governance

This roadmap is governed by `OPEN_STANDARDS_POLICY.md`, `LICENSE_POLICY.md`, and `RESEARCH_POLICY.md`. External code or data enters the project only after source, license, adapter isolation, security, testing, and ru/kk/en documentation review.


# Latest increment — DLIS/LIS79 and SEG-Y Metadata Adapter Foundation (v222.40)

Status: IMPLEMENTED / MANDATORY POLICY

- [x] Adopted an official open-standards and interoperability policy.
- [x] Adopted a third-party license policy and external research workflow.
- [x] Added a machine-readable third-party component evaluation registry.
- [x] Added synchronized ru/kk/en user guidance for supported formats and lawful external sources.
- [x] Added synchronized ru/kk/en developer guidance for integrating standards and libraries.
- [x] Added release tests for required policy files, documentation parity and registry structure.

All future LAS, DLIS/LIS79, SEG-Y, GIS, RESQML/GRDECL, HDF5/NetCDF, 3D and modeling integrations must pass this governance gate before adoption.
# Latest increment — Production LAS Dataset workflow (v222.28)

- [x] Register production LAS Viewer opens in Data Platform.
- [x] Maintain a project-scoped SQLite metadata projection while JSON manifests remain authoritative.
- [x] Return stable LAS validation codes and localized `ru/kk/en` import summaries.
- [x] Preserve explicit LAS 1.x and pre-2.0 compatibility metadata.
- [x] Detect legacy `WRAP=YES` and bounded-header anomalies.
- [ ] Render localized import summaries in every LAS upload entry point.
- [ ] Rebuild/reconcile SQLite projection from manifests.
- [ ] Add legacy encoding, delimiter and column-count validation.

# Latest increment — Legacy LAS compatibility foundation

Status: IMPLEMENTED / EXPANSION PLANNED

Required product capability:
- support LAS files older than 2.0, including LAS 1.x archive files;
- use a dedicated tolerant compatibility mode instead of rejecting old files;
- preserve original source bytes, mnemonics, units and headers;
- emit stable machine-readable warnings for legacy or malformed structures;
- separate safe heuristics from strict validation;
- never silently rewrite an old LAS during import;
- provide explicit user-visible compatibility reports in Russian, Kazakh and English.

Implemented in v222.27:
- `legacy-pre-2.0` classification for parseable LAS versions below 2.0;
- `legacy-tolerant` classification for recognizable LAS files without a usable `VERS` value;
- stable warning codes and bounded header-only detection;
- regression tests for LAS 1.2 and missing-version archival files.

Next priority:
- legacy WRAP and delimiter diagnostics;
- old encoding detection;
- malformed card recovery;
- localized import outcome and compatibility report;
- production import-workflow integration.

# Latest increment — Data Platform Foundation II

Status: IMPLEMENTED

Implemented:
- project-scoped SHA-256 duplicate discovery;
- immutable sequential Dataset lineage;
- collision-safe source artifact retention;
- generic metadata-scanner protocol;
- bounded LAS header-only metadata scanner;
- payload-free registration and scanner diagnostics.

Validation:
- focused Data Platform and application-service container tests;
- Python compilation for all changed modules.

Next priority: localized import outcomes, stable LAS validation codes and SQLite metadata catalog projection.

# Latest increment — Data Platform Foundation I

Status: IMPLEMENTED

Implemented:
- lightweight Data Format Registry with collision-safe ids/extensions;
- versioned Dataset Manifest and provenance contracts;
- streaming SHA-256 checksums;
- project-contained Artifact Store with atomic writes and path traversal protection;
- atomic Dataset Manifest Repository with JSON-safe diagnostics;
- lazy Data Platform Application Service in the application-service container;
- initial contracts for LAS, DLIS, SEG-Y, RESQML, GRDECL, GIS, HDF5/NetCDF, CSV/Excel and PDF/DOCX.

Validation:
- focused Data Platform and application-service container tests;
- Python compilation for all new modules.

Next priority: duplicate detection, immutable dataset version lineage and the metadata-scanner adapter contract, starting with LAS header-only scanning.

See: `docs/INDUSTRY_DATA_PLATFORM_ROADMAP.md`.

# Latest increment — Three-language Internationalization Foundation

Status: IMPLEMENTED / MIGRATION STARTED

Implemented:
- approved Russian (`ru`), Kazakh (`kk`) and English (`en`) as first-class product languages;
- defined separate localization scope for UI, instructions, reports and user-facing diagnostics;
- added an allow-listed language registry and deterministic Russian fallback;
- added safe JSON catalog loading and named-placeholder formatting;
- added catalog completeness diagnostics and a lazy application-service boundary;
- documented terminology governance, report-language separation and phased UI migration.

Validation target:
- aligned UTF-8 catalogs for all three languages;
- safe fallback and parameter handling;
- JSON-serializable health snapshot;
- application-service reuse without storing live services in session state.

Next priority: add persisted user-language preference and migrate the Dashboard/Workbench shell before implementing Data Format Registry UI.

See: `docs/INTERNATIONALIZATION_ROADMAP.md`.

# Latest increment — Industry Data Platform Plan + Global Navigation Byte Budget

Status: IMPLEMENTED / STRATEGIC PLAN UPDATED

Implemented:
- approved a staged industry-data roadmap for DLIS, SEG-Y 2.1, GIS, HDF5/NetCDF, GRDECL and RESQML 2.2;
- separated open exchange standards from proprietary vendor project access;
- defined metadata catalog, artifact store, provenance, CRS/units and chunked-I/O foundations;
- defined versioned KZ/RU regulatory report profiles instead of hard-coded forms;
- added a global estimated-byte budget to Project Navigation Runtime Cache;
- added LRU byte eviction and rejection of a single oversized navigation profile;
- exposed payload-free budget utilization, byte eviction and oversized rejection diagnostics.

Validation target:
- focused navigation-cache, Workbench route, repository invalidation and Diagnostics Center tests;
- Python compilation and JSON-serializable diagnostics.

Next priority: implement the Data Format Registry and Dataset Manifest contracts without adding heavy parser dependencies yet.

See: `docs/INDUSTRY_DATA_PLATFORM_ROADMAP.md`.

# Latest increment — Lazy Active Project Resolution

Status: COMPLETED

Implemented:
- single-record fast path for resolving the active Workbench project;
- eliminated full `project.json` enumeration on normal route reruns;
- fallback enumeration only when the requested project is missing, malformed or invalid;
- active-project recovery remains synchronized with application state;
- focused regression coverage for fast-path, missing-record and malformed-JSON recovery.

Validation:
- `python -m py_compile services/project_manager_service.py app/streamlit_app.py`;
- `78 passed` in focused Project Manager, Workbench route, entry-point, diagnostics and Dashboard tests.

Next priority: use route-data timings to isolate the next repository-heavy operation, with project-navigation metadata scanning as the leading candidate for finer-grained lazy loading.

# Latest increment — Project Open Stage Profiling

Status: COMPLETED

Implemented:
- payload-free project-opening diagnostics at the Workbench command boundary;
- separate timing for project metadata load, recent-project update, workspace opening and Dashboard navigation;
- bounded session-local history with an explicit slow-opening budget;
- Diagnostics Center exposure without retaining ProjectRecord, DataFrame or Streamlit objects;
- focused regression coverage for bounded retention and command integration.

Validation:
- `python -m py_compile core/project_open_diagnostics.py core/workbench_entry_points.py core/diagnostics_center.py`;
- `10 passed` in focused Workbench entry, route-data and diagnostics tests.

Next priority: use the new stage profile to identify remaining eager project-data reads and move the first confirmed heavy read behind a lazy application-service boundary.

# Latest increment — Project loading and DataFrame memory hardening

Status: COMPLETED

Implemented:
- project-scoped DataFrame runtime cache lifecycle;
- strict 64 MiB default cache budget plus entry-count limit;
- LRU eviction based on deep DataFrame memory usage;
- non-retention of single samples larger than the configured budget;
- payload-free memory diagnostics in Developer Diagnostics.

Next priority: profile project opening and move remaining eager project-data reads behind lazy repository boundaries.

# Latest increment — Bounded Report Preview Quarantine Maintenance

Status: COMPLETED

Implemented:
- bounded retention for quarantined report-preview snapshot files;
- deterministic newest-first quarantine discovery per project;
- automatic pruning during normal load and recovery paths;
- explicit project-scoped quarantine purge API;
- full reset now removes primary, backup and quarantined preview metadata;
- regression coverage for retention limits, disabled retention and project isolation.

Validation:
- `python -m py_compile reports/report_preview_persistence.py reports/report_designer.py app/streamlit_app.py`;
- `104 passed` in focused Report Designer, Export Wizard and Background Export tests;
- `logs/app.log` is not present in the supplied project archive.

Next priority: expose non-sensitive persistence health metrics in diagnostics and add migration support for future snapshot schema revisions.

# Latest increment — Report Preview Snapshot Validation Diagnostics

Status: COMPLETED

Implemented:
- schema-versioned persistence for actual EngineeringDocument block counts;
- explicit snapshot states: missing, current, stale, legacy, unsupported and invalid;
- safe normalization of persisted numeric counters;
- visible Streamlit diagnostics when saved counts cannot be reused;
- generated-at metadata for the current factual-count snapshot;
- backward-safe rejection of legacy and malformed session payloads.

Validation:
- `python -m py_compile reports/report_designer.py app/streamlit_app.py`;
- `78 passed` in focused Report Designer, Export Wizard and Background Export tests;
- `logs/app.log` is not present in the supplied project archive.

Next priority: persist the validated counts snapshot outside process-local session state so it can survive application restarts without storing EngineeringDocument payloads.

# Latest increment — Renderer Capability Diagnostics

Status: COMPLETED

Implemented:
- renderer-neutral capability profiles for PDF, DOCX, ZIP bundle, PNG, SVG and XLSX;
- explicit support state for pagination, table of contents, bookmarks and editable content;
- bundle-specific notice that outline bookmarks apply only to the PDF member;
- specialized-export diagnostics for PNG/SVG/XLSX where report pagination settings do not apply;
- safe warning for unknown future formats;
- Streamlit capability panel in the live report-structure preview.

Validation:
- `python -m py_compile reports/report_designer.py app/streamlit_app.py`;
- `52 passed` in focused Report Designer, Export Wizard and presentation UI tests.

Next priority: connect the preview to the preflight-built EngineeringDocument so live block counts appear after document assembly without duplicate engineering calculations.

# Latest increment — Document-Model Page Estimate Refinement and Format Readiness



Status: COMPLETED



Implemented:

- optional refinement of page estimates from an already assembled EngineeringDocument;

- renderer-neutral counts for sections, tables, table rows, plots, visualization previews and notices;

- PDF-specific readiness warning when page chrome is disabled;

- DOCX-specific readiness warning when PDF bookmarks cannot be applied;

- Streamlit preview now passes the selected target format into readiness diagnostics;

- backward-compatible fallback to heuristic estimates when no document model is available.



Validation:

- `python -m py_compile reports/report_designer.py app/streamlit_app.py`;

- `34 passed` in focused report designer/export wizard regression tests.



Next priority: expose live document-model counts after preflight assembly and add renderer capability diagnostics for bundle/PNG/SVG/XLSX exports.



# Latest increment — Report Structure Page Estimate and Export Readiness

Status: COMPLETED

Implemented:
- renderer-neutral page composition estimates for cover, TOC, report sections and technical appendix;
- min/max page range without rendering plots, tables, PDF or DOCX binaries;
- export-readiness diagnostics for blocking configuration, disabled sections and large reports;
- Streamlit presentation of estimated volume and per-component page contribution;
- regression tests for standard, disabled-figure and blocked-design scenarios.

Validation:
- `python -m py_compile reports/report_designer.py app/streamlit_app.py`;
- focused report preview and export integration tests.

Next priority: use real document-model counts to refine page estimates and add PDF/DOCX-specific readiness diagnostics.

# Latest increment — Background Export Runtime Performance Summary

Status: COMPLETED

Implemented:
- project-scoped runtime summary for the five most recent background export jobs;
- total and active job counters;
- terminal-job success rate;
- average terminal duration and average completed artifact size;
- explicit failed/cancelled/orphaned counters;
- renderer-neutral aggregation based only on persisted snapshot metadata;
- focused unit and Streamlit integration coverage.

Validation:
- `python -m py_compile reports/background_export.py reports/background_export_ui.py app/streamlit_app.py`;
- `37 passed` in the focused background-export regression set;
- `logs/app.log` is not present in the supplied project archive.

Next priority: extend the report-structure preview with estimated page composition and export-readiness diagnostics.

# Latest increment — Automatic Background Export Polling and Cooperative Renderer Cancellation

Status: COMPLETED

Implemented:
- Professional Export fragment now refreshes automatically every two seconds;
- manual progress refresh is no longer required while a background job is active;
- Report Designer PDF, DOCX and bundle renderers expose progress and cancellation callbacks;
- cancellation checkpoints run while report sections and blocks are assembled;
- bundle export reports separate PDF, DOCX and packaging phases;
- synchronous callers remain backward compatible because callbacks are optional.

Next priority: field acceptance of cancellation with large real-world PDF/DOCX reports and timeout/slow-job diagnostics.

# Latest increment — Streamlit Background Export Integration

Status: COMPLETED

Implemented:
- Professional Export submits long-running renders to BackgroundExportManager;
- progress and cancellation are surfaced in the isolated Streamlit export panel;
- completed artifacts are handed back to the bounded download cache and export history on the UI thread;
- worker code does not call Streamlit rendering APIs;
- duplicate requests remain blocked by project and request signature.

Next priority: automatic fragment polling while a job is active and field validation of cancellation during large PDF/DOCX renders.

# Latest increment — Recoverable Background Export Foundation

Status: COMPLETED

Implemented:
- process-local background export queue with bounded metadata snapshots;
- monotonic progress reporting and cooperative cancellation checkpoints;
- duplicate active-request protection per project and request signature;
- interrupted jobs are recovered as orphaned after application restart;
- binary artifacts remain in the existing bounded cache and are never persisted in job metadata;
- ExportController exposes optional progress and cancellation callbacks without breaking synchronous callers.

Next priority: connect the background manager to the Streamlit Professional Export panel with polling, Cancel and result handoff.

# Latest increment — Confirmed Stale Export Rebuild

Status: COMPLETED

Implemented:
- stale history entries now open an explicit rebuild confirmation summary;
- confirmation shows file, format, profile, depth range, report mode and template;
- confirmed rebuild restores the historical configuration and automatically starts a fresh render;
- cancel leaves the active export configuration unchanged;
- current and legacy entries preserve the existing repeat behavior.

Next priority: add cancellable background export execution and progress recovery for long PDF/DOCX renders.

# Latest increment — Repeat Export Revision Preflight

Status: COMPLETED

Implemented:
- export history schema v3 stores a lightweight project-data revision fingerprint;
- repeat-export history compares the historical fingerprint with the active project revision;
- current, stale and legacy/unknown history entries are distinguished explicitly;
- stale configurations remain reusable but warn that a fresh render is required;
- legacy v1/v2 history remains readable with safe unknown-revision behavior.

Next priority: add an explicit one-click re-render action for stale history entries with a preflight confirmation summary.

# Latest increment — Full-Fidelity Repeat Export

Status: COMPLETED

Implemented:
- export history schema v2 stores report mode, template, title, sections, technical appendix, page chrome and print mode;
- repeat action restores the complete report-design configuration together with profile, format and depth range;
- legacy v1 history remains readable with safe defaults;
- history remains metadata-only, bounded and project-scoped.

Next priority: add repeat-export preflight comparison and warn when the current project data revision differs from the historical export.

## Current increment: Export History Filtering and Repeat Action — COMPLETED

Implemented:
- added renderer-neutral search, format and profile filters for successful export history;
- added a Repeat action that restores the previous profile, format and depth range;
- applies repeated settings through a pending state before Streamlit widgets are created;
- preserves project isolation and does not restore binaries or engineering payloads;
- added regression tests for filtering and Streamlit integration.

Next priority: persist the complete report-design configuration in future history entries for full-fidelity repeat export.

## Current increment: Export Draft Reset and Successful Export History — COMPLETED

Implemented:
- added an explicit project-scoped reset action for saved Export Wizard settings;
- added compact metadata-only history of successful exports;
- history stores format, profile, depth range, file name, size, timestamp and cache status;
- added bounded retention, atomic JSON writes, deduplication and project-boundary validation;
- added a separate history clear action without deleting engineering data or rendered files.

Next priority: history filtering and repeat-export action based on stored metadata.

## Current increment: Export Wizard Draft Persistence — COMPLETED

Implemented:
- added project-scoped persistence for unfinished Professional Export Wizard settings;
- restores profile, format, report mode, template, title, sections, print scope and depth range;
- uses schema-versioned JSON and atomic file replacement;
- excludes engineering dataframes, rendered binaries and credentials from persisted drafts;
- added corruption, cross-project and round-trip regression tests.

Next priority: explicit reset/clear-draft action and last successful export history.

## Current increment: Visual Export Wizard Review — COMPLETED

Implemented:
- added renderer-neutral step presentation for Source, Content, Format, Destination and Review;
- added a final human-readable export review model with preflight status and target file name;
- integrated the five-step review into the Streamlit professional export form;
- blocked export submission when the final preflight contains a blocking issue;
- added regression tests for completed, locked and invalid wizard paths.

Next: persist the Export Wizard draft per project and restore unfinished export settings safely.

## Current increment: Interactive Report Structure Preview — COMPLETED

Implemented:
- added a renderer-neutral report structure preview contract;
- preview resolves the same report mode and template settings as PDF/DOCX export;
- added live Streamlit review of section order, navigation, appendices and page chrome;
- preview validation runs without plots, tables or binary rendering;
- added regression tests for Brief, Standard and Custom configurations.

Next: complete the visual Export Wizard step navigation and final review screen.

## Current increment: Report Output Modes — COMPLETED

Implemented:
- added Brief, Standard and Full Engineering report modes;
- preserved manual template composition through the Custom mode;
- synchronized mode selection with Report Designer sections, figures, technical appendix and page chrome;
- included report mode in export cache invalidation;
- added regression tests for mode resolution and Streamlit integration.

Next: table of contents and PDF bookmarks.

## Current increment: Export Performance and Memory Guard — COMPLETED

Implemented:
- bounded professional export artifact cache by both entry count and retained bytes;
- prevented oversized PDF/DOCX/PNG artifacts from remaining in session memory;
- added lightweight cache metrics for diagnostics and performance audits;
- preserved existing model reuse, project-aware invalidation and LRU behavior.

Next: large-LAS rendering benchmarks and selective dataframe downsampling.

## Current increment: Unified Chart Theme Engine — COMPLETED

Implemented:
- added shared screen, print and presentation Plotly theme profiles;
- added one immutable visual contract for fonts, axes, grids, margins, lines and markers;
- added stable theme signatures for cache invalidation;
- preserved trace data, engineering semantics and axis ranges while applying themes;
- routed static export through the shared print-safe theme engine.

Next: performance optimization for large LAS visualization and export workloads.

## Current increment: Unified Tooltip and Operation Feedback Layer — COMPLETED

Implemented:
- added a framework-neutral tooltip registry for Professional Export controls;
- added validated operation progress contracts with monotonic stages;
- connected Report Designer controls to centralized help text;
- connected export preparation to the shared progress plan;
- added tooltip coverage and progress-sequence tests.

Next: extend tooltip coverage to remaining high-priority engineering controls and unify chart themes.

## Current increment: Professional Report Designer UI Integration — COMPLETED

Implemented:
- connected Engineering, Corporate and Minimal templates to the Streamlit export panel;
- added report title, section composition, technical appendix and page-chrome controls;
- routed PDF, DOCX and bundle exports through one designed EngineeringDocument;
- included design parameters in export cache invalidation;
- preserved PNG, SVG and XLSX specialized export channels.

Next: interactive report structure preview and unified tooltip/help layer.

## Current increment: v222.12 — Professional Report Visualization Renderer

Status: **STABLE BUGFIX CANDIDATE**

Implemented:
- dedicated print-oriented plot metadata shared by PDF and DOCX;
- readable curve legend with colour, mnemonic and engineering meaning;
- explicit fluid-zone legend and top/base/priority marker explanations;
- high-resolution report rendering with larger typography and line weights;
- one synchronized legend contract for client and engineering profiles.

## v222.9 — Interval-Focused Tablet and Visual Legends — COMPLETED

- focus the tablet on meaningful interpreted depth intervals;
- exclude empty and unclassified well sections from the default viewport;
- add clear curve names, colours and marker symbols above the plot;
- add fluid-class colours and top/base markers;
- preserve the full interval registry in reports and tables.

Next: frontend rendering optimization and field acceptance of the focused tablet.

## v222.5 — Streamlit Rerun Coordination — COMPLETED

- centralize full-app rerun requests;
- suppress duplicate reruns inside one render cycle;
- preserve named refresh reasons for diagnostics;
- keep Professional Export fragment isolated;
- verify navigation, export and render-queue regressions.

Next: field acceptance and targeted v222.5 performance fixes only.

## v222.3 — Engineering UX & Visibility Stabilization — COMPLETED

- strengthen screen curve and marker visibility;
- preserve Plotly viewport state across stable reruns;
- prevent hydrocarbon zones from obscuring analytical curves;
- improve tablet zone-label contrast;
- verify behavior with focused UI regression tests.

## v222.1 — Field Acceptance Bugfix Cycle

Current priority:
1. harden Professional Export state across LAS/range/profile changes;
2. preserve correct report cache invalidation for engineering context changes;
3. continue field acceptance and fix only confirmed runtime defects;
4. do not add new scientific methods before acceptance closure.

# GAS RATIO PRO — Active Roadmap

## v222 Stable — Final Regression and Packaging

Status: **COMPLETED**

Required gates:
1. Execute all 2048 tests in deterministic segments.
2. Resolve only confirmed regressions or stale release contracts.
3. Compile application, core, reports, projects and palettes.
4. Verify Professional Export first-run, format switching and cache reuse.
5. Verify Plot Cache memory limits, lazy workspace rendering and partial renderer recovery.
6. Preserve README.md unchanged.
7. Package a clean stable archive without caches, logs or virtual environments.

Next: field acceptance and targeted v222.1 bugfixes only. No new scientific methods are authorized before acceptance closure.

## v218 — Print & Export 2.0 (completed)

- Removed HTML as a user-download format from reports and calculation comparison.
- Unified PDF, DOCX, PNG, SVG and XLSX under one professional export workflow.
- Added one depth-range contract shared by document, image and spreadsheet exports.
- Kept active interval selection as the default export range.
- Cleaned export labels from renderer and implementation terminology.
- Next priority: Sprint 4 — Engineering Reports.


## v217 — Engineering Navigation (completed)

- Added searchable, filterable interval navigation to Data and Interpretation workspaces.
- Preserved one shared active interval across Pixler, ternary, depth panel, tablet, passport and export.
- Kept the active row visible and marked without previous/next buttons.
- Next priority: Sprint 3 — Print & Export 2.0.


## v216 — Graphics Recovery (completed)

- Unified depth-track titles, legends, margins and engineering hover labels.
- Removed renderer implementation terms from tablet track headers.
- Stabilized tablet fill rendering without exposing `fill`, `line` or scale-mode captions.
- Confirmed Pixler, ternary, depth-panel, tablet, print and export regression tests.
- Next priority: Sprint 2 — Engineering Navigation.


## v215 — Engineering UI cleanup (in progress)

- Removed the blocking previous/next interval buttons from Data and Interpretation workspaces.
- Added one synchronized interval selector with engineering labels.
- Removed user-visible PDF placeholders such as `+N колонок в HTML/DOCX`.
- Simplified tablet track titles by removing `auto`, `line` and internal scale-mode captions.
- Renamed the chart to `Интерпретационный планшет`.
- PDF and DOCX remain the primary report formats; HTML stays internal only.

# GAS RATIO PRO — Active Project Roadmap

Status: Active  
Baseline: v208  
Purpose: единственная активная последовательность реализации проекта.

## 1. Обязательные правила

- Работать только с последним подтверждённым архивом.
- UI не содержит бизнес-логику и инженерные вычисления.
- Не создавать боковые подсистемы вне активного этапа.
- Новый этап начинается только после Definition of Done текущего этапа.
- Каждый инкремент проходит: реализация → тесты → исправление → preflight → архив.
- Документация обновляется в существующих управляющих файлах; отдельные version-note документы по умолчанию не создаются.

## 2. Целевая архитектурная цепочка

```text
Source Adapter
→ Domain Model
→ Scene
→ Layout
→ Axis / Grid
→ Track
→ Curve Quality
→ Label / Legend
→ Print Layout
→ Render Model
→ Renderers
```

Поток данных продукта:

```text
LAS → Core → Interpretation → Presentation → UI / Reports
```

## 3. Активная последовательность работ

### Stage 1 — Visualization Engine completion

Status: **COMPLETED v179**

Цель: завершить графическое ядро и доказать одинаковую, печатно пригодную геометрию SVG/PDF.

Оставшиеся обязательные задачи:

1. Точечное исправление дефектов, обнаруживаемых Render Validation Pipeline.
2. Расширенная проверка коллизий легенд, осей и track headers.
3. Визуальная проверка эталонных multi-track сцен и фиксация ожидаемых артефактов. **COMPLETED v177**
4. Проверка Unicode и читаемости печати на эталонных экспортных файлах.
5. Финальный performance/large-LAS regression. **COMPLETED v179 — 1743 tests passed; preflight OK**

Definition of Done:

- validation pipeline не только сообщает ошибки, но предотвращает некорректный export;
- SVG и PDF используют один Render Model и одинаковую geometry signature;
- эталонные сцены проходят автоматическую и визуальную QA;
- большие LAS не приводят к неконтролируемому росту памяти;
- полный test suite и preflight проходят.

### Stage 2 — LAS Viewer completion

Status: **COMPLETED v186**

Цель: собрать уже реализованные viewport, cursor, selection, layout и render pipeline в законченный инженерный viewer.

Обязательные задачи:

1. Реальный LAS-open workflow через существующий импортёр. **COMPLETED v180**
2. Полноценное построение multi-track viewer из LAS curves. **COMPLETED v181**
3. Общие depth viewport, cursor и selection. **COMPLETED v182**
4. Track configuration: порядок, ширина, шкала, видимость. **COMPLETED v183**
5. Zoom, pan, fit, reset и стабильная работа на больших LAS. **COMPLETED v184**
6. Экспорт текущего вида в SVG/PDF через Visualization Engine. **COMPLETED v185**
7. Ошибки, пустые кривые, null intervals и invalid units. **COMPLETED v186**

Definition of Done:

- пользователь открывает LAS и получает рабочий viewer без ручной подготовки payload;
- интерактивность и экспорт используют одни контракты;
- состояние viewer восстанавливается без сохранения raw dataframe в UI session;
- viewer проходит функциональные, performance и export-тесты.

### Stage 3 — Modern Workbench and new main page

Status: **COMPLETED v193**

Цель: один раз выполнить полноценный редизайн после стабилизации графического ядра.

Обязательные задачи:

1. Workbench shell и navigation model. **COMPLETED v187**
2. Dock Manager и панели инструментов. **COMPLETED v188**
3. Command Framework и Event Bus integration. **COMPLETED v189**
4. LAS Viewer как основной рабочий модуль. **COMPLETED v190**
5. Project/recent-session entry points без дублирования навигации. **COMPLETED v191**
6. Полный responsive и accessibility audit. **COMPLETED v192**
7. Production entry-point integration: Modern Workbench по умолчанию, legacy UI только через явный process-level fallback. **COMPLETED v193**

Запрещено до Stage 3:

- косметически переделывать главную страницу;
- создавать второй параллельный UI workflow;
- переносить вычисления в UI.

### Stage 4W — Workbench Stabilization and Information Architecture

Status: **IN PROGRESS v214**

Цель: устранить ложные состояния, дублирующую навигацию и визуальный хаос до перехода к новому Well Log Renderer.

Обязательные задачи:

1. Разделить текущую рабочую сессию и архив проекта.
2. Не показывать предупреждения, integrity-check и экспорт архивного расчета без явного открытия пользователем.
3. Оставить один основной уровень навигации; ribbon использовать только для контекстных команд активного модуля.
4. Синхронизировать Project Explorer с реальными объектами и счетчиками проекта.
5. Добавить понятные empty states для проекта, LAS и расчетов.
6. Провести live visual acceptance на широком и обычном desktop-разрешении.

Definition of Done:

- пустая рабочая сессия не показывает ошибки и предупреждения архивных расчетов;
- архивные snapshots открываются только по явному действию;
- верхнее меню, Explorer и ribbon не дублируют одну и ту же навигацию;
- счетчики Explorer соответствуют проекту;
- центральная рабочая область визуально доминирует над служебными панелями.

### Stage 4 — Workbench UI Completion

Status: **IN PROGRESS v213 — live acceptance failed for professional visualization, reporting and runtime responsiveness; controlled refactor approved**

Цель: превратить подключённый production Workbench из минимального shell в полноценное инженерное рабочее окружение до подключения следующих domain-модулей.

Обязательные задачи:

1. Полноэкранный application layout без неиспользуемой центральной области. **COMPLETED v195**
2. Верхний command toolbar/ribbon, использующий существующий Command Framework. **COMPLETED v196**
3. Центральный workspace-host для LAS Viewer и последующих инженерных модулей. **COMPLETED v196**
4. Project Explorer слева с сериализуемым project-tree contract. **COMPLETED v196**
5. Context-sensitive Properties panel справа без domain-вычислений в UI. **COMPLETED v196**
6. Status bar: активный проект, скважина, LAS, viewport/scale и operational status. **COMPLETED v196**
7. Реальное размещение, collapse/restore и изменение размеров dock panes в поддерживаемых Streamlit границах. **COMPLETED v196**
8. Responsive, keyboard-navigation и accessibility regression для нового layout. **COMPLETED v197**
9. Smoke-проверка production startup и основных navigation/tool workflows. **AUTOMATED COMPLETE v197; LIVE ACCEPTANCE FAILED**
10. Runtime build/source identity visible in UI. **COMPLETED v198**
11. Launcher port ownership and stale-process protection. **COMPLETED v198**
12. Live acceptance on the owner environment with confirmed five-region layout. **COMPLETED v198**
13. Professional UX redesign: readable ribbon, balanced panels, dominant workspace, compact dock controls and visual hierarchy. **IMPLEMENTED v199; LIVE FIXES v200**
14. Production interaction acceptance: unobscured title bar, visible active navigation, deterministic command feedback, and state-aware dock commands. **COMPLETED v200**
15. Command-backed quick actions and visible workspace-context transitions in the empty production workspace. **COMPLETED v201**
16. Live visual acceptance of the redesigned Workbench. **COMPLETED v201**
17. Existing LAS import/analysis, LAS editor and LAS correlation screens embedded in the central Workbench host. **COMPLETED v202**
18. Existing interpretation graphs, printable reports, export archive and Documentation Center routed through the single Workbench navigation model. **COMPLETED v202**
19. Live functional acceptance: upload a LAS, edit/create LAS, view graphs, generate/download a report and open documentation. **FAILED IN v202 — modules changed navigation state but real workflows were not observable**
20. Workbench Module Integration Audit: for every route confirm command → state → renderer → provider → visible workflow → user result. **ACTIVE v203**
21. Centralized runtime diagnostics: correlation ID, rotating log traceback, compact incident state, command failure events and module-binding snapshot. **IMPLEMENTED v203**
22. Developer Diagnostics panel behind an explicit process flag; no diagnostics runtime objects in normal presentation state. **IMPLEMENTED v203**
23. Production acceptance gates for each route: module loaded, controls visible, input accepted, output visible/downloadable, no traceback. **REQUIRED BEFORE CLOSURE**
24. Browser form/accessibility findings: stable widget keys, labels and supported autocomplete semantics where Streamlit permits control. **PLANNED AFTER MODULE BINDING**
25. Arrow-safe UI tables: normalize mixed presentation columns before Streamlit serialization. **COMPLETED v204**
26. Streamlit API compatibility: replace deprecated raw HTML component usage and capture Streamlit/PyArrow warnings in the single rotating application log. **COMPLETED v205**
27. Module Render Audit: log route resolution, provider, renderer, start/completed/failed phase, duration and expected visible controls for every Workbench route. **COMPLETED v205**
28. Live module acceptance using render-audit evidence and visible controls for LAS, Interpretation, Reports, Exports and Documentation. **FAILED AFTER v205 OWNER TEST — renderers completed but controls were pushed below an empty fixed-height shell**
29. Functional visibility repair: remove the empty fixed-height HTML workspace shell so native Streamlit controls render immediately inside the central column. **COMPLETED v206**
30. Repeat live acceptance for LAS upload/editor/viewer, Interpretation, Reports, Exports and Documentation. **FAILED AFTER v206 OWNER TEST — dead menu/tree controls and missing Data Workspace blocked calculations**
31. Restore Data Workspace as a first-class Workbench route and replace decorative top-menu/Project Explorer entries with command-backed buttons. **COMPLETED v207**
32. Restore the end-to-end flow Data input → calculation → Interpretation → Reports, with an actionable Reports prerequisite state. **COMPLETED v207; LIVE ACCEPTANCE REQUIRED**
33. Replace silent File/Project labels with real project/session controls and move the single compact brand logo to the Workbench title bar; remove the duplicate Documentation logo overlay. **COMPLETED v208; LIVE ACCEPTANCE REQUIRED**

Definition of Done:

- после запуска пользователь получает заполненное инженерное рабочее пространство, а не список shell-кнопок;
- центральный workspace занимает доступную площадь и отображает активный модуль;
- Project Explorer, Properties, Toolbar и Status Bar используют только application/render contracts;
- LAS Viewer открывается внутри workspace-host;
- UI не содержит repository/file operations, инженерные вычисления или raw DataFrame;
- responsive/accessibility, Workbench regression и preflight проходят;
- каждая runtime-ошибка получает correlation ID и полный traceback в `logs/app.log`;
- route считается интегрированным только когда отображается и выполняется реальный пользовательский workflow, а не только меняется navigation state.

### Stage 4R — Engineering Presentation Refactor

Status: **ACTIVE — approved after v213 live review**

Цель: заменить накопившиеся patch-level решения в визуализации, корреляции и отчетности единым инженерным presentation pipeline без изменения проверенной расчетной логики.

#### 4R.1. Refactor boundaries

В рефакторинг входят только следующие подсистемы:

1. `WellLogRenderModel` и профессиональный multi-track планшет.
2. `CorrelationRenderModel` и синхронизированная multi-well визуализация.
3. `DiagnosticPlotModel` для Pixler и ternary.
4. `ReportDocumentModel` и независимые PDF/DOCX/HTML renderers.
5. Streamlit state/rerun boundary для тяжелых графиков и экспорта.
6. Interval consolidation и правила отбора интервалов для пользовательских отчетов.

В рефакторинг **не входят** новые петрофизические формулы, геомоделирование, 3D и новые domain-модули.

#### 4R.2. Architectural target

```text
CalculationResult
→ ValidatedInterpretationDataset
→ PresentationModels
   ├─ WellLogRenderModel
   ├─ CorrelationRenderModel
   ├─ PixlerModel
   ├─ TernaryModel
   └─ ReportDocumentModel
→ Independent Renderers
   ├─ Interactive Plotly/Streamlit
   ├─ Static SVG/PNG
   ├─ PDF
   ├─ DOCX
   └─ HTML
```

Требования:

- UI не вычисляет инженерные показатели;
- каждый renderer получает готовую типизированную модель;
- экран и печать используют одинаковые диапазоны, единицы, подписи и interval selection;
- PDF и DOCX не строятся путем слепого копирования HTML-таблиц;
- raw diagnostics и внутренние dict/list структуры не попадают в пользовательские документы;
- изменение UI-настроек не перечитывает LAS и не запускает расчет заново.

#### 4R.3. Implementation sequence

**R1 — State and performance foundation**

- убрать оставшиеся конфликты widget default/session state, включая `interpretation_tablet_marker_count`;
- перенести mapping, tablet settings и export settings в подтверждаемые формы;
- кэшировать LAS parsing по content hash;
- разделить data revision, calculation revision и presentation revision;
- запретить построение пяти тяжелых фигур на нерелевантном rerun;
- заменить непонятный floating running indicator на нормальный inline status;
- добавить измерение `parse_ms`, `calculation_ms`, `model_ms`, `render_ms`, `export_ms`.

**R2 — Professional Well Log Renderer**

- единая depth axis;
- компактные track headers с названием, единицами и шкалой;
- linear/log scale;
- стандартные grid/ticks;
- ограничение числа треков на лист;
- автоматический active-depth window с ручным override;
- interval lane вместо десятков пересекающихся горизонтальных линий;
- отдельные screen и print presets при общей модели;
- визуальные golden tests для A4 portrait, A4 landscape и wide screen.

**R3 — Pixler, ternary and validation plots**

- модели строятся по набору всех валидных строк, а не по случайной первой строке;
- явные причины исключения точек;
- нормализация и фильтрация NaN/Inf/zero denominator до renderer;
- минимум одна валидная точка отображается;
- пустое состояние содержит агрегированную диагностику, а не каскад повторяющихся предупреждений.

**R4 — Correlation Workspace**

- минимум две реальные скважины;
- общий depth window и синхронный zoom/scroll;
- выбор кривых и tops;
- нормальные масштабы по каждой скважине;
- отсутствие пустой геологической панели;
- экспорт correlation board в SVG/PDF/PNG через тот же render model.

**R5 — Reports v4**

- инженерный отчет: 6–10 страниц;
- экспертный отчет: ограниченный основной документ плюс приложения CSV/XLSX/JSON;
- PDF renderer с фиксированными page templates;
- DOCX renderer через `python-docx` с управляемыми widths, captions и page breaks;
- HTML renderer без raw diagnostic structures;
- таблицы максимум 5–6 смысловых колонок;
- длинные заключения выводятся карточками/абзацами, а не узкой колонкой;
- нулевые интервалы исключаются из основного отчета;
- одинаковые русские термины и единицы во всех форматах.

**R6 — Interval consolidation and acceptance**

- объединять соседние интервалы одного типа по настраиваемому depth gap;
- одиночные точки маркировать как anomalies, а не полноценные пласты;
- отдельно считать raw candidates и consolidated intervals;
- live acceptance на одном и нескольких LAS;
- regression, golden-image, document-layout и performance gates.

#### 4R.4. Definition of Done

Рефакторинг завершен только если одновременно выполнено следующее:

- смена вкладки без изменения данных не перечитывает LAS и не пересчитывает формулы;
- обычный navigation rerun не показывает пустой floating square;
- Interpretation cached rerender укладывается в целевой бюджет до 2 секунд на тестовом LAS;
- профессиональный планшет читаем на экране и на A4, без пустых 60–70% листа;
- Pixler и ternary отображают валидные точки либо одну понятную агрегированную причину отсутствия данных;
- correlation открывается без route errors и показывает минимум две скважины;
- инженерный PDF/DOCX не содержит вертикального текста, raw keys, нулевых интервалов и повторяющихся таблиц;
- PDF, DOCX и HTML проходят визуальную приемку пользователем;
- Stage 5 остается заблокирован до полного закрытия Stage 4R.

#### 4R.5. First authorized increment

Следующий разрешенный инкремент: **v214 — Presentation Refactor Foundation**.

Текущий прогресс: explicit mapping apply, explicit interpretation run и explicit presentation/tablet build реализованы; inline runtime status и оставшиеся вторичные presentation/export boundaries являются следующим подэтапом.

Состав:

1. revision-based state model;
2. устранение всех widget/session-state conflicts;
3. deferred tablet/export forms;
4. LAS parse cache;
5. inline progress state вместо floating indicator;
6. базовые типы `WellLogRenderModel` и `ReportDocumentModel`;
7. characterization tests текущего поведения перед заменой renderers.

До завершения v214 запрещено одновременно переписывать PDF, DOCX и correlation renderer: сначала должен быть стабилизирован общий state/model boundary.

### Stage 5 — Petrophysical Engine

Status: **BLOCKED — starts only after confirmed Stage 4 live production acceptance**

- подтверждённые формулы и единицы;
- transparent calculation contracts;
- petrophysical curves and quality flags;
- integration with LAS Viewer and reports.

### Stage 6 — Modeling Engine

Status: **PLANNED**

- correlation;
- structural/facies/property modeling;
- 2D/3D visualization;
- plugin/API extensibility.

## 4. Замороженные боковые направления

До подтверждённого завершения Stage 4 и последующего Petrophysical Engine не расширять:

- bookmarks/recent-session convenience features;
- audit report exchange and signing infrastructure;
- licensing and activation;
- telemetry;
- cloud collaboration;
- AI assistant.

Существующий код сохраняется и поддерживается только на уровне исправления критических дефектов.

## 5. Изменение roadmap

Roadmap изменяется только когда:

1. найден архитектурный блокер;
2. изменилось подтверждённое требование владельца проекта;
3. текущий этап завершён по Definition of Done.

Любое изменение отражается в `PROJECT_ROADMAP.md` и `PROJECT_STATUS.md`; история фиксируется в `CHANGELOG.md`. Новые plan/status файлы не создаются.

## Stage 4 corrective increment — v209

- [x] Expose a dedicated `nav.correlation` route in the top menu, LAS workflows and Project Explorer.
- [x] Reuse the existing multi-well LAS correlation renderer and export controls.
- [x] Move the engineering well-log figure before long report tables.
- [x] Limit the engineering profile to the 15 strongest non-zero-thickness intervals.
- [x] Move full interval reasoning to the expert appendix.
- [x] Add static Plotly-to-PDF rendering with a controlled Kaleido fallback.
- [x] Connect Project Explorer object clicks to Workbench Selection Service.
- [x] Render contextual Properties for project, well, LAS, curve and collection selections.
- [x] Replace technical empty Properties rows with an actionable empty state.
- [x] Prevent Developer Diagnostics from rendering inside a collapsed narrow dock rail.
- [x] Preserve Properties collapse/restore state through the existing Dock Manager.
- [ ] Live acceptance: load two wells, render correlation, export correlation, generate PDF with embedded plot.


## Stage 4 corrective increment — v210

- [x] Stop implicit professional report generation on every Streamlit rerun.
- [x] Batch profile/format controls behind an explicit prepare action.
- [x] Keep prepared export bytes in the existing session state.
- [x] Make the download label, MIME type and filename match the prepared format.
- [x] Add timing/error logging for presentation export.
- [x] Reuse unchanged interpretation figure sets across reruns.
- [ ] Complete live acceptance for HTML, PDF, DOCX and bundle downloads on Windows.


## Stage 4 corrective increment — v211

- строгая валидация mapping C1, C2, C3, iC4, nC4, iC5, nC5;
- блокировка расчета при неполном mapping;
- очистка устаревших графиков/отчетов при смене источника;
- явный текстовый индикатор подготовки экспорта вместо пустого spinner;
- acceptance: новый файл с неверным mapping не может показывать графики предыдущего расчета.

### Stage 4 — v212 printable-report acceptance
- [x] Remove widget/session-state conflict for tablet track selection.
- [x] Remove raw Python diagnostic payloads from printable reports.
- [x] Crop report tablets to active data and limit interval overlays.
- [x] Embed plot images into DOCX instead of renderer placeholders.
- [ ] Live acceptance: PDF, DOCX, HTML and browser printing on Windows.
- [ ] Confirm no floating empty status box during navigation and export settings.

- v213: repair correlation route registration, printable plot depth crop, report table density, and valid interval defaults.


## Stage 4R v214 export preparation boundary

- [x] Generate PNG/PDF/SVG only after an explicit prepare action.
- [x] Cache static Plotly artifacts by source signature, presentation revision and export dimensions.
- [x] Generate interpretation HTML and printable interval reports only after explicit preparation.
- [x] Generate selected-interval CSV only after explicit preparation.
- [x] Generate LAS-correlation HTML only after explicit preparation.
- [x] Increment export revision only when artifact bytes are generated.
- [ ] Complete live Windows acceptance with Kaleido installed for PNG/PDF/SVG.

### Stage 4W Dataset lifecycle hardening
- [x] Audit active, archived and orphan dataset storage per table section.
- [x] Add safe cleanup actions with project ID confirmation.
- [x] Create automatic ZIP backup before bulk dataset cleanup.
- [x] Rebuild manifests and project index after deletion.

### Stage 4W — Project Database table lifecycle (completed)

- Separate derived metadata cleanup from user-file deletion.
- Add synchronized maintenance for file index, file versions and UUID registry.
- Add safe compaction/reset with automatic project backup.
- Permit real-file cleanup only for verified exact duplicates with explicit confirmation.

- [x] Improve Project Database tables with filtering, sorting, pagination and optional technical metadata.

### Unified Workbench Data Grid

- [x] Project Database tables
- [x] Dataset Manager tables
- [x] Saved calculation archive
- [x] Project export catalog
- [ ] Dedicated persisted report catalog, after Report Repository is introduced

### Unified Workbench Data Grid — selection boundary

- [x] Publish selected Dataset rows to Properties.
- [x] Publish selected Calculation rows to Properties.
- [x] Publish selected Export rows to Properties.
- [x] Remove duplicate selectors below unified grids.
- [x] Move contextual object actions into Properties.
- [ ] Add multi-selection and bulk actions.
- [ ] Extend selection to all Project Database tables.

### Workbench UX Refactor — Project Explorer 2.0

- [x] Replace the flat Explorer counter list with the persisted metadata-only project hierarchy.
- [x] Add expandable project, folder, well group, well, LAS version, calculation and export nodes.
- [x] Add project-object search that retains ancestor context.
- [x] Synchronize Explorer selection with Properties through WorkbenchSelectionService.
- [x] Add compact ready/warning/error/empty status markers.
- [ ] Add persisted report and correlation nodes after their repositories are available.
- [x] Move contextual actions to Properties.
- [ ] Add safe multi-selection and bulk actions.

- [x] Unified Data Grid multi-selection and safe bulk actions for datasets, calculations and exports.

### Calculation Diagnostics 2.0

- [x] Structured C1–nC5 column quality report.
- [x] Per-formula valid/invalid row counts.
- [x] Missing-input, zero-denominator and non-numeric cause counts.
- [x] Problem-row preview and concrete recommendations.
- [x] Replace repeated NaN banners with grouped diagnostics UI.
- [ ] Persist diagnostics snapshots with saved calculations.
- [ ] Add diagnostics comparison between calculation revisions.
- [ ] Export diagnostics into PDF and DOCX reports.

### Persisted Calculation Diagnostics Snapshot

- [x] Store structured diagnostics with each new saved calculation.
- [x] Validate diagnostics JSON during calculation integrity checks.
- [x] Preserve backward compatibility with older snapshots.
- [ ] Display persisted diagnostics after restart without recalculation.
- [ ] Add LAS NULL and sampling-density diagnostics.

- Regression guard added for methodology warning imports used by the Data workspace.

- [x] Preserve active calculation across Data, Interpretation and Reports navigation.
- [x] Add project-bound guard for shared calculation state.


### Completed: durable Data to Interpretation handoff
- Preserve the last explicit calculation across Workbench workspace transitions.
- Invalidate it only on explicit mapping reset, project change, LAS reset or manual cleanup.

- [x] Fix active calculation revision contract used by Data → Interpretation handoff.

- Completed compatibility hardening for revision snapshots used by Data → Interpretation handoff.

- Interpretation first-render fix: initial graphs/tablet now auto-commit on first valid calculation; explicit button remains for later settings changes. Streamlit marker/zone count widgets now use Session State as the single source of truth.

- [x] Stabilize Interpretation full-interval rendering/export metadata and tablet marker/zone widget state.

### Completed: Engineer-oriented interpretation tables
- interval-first summary in Interpretation workspace;
- scrollable calculation and interval tables;
- printable interval registry and decision-oriented executive summary.

## 4. Active engineering refactor — Reservoir Intelligence / Interpretation 2.0

This is the current product priority. The goal is to replace technically correct but weak visual output with an engineer-facing interpretation workspace.

### 4.1 Information architecture and terminology

- [x] Remove dataframe row counters from the primary interpretation summary.
- [x] Show interval, top/base, thickness, probable fluid, confidence, data quality, geological support and conclusion.
- [ ] Add interval filters by fluid, depth, thickness, confidence and review status.
- [ ] Synchronize table selection with Pixler, ternary, depth tracks and interval passport.
- [ ] Keep rows/cells/counts only in Diagnostics and Developer mode.

### 4.2 Pixler rehabilitation

- [ ] Plot all valid samples for the selected interval instead of a single decorative polyline.
- [ ] Add selected-depth marker, interval centroid/median and interval trend.
- [ ] Add named interpretation fields with explicit methodology status.
- [ ] Show depth, ratio, classification, data quality and method agreement in hover details.
- [ ] Explain what the graph supports, contradicts or cannot determine.
- [ ] Provide dark interactive and light print render profiles from one plot model.

### 4.3 Ternary rehabilitation

- [ ] Plot the interval point cloud, selected depth and robust center.
- [ ] Show percentages of valid points by interpretation region.
- [ ] Distinguish confirmed methodology boundaries from project draft boundaries.
- [ ] Report component completeness and points outside defined regions.
- [ ] Link ternary classification to the common confidence engine.

### 4.4 Depth engineering panel

- [x] Use a shared reversed depth axis across every track.
- [x] Add Total Gas, C1–C5, Wh/Bh/Ch, Pixler ratios, reservoir type and confidence tracks.
- [x] Draw top/base boundaries, interval fills, IDs, thickness and selected-depth marker.
- [ ] Use logarithmic scale only for curves whose physical range requires it.
- [x] Never replace missing measurements with zero for presentation.
- [ ] Add practical track presets and readable print layout.
- [x] Add collision-aware interval labeling: suppress tiny/overlapping labels, show selected interval prominently and keep full details in hover.
- [x] Add a compact QC/recommendation track with hover details instead of long text inside the depth panel.

### 4.5 Interval passport and method agreement

- [ ] Show interval ID, top, base, thickness, probable fluid and confidence.
- [ ] Show robust interval statistics for gas components and calculated ratios.
- [ ] List supporting, conflicting and unavailable methods.
- [ ] Show data limitations and concrete verification recommendations.
- [ ] Keep water, non-productive and insufficient-data conclusions methodologically distinct.

### 4.6 Reporting profiles

- [ ] Customer Summary: concise deliverable for the customer, focused on intervals, confidence, limitations and recommendations.
- [ ] Engineering Report: full working interpretation with plots, interval registry, passports and methodology agreement.
- [ ] Technical Report: reproducible audit with mapping, formulas, diagnostics and calculation provenance.
- [ ] Export figures from the shared plot model; do not use UI screenshots.
- [ ] Produce vector or high-resolution print-safe figures for PDF and DOCX.

### 4.7 Refactoring and quality gates

- [ ] Separate interval analytics, plot models, Plotly renderers and report renderers.
- [ ] Reduce `app/streamlit_app.py` by moving interpretation business logic out of UI functions.
- [ ] Add golden-data tests for Pixler, ternary and depth panel classification.
- [ ] Add visual/export smoke tests for dark screen and light print profiles.
- [ ] Each graph must answer: what, where, interpretation, evidence, confidence and limitation.

### Definition of Done

The stage is complete only when an engineer can select an interval and obtain synchronized Pixler, ternary, depth panel, interval passport and printable reports without reading dataframe counters or developer diagnostics.

### Pixler 2.0 — interval-aware visualization (implemented foundation)
- [x] Use all valid measurements of the selected hydrocarbon interval instead of a single row.
- [x] Show interval median and a separate marker for the selected depth.
- [x] Overlay configurable interpretation zones and an engineer-facing conclusion.
- [ ] Validate zone limits against approved corporate methodology and field calibration.
- [ ] Add interval selector synchronization with the reservoir register and passport.
- [x] Ternary 2.0 interval foundation: cloud of valid interval measurements, normalized median center, selected-depth marker, configured methodological regions, completeness assessment and engineering conclusion.
- [x] Depth Panel 2.0 foundation: shared reversed depth axis, fluid-colored interval fills, explicit top/base boundaries, interval ID, thickness and selected-depth marker.
- [x] Depth Panel 2.0 engineering tracks: separate Reservoir Type, Confidence and Recommendations tracks driven by the common interval model.

- [x] Depth Panel readability hotfix: removed repeated Depth titles, suppressed overlapping HC labels and confidence text, reduced full-width boundaries, and moved recommendation detail to hover-only QC markers.

### Axis, depth and print controls
- [x] Use factual LAS top/base as the default Y range; never introduce an empty 0..top-depth segment.
- [x] Keep manual depth-from/depth-to controls for the interpretation workspace.
- [x] Add persisted manual Y limits for the Pixler logarithmic crossplot.
- [x] Add an independent depth-from/depth-to interval for PDF/DOCX report generation.
- [ ] Extend the reusable manual X/Y axis contract to correlation and remaining project charts.
- [ ] Add print presets for current interval, selected reservoir and full well.


## Reporting format policy

- [x] Remove user-facing HTML print/export.
- [x] Keep PDF and DOCX as primary professional report formats.
- [x] Keep a PDF + DOCX package for convenient delivery.
- [ ] Continue synchronized interval selection and the two Depth Panel viewing modes.

## Completed: synchronized interval viewing

- [x] Whole-well overview mode.
- [x] Detailed selected-interval mode.
- [x] Adaptive depth-panel height.
- [x] Minimum interval thickness visualization filter.
- [x] Shared selected interval state for the interpretation workspace.
- [x] Selected interval passport foundation.

Next: use the same selection context in the Data workspace Pixler and ternary selectors and in report generation without duplicating interval detection.

## Completed: shared selected interval in Data Workspace and report export

- [x] Drive Data Workspace Pixler and ternary from `selected_reservoir_interval_id`.
- [x] Keep the selected reservoir synchronized between Data Workspace and Interpretation without overwriting a new user choice during rerun.
- [x] Use the selected reservoir top/base as the default PDF/DOCX print interval.
- [x] Preserve manual and current-graph print interval modes as explicit alternatives.

- [x] Выбор инженерного интервала кликом по строке таблицы с общей синхронизацией Pixler, ternary, Depth Panel, паспорта и PDF/DOCX.

- [x] Engineering Navigation 2.0: предыдущий/следующий интервал, центрированное окно таблицы и визуальный маркер активного пласта.

- [x] Unified compact Engineering Header for the selected reservoir above Pixler, ternary and Depth Panel.
- [x] Fluid-colored active-row markers shared by engineering interval tables.

### Reservoir Passport 2.0 — выполнено
- [x] Газовый состав C1–C5 по интервалу.
- [x] Производные коэффициенты и отношения.
- [x] Результаты Pixler, ternary и Haworth.
- [x] Индекс согласованности методик.
- [x] Ограничения, рекомендации и готовность к PDF/DOCX.


## Reservoir Ranking (v214)

- Добавлен прозрачный индекс инженерного приоритета 0–100.
- Весовые компоненты: достоверность 30%, согласованность методик 30%, полнота C1–C5 20%, валовая мощность 20%.
- Нулевые по мощности одиночные точки и неопределённый флюид получают явные штрафы.
- Рейтинг не является оценкой запасов, net pay, насыщенности или коммерческой ценности.
- Выбор строки рейтинга синхронизирует активный интервал, Pixler, ternary, Depth Panel, паспорт и PDF/DOCX.

### Reservoir Ranking 2.0 — выполнено

- [x] Встроенные инженерные профили ранжирования.
- [x] Ручная настройка и автоматическая нормализация весов.
- [x] Сохранение пользовательских профилей в проекте.
- [x] Сравнение текущего рейтинга с выбранным базовым профилем.
- [x] Объяснение изменения места и итогового индекса.
- [x] Передача активного профиля в PDF/DOCX.

Следующий этап: Cross-Method Analysis — структурированный анализ согласий и противоречий Pixler, ternary и Haworth с инженерным объяснением причин расхождений.

## Explainable Interpretation Engine

- [x] Единый формат результата методик.
- [x] Анализ согласия и противоречий Pixler, ternary и Haworth.
- [x] Матрица согласованности.
- [x] Вклад методик в итоговую классификацию.
- [x] QC и причины возможных расхождений.
- [x] Разложение уверенности.
- [x] Интеграция с Reservoir Passport и PDF/DOCX.
- [ ] Расширение Method Library новыми методиками.

## Method Framework 1.0

- [x] Added the common `BaseMethod`, `MethodContext` and `MethodResult` contracts.
- [x] Added an ordered `MethodRegistry` and default registry factory.
- [x] Moved Pixler, ternary and Haworth interval analysis behind the common method interface.
- [x] Changed Reservoir Passport to execute registered methods instead of calling method-specific analyzers directly.
- [x] Added non-throwing unavailable-result diagnostics for missing method inputs.
- [ ] Move plot descriptions behind the same method capability contract.
- [ ] Add project-level enable/disable configuration for registered methods.
- [ ] Add new published methods only through the framework.

- [x] Graphics Recovery: restore local palette configuration in Interpretation and prevent route-level `NameError`.

## Sprint 4 — Engineering Reports — завершено
- Добавлены отдельные профили «Отчет для заказчика» и «Инженерный отчет».
- Клиентский профиль сокращен до ключевых выводов, интервалов, достоверности, рекомендаций и ограничений.
- Инженерный профиль сохраняет расширенные расчетные таблицы и приложения.
- PDF и DOCX используют единую модель документа и одинаковую структуру разделов.
- Служебные поля, внутренние идентификаторы и технические метаданные исключены из пользовательских титульных данных.

## Sprint 5 — Plot Engine Cleanup — завершено
- Добавлен единый конфигурационный слой `palettes/plot_engine.py`.
- Унифицированы инженерная палитра, типографика, поля, легенды и сетка.
- Введён единый контракт глубинной оси с обратным направлением и единицами «м».
- Унифицированы толщина линий, размеры маркеров и hover-подсказки.
- Depth-графики, Pixler, ternary, интерпретационный и отчётный планшеты переведены на общий слой.
- PNG, SVG и PDF используют экспортную копию той же экранной фигуры и темы.
- Добавлены регрессионные тесты общего графического контракта.

## v221 — Stabilization & Release Audit (active)

Status: **IN PROGRESS**

- Full regression suite and release preflight.
- Separation of current regressions from historical compatibility debt.
- Manual smoke scenarios for data import, interpretation, navigation and export.
- Real LAS verification for Pixler, ternary, Haworth and engineering tablet.
- PDF, DOCX, PNG, SVG and XLSX cross-format verification.
- Large-LAS and performance regression.
- Removal of dead user-facing HTML paths and obsolete export entry points.
- Elimination of direct UI access to `st.session_state` outside the application-state boundary.
- Release candidate packaging only after critical gates pass.

Release candidate Definition of Done:

- no collection errors;
- no new regressions in v216-v220 contracts;
- architecture state audit passes;
- export and large-LAS preflight passes;
- unresolved historical failures are documented explicitly.


## Stabilization & Release Audit

### v221-rc2 — Full Regression Closure — COMPLETED
- Full regression suite closed: 2003 tests passed.
- Release profile, navigation, dataset UI and build identity contracts synchronized.
- Next gate: v221 stable packaging and final manual acceptance.


### v221 — Stable Release — COMPLETED

- Promoted build identity to v221 / stable.
- Preserved the five completed engineering stabilization sprints.
- Closed the automated regression suite before stable packaging.
- Next gate: manual acceptance and targeted v221.1 maintenance fixes.

## v222-rc1 — Export Engine Refactoring

- Добавлен renderer-neutral `ExportController`.
- Разделены кэш модели отчёта и кэш готового формата.
- Переключение PDF/DOCX/PNG/SVG/XLSX не перестраивает инженерную модель при неизменных данных.
- Генерация запускается только после явного подтверждения пользователя.
- Ошибки экспорта содержат этап, тип исключения и корреляционный код.
- Рабочая область не падает при ошибке отдельного renderer.
- README.md не изменялся.



## v222-rc3 — Transactional Export Session

Статус: реализовано.

Критерии завершения:
- ранняя валидация экспортного запроса;
- идемпотентный повторный запрос;
- защита от двойного запуска;
- ограничение памяти экспортного кэша;
- изоляция пустых и повреждённых результатов renderer.


### v222-rc4 — Isolated Professional Export panel — выполнено

- изоляция панели экспорта через Streamlit fragments;
- отсутствие полного rerun при работе с настройками экспорта;
- отсутствие повторного Plotly render после подготовки файла;
- регрессионная проверка fragment-контракта и fallback-поведения.


### v222-rc5 — Engineering UI readability — выполнено

- контраст графиков и УВ-зон;
- компоновка заголовков планшета;
- адаптивные таблицы PDF/DOCX.

### v222-rc6 — Engineering Workspace Refactoring — выполнено

- ограниченный Plot Cache 2.0;
- стабильные ключи экранных Plotly-компонентов;
- адаптивная компоновка инженерных дорожек планшета;
- устранение наложения верхних заголовков.

### v222-rc7 — Engineering Core Refactoring — завершено

- State namespaces.
- Observable Plot Cache.
- Runtime diagnostics ring buffer.
- Plot render metrics in logs.

Следующий подэтап: v222-rc8 — Lazy Workspace Rendering and Render Queue.

## v222-rc8 — Lazy Workspace Rendering and Render Queue

- Lazy route resolution for the active workspace only.
- Sequential render queue for expensive Plotly builders.
- Duplicate task suppression within a render cycle.
- Per-task runtime diagnostics and bounded cache integration.
- Stable Plotly component keys retained for frontend reuse.

## v222-rc9 — Plot Serialization Cache

- Cache normalized Plotly browser payloads.
- Reuse stable content fingerprints across reruns.
- Avoid repeated Python-side figure serialization.
- Keep original figures for static export and reports.


## v222-rc10 — Render Resilience and Memory Guardrails

- isolate individual plot-builder failures;
- preserve successful graphs when one renderer fails;
- enforce Plot Cache byte and entry limits;
- collect frontend dispatch timing and payload-size diagnostics;
- prepare performance acceptance gates for v222 stable.

### v222-rc12 — Workspace Performance Audit
- Aggregate runtime diagnostic events into release-gate summaries.
- Detect critical render duration, failed stages and oversized frontend payloads.
- Remove avoidable full-frame copies from the interpretation workflow.

## v222.2 — Export Contract Synchronization — завершено

- строгий контракт запроса и готового файла;
- обнаружение устаревшего подготовленного артефакта;
- синхронизация профиля и диапазона в XLSX;
- регрессионные тесты PDF/DOCX/XLSX-контрактов.

### v222.6 — Commercial Tablet Visual Pass
Статус: выполнено. Единое полотно, общая легенда, одна шкала глубины, приоритетный интервал и DOCX hotfix.


### v222.7 — Engineering Visualization Polish
- ограничение browser overlay payload без потери полного инженерного реестра;
- единое полотно и инженерная major/minor grid;
- приоритетный интервал с явным визуальным статусом;
- уменьшение межтрековых разрывов печатного планшета.

## Завершено: v222.10
- единый полезный диапазон для всех depth-графиков;
- адаптация графиков раздела данных;
- цветные значки кривых и флюидов;
- синхронное выделение УВ-интервалов.


## Завершено в v222.13
- обзорный планшет всей скважины;
- детальные планшеты по продуктивным интервалам;
- объединение близких пластов;
- адаптивный диапазон глубин;
- лимиты детализации по профилю отчёта.

## Следующий приоритет
- оглавление и PDF-закладки;
- пользовательский выбор режима отчёта: краткий, стандартный, полный инженерный.


## Завершено в v222.14
- Discoverable Professional Export UI.
- Full-well atlas scope.
- Four-stage export progress and user guidance.

---

## Reporting modernization — current increment

### Completed

- Industrial PDF page chrome and metadata.
- Professional Export Wizard state machine and preflight validation.
- Professional Report Designer foundation.
- Engineering, Corporate and Minimal report templates.
- Renderer-neutral section filtering and ordering.
- Synchronized PDF/DOCX presentation options.

### Next

1. Connect Report Designer to Streamlit UI.
2. Add live report structure preview.
3. Connect approved design state to Export Wizard execution.
4. Add operation progress indicators and tooltips.
5. Unify engineering chart theme and export quality.

## Завершено — Large-LAS Performance Acceptance Gates

- добавлен воспроизводимый synthetic LAS benchmark для renderer-neutral pipeline;
- введены release gates по cold/warm latency, peak memory, cache hit и geometry reduction;
- добавлен JSON-отчет для локального запуска и CI;
- инженерные расчеты и исходные данные не изменяются;
- следующий приоритет: подключить benchmark report к CI и вывести performance summary в runtime diagnostics.

## Завершено — PDF Table of Contents and Bookmarks

- добавлено многостраничное оглавление с фактическими номерами страниц;
- добавлены PDF outline-закладки для заголовка и инженерных разделов;
- стандартный и полный инженерный режимы включают навигацию автоматически;
- краткий режим сохраняет компактный PDF без оглавления и закладок;
- настройки проходят через единый Report Designer и не меняют расчётную модель.

### Следующий приоритет

- интерактивный preview структуры отчёта перед экспортом;
- отображение состава разделов и навигации в Export Wizard;
- проверка длинных отчётов и стабильности пагинации.

## Runtime stabilization — static export scope hotfix

- [x] Remove invalid `active_project` capture from `_render_static_export_controls`.
- [x] Remove invalid `current_export_request` capture from the static Plotly exporter.
- [x] Build export data revision in the professional report request scope.
- [x] Route Export Wizard persistence through `ApplicationStateController` state.
- [x] Add regression coverage for interpretation workspace static export rendering.

## Завершено — Recoverable Background Export Retry

- завершённые задания без process-local артефакта корректно распознаются после перезапуска приложения;
- интерфейс больше не показывает недоступный бинарный файл как готовый к скачиванию;
- для failed, cancelled, orphaned и потерянных completed-результатов добавлен безопасный повторный запуск;
- повтор использует текущие проверенные параметры Export Wizard и создаёт новую задачу;
- старый terminal snapshot удаляется перед повтором, активные задания по-прежнему защищены от удаления;
- регрессионные тесты покрывают доступность артефакта, retryable-состояния и Streamlit-интеграцию.

### Следующий приоритет

- сохранить краткую диагностическую причину повторного запуска в истории заданий;
- добавить ограниченный список последних фоновых экспортов в UI;
- провести ручную acceptance-проверку отмены и повторного запуска на большом LAS.

## Завершено — Bounded Background Export History and Retry Diagnostics

- добавлен компактный список пяти последних фоновых экспортов проекта;
- история показывает состояние, прогресс и краткую диагностическую причину повторного запуска;
- новый фоновый job сохраняет связь с предыдущей задачей через `retry_of_job_id`;
- причина retry сохраняется в metadata snapshot и восстанавливается после rerun/restart;
- добавлен безопасный fallback для `st.fragment`, когда тестовый или старый Streamlit возвращает некорректный decorator;
- новые unit- и integration-тесты покрывают лимит истории, причины retry и persistence metadata.

### Следующий приоритет

- ручная acceptance-проверка отмены и повторного запуска на большом LAS;
- добавить действия очистки отдельных terminal-записей из списка последних фоновых экспортов;
- подключить runtime performance summary к диагностической панели.

## Завершено — Terminal Background Export History Cleanup

- в списке последних фоновых экспортов добавлено удаление отдельных terminal-записей;
- добавлена проектная массовая очистка завершённых записей;
- активные задания остаются защищёнными от удаления;
- завершённый job с ещё не переданным process-local артефактом не удаляется массовой очисткой;
- исправлена защита от обращения к `relevant_job`, когда для текущей сигнатуры нет подходящей задачи;
- добавлены unit- и Streamlit integration-тесты для индивидуальной и массовой очистки.

### Следующий приоритет

- ручная acceptance-проверка отмены, повторного запуска и очистки истории на большом LAS;
- подключить runtime performance summary к диагностической панели;
- добавить фильтрацию истории экспортов по статусу и формату.

## Завершено — Background Export History Filters

- история фоновых экспортов получила фильтрацию по статусу и формату;
- формат экспорта сохраняется в metadata snapshot и восстанавливается после rerun/restart;
- пустой фильтр означает отображение всех записей, порядок newest-first сохраняется;
- массовая очистка применяется только к видимым после фильтрации terminal-записям;
- добавлено пустое состояние для комбинаций фильтров без совпадений;
- добавлены unit- и Streamlit integration-тесты для фильтрации и persistence metadata.

### Следующий приоритет

- ручная acceptance-проверка отмены, retry, cleanup и фильтров на большом LAS;
- подключить runtime performance summary к диагностической панели;
- добавить длительность задания и размер готового артефакта в историю экспортов.

## Завершено — Background Export Duration and Artifact Size

- snapshot фонового задания сохраняет итоговую длительность операции;
- для завершённого экспорта сохраняется размер process-local артефакта;
- извлечение размера остаётся renderer-neutral и поддерживает bytes, content и вложенный artifact;
- история экспортов показывает длительность, размер готового файла и формат;
- старые metadata snapshots без новых полей продолжают загружаться с безопасными значениями по умолчанию;
- добавлены unit- и Streamlit regression-тесты для persistence, форматирования и UI-интеграции.

### Следующий приоритет

- ручная acceptance-проверка cancel/retry/cleanup/filters на большом LAS;
- подключить runtime performance summary к диагностической панели;
- добавить сортировку истории экспортов по времени, длительности и размеру.

## Завершено — Background Export History Sorting

- история фоновых экспортов получила сортировку по времени обновления, длительности и размеру артефакта;
- для каждого критерия доступны прямой и обратный порядок;
- сортировка применяется после фильтрации и не изменяет исходные snapshots;
- неизвестное сохранённое значение безопасно возвращает порядок «сначала новые»;
- детерминированные вторичные ключи предотвращают визуальное перемешивание записей между Streamlit rerun;
- добавлены unit- и Streamlit integration-тесты.

### Следующий приоритет

- ручная acceptance-проверка cancel/retry/cleanup/filters/sorting на большом LAS;
- подключить runtime performance summary к диагностической панели;
- перейти к интерактивному preview структуры отчёта перед экспортом.

## Завершено — Actual Document Counts in Report Preview

- после успешной подготовки PDF, DOCX или ZIP-пакета сохраняется renderer-neutral снимок фактического состава `EngineeringDocument`;
- предпросмотр структуры повторно использует этот снимок без хранения бинарного документа и без повторных инженерных расчётов;
- фактические количества разделов, таблиц, строк, графиков, планшетов и информационных блоков уточняют диапазон страниц;
- явный `EngineeringDocument` имеет приоритет над сохранённым снимком, что исключает расхождение при прямом API-вызове;
- сброс черновика экспорта очищает и сохранённую статистику модели;
- добавлены unit-, export- и Streamlit integration-тесты.

### Следующий приоритет

- привязать снимок состава к сигнатуре выбранного дизайна и диапазона глубин, чтобы не показывать устаревшую оценку после изменения настроек;
- добавить отметку времени и источник оценки в preview;
- затем перейти к миниатюрам страниц PDF Preview.

## Завершено — Signature-bound Report Preview Counts

- сохранённый снимок фактического состава отчёта теперь привязан к стабильной SHA-256-сигнатуре контекста;
- сигнатура учитывает разрешённый дизайн отчёта, формат экспорта, нормализованный диапазон глубин, сигнатуру источника и ревизии расчёта/представления;
- после изменения шаблона, режима, заголовка, разделов, формата, диапазона глубин или исходных данных устаревшие фактические значения автоматически скрываются;
- перестановка верхней и нижней границы одного диапазона не инвалидирует корректный снимок;
- старый формат session-state без сигнатуры безопасно игнорируется;
- добавлены unit- и Streamlit integration-тесты.

### Следующий приоритет

- добавить отметку времени и источник фактической оценки в preview;
- реализовать PDF Preview с миниатюрами страниц;
- выполнить ручную acceptance-проверку на большом LAS.

### Increment: persisted report-preview document counts
- [x] Store the compact, schema-versioned report document-count snapshot per project.
- [x] Restore it after application restart without persisting the full `EngineeringDocument`.
- [x] Revalidate the restored snapshot against the current design/data signature before reuse.
- [x] Remove persisted preview metadata when export settings are reset.

# Latest increment — Report Preview Persistence Recovery

Status: COMPLETED

Implemented:
- one-generation backup for each project report-preview count snapshot;
- automatic recovery when the primary JSON file is truncated, malformed or invalid;
- quarantine of unrecoverable primary and backup metadata instead of repeated startup failures;
- atomic restoration of a valid backup to the primary location;
- Streamlit warning and structured logging when recovery or quarantine occurs;
- reset removes both primary and backup metadata.

Validation:
- `python -m py_compile reports/report_preview_persistence.py app/streamlit_app.py`;
- `48 passed` in focused persistence and report-preview regression tests.

Next priority: add bounded retention and cleanup for quarantined metadata files plus project-storage diagnostics.

## Завершено — Report Preview Storage Health Diagnostics

- добавлена read-only диагностика проектного хранилища снимков предпросмотра;
- контролируются наличие и валидность основного файла и резервной копии;
- отображаются количество quarantine-файлов и занимаемый ими объём;
- состояния `healthy`, `recoverable`, `degraded`, `quarantined` и `empty` не изменяют файлы при проверке;
- диагностический блок добавлен в предпросмотр структуры отчёта;
- добавлены unit- и Streamlit integration-тесты.

### Следующий приоритет

- реализовать PDF Preview с миниатюрами страниц;
- добавить ручную очистку quarantine-файлов из диагностического блока;
- выполнить acceptance-проверку на большом LAS-файле.

## Data hygiene increment

- Project documentation is kept under `docs/`; no planning Markdown files are created at repository root.
- Generated local project state was removed from the distributable archive.
- Safe disposable-data cleanup is available through `core.data_cleanup.DataCleanupService` and preserves `data/projects` by default.

## PDF Preview foundation

- Added bounded raster preview generation for already-rendered PDF artifacts.
- The service prefers PyMuPDF and falls back to local `pdftoppm`.
- Preview rendering is limited to 1–12 pages and 72–180 DPI.
- Temporary source and page files are isolated outside project `data/` and removed automatically.
- Next step: connect the service to the Report Designer UI and cache previews by report signature.


### Implemented: PDF Preview UI integration

- On-demand bounded thumbnails for completed PDF exports.
- Session cache bound to artifact content and export request signature.
- Safe fallback when PyMuPDF/pdftoppm is unavailable.

### Implemented: PDF Preview compact layout and performance metrics

- PDF thumbnails can be displayed in one or two columns;
- preview result records actual rendering time and memory footprint;
- the UI displays page count, backend, PDF size, thumbnail size and average page thumbnail size;
- layout changes reuse the same raster cache.

### Implemented: selective PDF page-range preview and cache cleanup

- PDF preview can start from an explicitly selected page while keeping the bounded page-count limit;
- preview cache signatures now include the selected starting page;
- PyMuPDF and `pdftoppm` backends preserve the real page numbers in thumbnail captions;
- the Professional Export panel exposes an explicit project-scoped preview-cache cleanup action;
- changing the visual one/two-column layout still reuses the same raster cache.

Next priority: add keyboard-friendly page navigation and optional DPI control without allowing unbounded raster workloads.

### Implemented: PDF Preview navigation and bounded DPI

- Added keyboard-friendly previous/next page-group navigation in the Professional Export panel.
- Added a bounded DPI selector with fixed safe values from 72 to 180 DPI.
- Preview cache signatures already bind DPI and now receive the selected UI value.
- Renderer-neutral page-window helpers clamp navigation to valid first/last groups.
- No planning Markdown files were created at repository root.

Next priority: direct page-jump feedback and optional bounded adjacent-window prefetch without unbounded raster work.

### PDF Preview: direct page-jump validation

- Completed bounded direct page-jump validation and user feedback.
- Cache keys and rendering now use the same normalized start page.
- Planned next: opt-in prefetch of the next bounded page range.

### Runtime hardening — Professional Export

Исправлен порядок вычисления диапазона печати перед построением сигнатуры предпросмотра и устранены конфликты значений Streamlit Session State с параметрами виджетов.

## Runtime stability update

- [x] Make Workbench navigation tolerant of non-pickleable background runtime services in application state.
- [x] Preserve deep rollback for ordinary mutable shell state.
- [x] Cover `queue.SimpleQueue` navigation and rollback scenarios with regression tests.

### Runtime state isolation

- [x] Introduce a session-scoped registry for executors, queues, locks and in-memory runtime caches.
- [x] Move background export, dataframe cache, plot cache and runtime diagnostics behind the registry boundary.
- [x] Exclude the runtime registry from transactional deep-copy rollback while retaining deep rollback for data state.
- [ ] Add explicit lifecycle shutdown for registered services when a session is disposed.

### Runtime service lifecycle shutdown

- [x] Add best-effort `close()` / `shutdown(wait=False)` handling to `RuntimeServiceRegistry`.
- [x] Return serializable per-service shutdown diagnostics without leaking live objects.
- [x] Dispose and remove session runtime services when the Workbench workspace closes.
- [x] Preserve shutdown progress when one service raises during cleanup.
- [ ] Connect the same disposal boundary to full Streamlit session termination where supported.

### Runtime shutdown telemetry

- [x] Aggregate per-service shutdown outcomes into a serializable summary.
- [x] Publish `workbench.runtime_services.shutdown` during workspace disposal.
- [x] Report failed service keys/types/errors without retaining live objects.
- [x] Detach the disposed runtime registry from application state.
- [ ] Connect disposal to a stable Streamlit session-termination hook when supported.

### PDF Preview: bounded adjacent-window prefetch

- [x] Add an explicit opt-in checkbox for preloading the next page group.
- [x] Keep the preview cache bounded to three recent signatures.
- [x] Preserve compatibility with legacy single-preview Session State payloads.
- [x] Reuse prefetched thumbnails when the user navigates to the next range.
- [x] Keep page count and DPI workload limits unchanged.
- [ ] Add cache hit/prefetch telemetry and validate behavior on a large generated report.

### PDF Preview: cache and prefetch telemetry

- [x] Add safe cache lookup metadata for legacy and bounded multi-entry payloads.
- [x] Log current-range cache hits and misses with page-window parameters.
- [x] Log prefetch render duration, thumbnail bytes and backend.
- [x] Log reuse of an already-prefetched adjacent range.
- [x] Validate bounded adjacent-window reuse on a generated 24-page PDF.
- [ ] Add optional UI cache statistics and memory-pressure diagnostics.

### PDF Preview: UI cache statistics and memory pressure diagnostics

- [x] Add payload-free aggregation of cached range count, page count and PNG memory usage.
- [x] Display optional per-project cache metrics in the Professional Export panel.
- [x] Classify cache pressure with bounded warning and critical thresholds.
- [x] Preserve the three-entry cache bound and avoid copying binary payloads during diagnostics.
- [ ] Add explicit cache eviction telemetry and configurable bounded memory budget.

## PDF Preview memory budget

- [x] Add per-project in-session preview cache memory budget control.
- [x] Evict oldest thumbnail ranges when count or memory limits are exceeded.
- [x] Add renderer-neutral eviction diagnostics and payload-free logging.
- [ ] Begin editable interpretation interval manager with project persistence and validation.

## Phase 2 — Stabilization, optimization and architecture hardening

### Runtime & Performance Foundation

- [x] Treat an absent active calculation as a valid empty-project state.
- [x] Add reusable bounded stage timers to runtime diagnostics.
- [x] Instrument the LAS correlation render pipeline by stage.
- [x] Add correlation performance budgets and cache hit-rate telemetry.
- [x] Add serializable runtime-service lifecycle counters.
- [x] Add a shared cache metrics registry for runtime caches.
- [x] Add payload-free Session State audit diagnostics.
- [ ] Move the correlation figure cache behind `RuntimeServiceRegistry`.
- [ ] Add bounded cache eviction and memory-budget telemetry.
- [ ] Add a diagnostics UI for runtime, cache, session and render metrics.
- [ ] Establish cold/warm correlation benchmark baselines for 1, 2, 5 and 10 wells.

### Phase 2 increment — Workbench Diagnostics Center (completed)

- [x] Consolidated runtime-service lifecycle metrics.
- [x] Consolidated cache hit/miss/invalidation/eviction metrics.
- [x] Session State ownership and scope audit without deepcopy.
- [x] Performance-budget status from bounded diagnostic events.
- [ ] Next: bounded correlation figure cache with memory-aware eviction and cold/warm benchmarks.

### Phase 2 increment — Repository and transaction hardening (completed)

- [x] Centralize durable atomic JSON writes.
- [x] Add payload-free repository I/O telemetry.
- [x] Migrate the correlation repository and its journals/profile stores.
- [x] Surface repository metrics in Developer Diagnostics.
- [x] Preserve backward-compatible repository constructors.
- [ ] Next: migrate the correlation figure cache into a bounded runtime cache service.

## Phase 2 engineering update — Logging and tracing

- [x] Structured operation tracing with bounded runtime storage.
- [x] Correlation execution grouping and slow-stage classification.
- [x] Diagnostics Center trace summary and recent-event inspection.
- [ ] Cold/warm correlation benchmark baselines.
- [ ] Byte-aware runtime cache eviction.

### Phase 2 increment — Route data contracts and lazy project loading (completed)

- [x] Declare route-specific project data requirements.
- [x] Separate active-project resolution from project-tree construction.
- [x] Reuse project navigation data until the active project changes.
- [x] Add route data loading diagnostics and budgets.
- [ ] Move heavy route providers behind lazy module factories.

### Phase 2 increment — Project navigation cache and repository invalidation (completed)

- [x] Add bounded process-local LRU cache for serialized project navigation.
- [x] Add metadata fingerprint tokens without reading payload file contents.
- [x] Invalidate only changed project entries and report the rebuild reason.
- [x] Restore navigation state from runtime cache after Session State cleanup.
- [x] Expose hit-rate, invalidations, evictions and token cost in Developer Diagnostics.
- [ ] Next: connect repository write operations to explicit navigation invalidation hooks.

### Phase 2 — Repository cache coherence (completed)

- Shared repository mutation notifications.
- Targeted project navigation cache invalidation.
- Active-project DataFrame cache invalidation.
- Mutation diagnostics and failure isolation.

### Phase 2 — Repository transaction boundaries and consistency diagnostics (completed)

- [x] Add staged multi-file JSON transactions with one transaction identifier.
- [x] Prepare all write payloads before replacing destination files.
- [x] Restore already-applied files when a later commit step fails.
- [x] Publish one coherent cache-invalidation mutation after successful commit.
- [x] Expose transaction counts, rollbacks and recent transaction metadata in Developer Diagnostics.
- [ ] Next: migrate high-value multi-file workflows to the shared transaction API.


### Phase 2 — Repository and service decoupling (in progress)

- [x] Add lazy application service container on top of the runtime registry.
- [x] Move correlation workspace/profile/audit repository access behind an application service.
- [x] Keep application services project-scoped and removable through lifecycle cleanup.
- [x] Add architecture tests preventing direct repository construction in correlation UI.
- [ ] Migrate interpretation workspace, revision and publication UI to application services.
- [ ] Add service dependency and health diagnostics.

### Phase 2 increment — Lazy Project Explorer branches (completed v222.15)

- [x] Build the initial Explorer root without reading collapsed well, calculation, export or custom-folder repositories.
- [x] Materialize only the metadata branch explicitly expanded by the operator.
- [x] Force a complete metadata view while Project Explorer search is active.
- [x] Include the requested branch profile in the runtime navigation-cache token.
- [x] Preserve the legacy full-tree contract for callers that do not request lazy sections.
- [ ] Next: add branch-level load timing and per-section cache hit diagnostics.

### Phase 2 increment — Project Explorer branch diagnostics (completed v222.16)

- [x] Measure metadata loading at the `project`, `well_cards`, `wells`, `calculations`, `exports`, `custom` and `labels` boundaries.
- [x] Keep timing payloads primitive and bounded; no project objects, DataFrames or repository payloads are retained.
- [x] Record cache hits, misses, loads and hit rate independently for each requested branch profile.
- [x] Surface the latest per-branch timings through the shared Project Navigation cache diagnostics snapshot.
- [x] Verify that collapsed branches do not appear in timing events and therefore are not read eagerly.
- [x] Preserve multiple branch profiles concurrently instead of replacing the active project's previous profile entry.

### Phase 2 increment — Multi-profile Project Explorer cache (completed v222.17)

- [x] Key serialized navigation entries by both project and requested branch profile.
- [x] Preserve root-only, partial and full-search profiles concurrently for one active project.
- [x] Keep capacity bounded by project count rather than by profile count.
- [x] Remove all profiles coherently on project invalidation, metadata change or LRU eviction.
- [x] Expose payload-free project-to-profile occupancy diagnostics.
- [x] Add a bounded per-project profile cap and profile-level memory estimates before large custom Explorer profiles are introduced.

### Phase 2 increment — Bounded Project Explorer profile cache (completed v222.18)

- [x] Limit cached branch profiles independently for each project.
- [x] Evict the least recently used profile without evicting the whole project.
- [x] Estimate serialized cache memory without retaining duplicate payload objects.
- [x] Expose total, per-project and per-profile byte diagnostics.
- [x] Keep existing project-level LRU and repository invalidation semantics intact.
- [ ] Next: add an optional global byte budget and byte-aware eviction for unusually large full-search profiles.

- [x] Localized LAS import result contract (ru/kk/en).
- [x] Rebuild/reconcile SQLite metadata catalog from immutable manifests.
- [x] Detect legacy LAS encodings and non-standard data delimiters with stable warning codes.


## v222.30 — Legacy LAS UI and catalog operations
- Added manual SQLite metadata-catalog reconciliation in Workbench Diagnostics Center.
- Added bounded decimal-comma and fixed-width legacy LAS diagnostics.
- Added stable validation codes and synchronized ru/kk/en messages.


# Latest increment — LAS Editor Dataset lineage and column validation

Status: COMPLETED

Implemented:
- localized Data Platform registration feedback directly in the LAS Editor upload surface;
- session/checksum deduplication so Streamlit reruns do not register the same upload repeatedly;
- immutable Dataset version creation when an edited LAS is saved to the project;
- lineage linkage from the editor output to the uploaded source Dataset;
- bounded first-row column counting and comparison with Curve Information;
- stable `las.validation.curve_data_column_mismatch` diagnostics in ru/kk/en.

Next priority: expose Dataset lineage/history in Project Explorer and add a deliberate strict/tolerant import-mode selector for legacy LAS.


# Latest increment — Dataset lineage explorer and deliberate LAS import modes

Completed in v222.32:

- lazy `datasets` branch in Project Explorer with one node per immutable lineage and chronological version children;
- lightweight lineage application-service projections without artifact payloads;
- explicit `tolerant` and `strict` LAS import modes in LAS Editor;
- strict mode blocks legacy/structural deviations before artifact or manifest persistence;
- tolerant mode preserves archival LAS behaviour and records warnings;
- bounded multi-row LAS sampling (up to eight rows by default);
- stable `las.validation.inconsistent_data_columns` diagnostics when sampled row widths differ;
- ru/kk/en labels and messages for import-mode selection and inconsistent-column validation.

Next priority: expose selected Dataset version properties and provenance in the Properties pane, add a lineage comparison action, and validate depth monotonicity/step stability from a bounded sample.


### v222.33 — Dataset Version Properties and bounded LAS depth QC

- Dataset version selection exposes SHA-256, provenance, artifact reference and previous-version metadata without reading LAS payloads.
- Application service can compare two immutable versions from one lineage using manifest metadata only.
- LAS scanner validates monotonic depth and STEP stability over the bounded sample rows.

## v222.34 — LAS Quality Control Foundation

Status: COMPLETED

- [x] Stable platform-level `QC-*` codes independent from UI language.
- [x] Depth, NULL, range, spike, flat-line and unit checks through a reusable QC engine.
- [x] JSON-safe per-curve statistics.
- [x] Lazy `QCApplicationService` boundary.
- [x] User and developer documentation in Russian, Kazakh and English.
- [x] Documentation manifest and petroleum terminology foundation.
- [ ] Next: register QC output as a derived Dataset version/artifact and add Workbench QC presentation.

## QC Platform Phase II

- [x] Persist QC Report as immutable derived Dataset artifact.
- [x] Link QC provenance to the exact source Dataset version.
- [x] Add severity/code filtering projection.
- [x] Add lazy PDF/DOCX export boundary.
- [ ] Wire the localized QC panel into the production Workbench route.
- [ ] Add interactive curve-statistics table and finding filters.
- [ ] Register exported PDF/DOCX files as export artifacts.


### QC Workbench production integration — completed in v222.36

- Localized QC panel in LAS Editor.
- Severity and stable-code filters.
- Findings and curve-statistics tables.
- Derived QC Dataset persistence.
- Registered PDF/DOCX export artifacts with provenance.

Next: QC history in Project Explorer, direct downloads, Dataset comparison badges and report-template profiles.

### QC Platform Phase IV — Project Explorer and registered downloads (completed v222.38)

- [x] Expose saved QC report Datasets in a dedicated lazy Project Explorer folder.
- [x] Expose registered PDF/DOCX QC exports with downloadable metadata.
- [x] Add a bounded and path-contained registered-artifact read boundary.
- [x] Add QC status badges through stable metadata, without reading report payloads.
- [x] Attach latest QC summaries to Dataset version comparisons.
- [ ] Next: report-template profiles and localized interactive QC comparison presentation.

## v222.40 — DLIS/LIS79 and SEG-Y metadata adapter foundation

- [x] Formally evaluate official specifications and open-source candidates.
- [x] Approve `dlisio` and `segyio` only as lazy optional LGPL adapters.
- [x] Add a dependency-free bounded SEG-Y textual/binary-header scanner.
- [x] Add DLIS/LIS79 scanner boundaries with graceful dependency-unavailable diagnostics.
- [x] Register LIS79 as a separate format capability.
- [x] Add generated conformance fixtures with explicit legal provenance.
- [x] Add a SEG-Y trace-header inventory adapter using `segyio` with configurable byte mapping.
- [x] Add DLIS logical-file/frame/channel metadata projection behind the installed `dlisio` boundary.
- [x] Add localized ru/kk/en metadata import previews.
- [ ] Wire previews and DLIS frame/channel selection into the production Data workspace.
- [ ] Add coordinate scalar and trace-coordinate geometry diagnostics for SEG-Y.


## v222.44 — Production subsurface import preview and SEG-Y geometry diagnostics

- [x] Wire bounded DLIS/LIS79/SEG-Y metadata preview into Data Workspace.
- [x] Keep binary subsurface files outside the tabular CSV/Excel/LAS calculation parser.
- [x] Add configurable SEG-Y inline, crossline, coordinate-scalar, X and Y header-byte mapping.
- [x] Apply SEG-Y coordinate scalar semantics without reading trace amplitudes.
- [x] Add geometry confidence and stable diagnostics for missing or implausible coordinate mappings.
- [x] Localize preview controls, fields and warnings in ru/kk/en.
- [ ] Next: interactive DLIS logical-file/frame/channel selection and persisted preview manifests.


## v222.45 — Global locale and subsurface preview completion

- [x] Add persistent RU / ҚАЗ / EN buttons to every Workbench page.
- [x] Bind Documentation Center content and documents to the active interface locale.
- [x] Verify Russian, Kazakh and English document resolution independently.
- [x] Add explicit fallback disclosure instead of silently showing Russian content.
- [x] Add DLIS/LIS79 logical-file/frame/channel selection projection.
- [x] Persist bounded import previews as immutable Dataset Manifest records.
- [ ] Next: render SEG-Y geometry preview on an interactive map/schematic and add optional-adapter CI jobs.

## v222.46 — Unified Import Pipeline foundation

- [x] Add a format-plugin registry layered on the existing Format Registry.
- [x] Publish a JSON-safe capability matrix for Workbench decisions.
- [x] Add preview cache keys based on SHA-256, profile and scanner version.
- [x] Add project-scoped, atomic import-profile persistence.
- [x] Add an explainable Dataset readiness score (0–100).
- [x] Add synchronized ru/kk/en user and developer documentation.
- [ ] Next: production Import Wizard state machine, batch import and readiness badges in Project Explorer.

### v222.47 — Professional Import Platform foundation — completed

- [x] JSON-safe production Import Wizard state machine.
- [x] Failure-isolated batch import service.
- [x] Metadata-only quick QC for LAS, DLIS, LIS79 and SEG-Y.
- [x] Persisted readiness fields in Dataset Manifest.
- [x] Readiness projection in Project Explorer.
- [x] RU/KK/EN user and developer documentation.
- [ ] Next: bind the wizard state machine to a full step-by-step Workbench UI, add background batch jobs and import history views.

### Completed in v222.48
- Public README links for Russian, Kazakh and English.
- Language-specific user and developer documentation indexes.
- Release gate for multilingual links and documentation manifest consistency.

## Завершено — Professional Import Wizard UI and Background Jobs (v222.50)

- [x] Multilingual multi-file Import Wizard in Data Workspace.
- [x] Bounded session-local background import job manager.
- [x] Project-scoped append-only import history.
- [x] Independent per-file results and readiness display.
- [x] Retry of failed batch items only.
- [x] Updated user documentation in ru/kk/en.

Next: persistent job recovery after application restart, cancellation, and import-history filtering/export.


## Import operations hardening — v222.51

Completed:
- durable project-scoped import job snapshots;
- restart recovery into an explicit interrupted state;
- queued/running cancellation contract;
- history filters and JSON/CSV export;
- staging cleanup with active-job protection.

Next:
- cooperative cancellation between individual batch items;
- explicit resume workflow for interrupted jobs;
- configurable retention and automatic cleanup;
- Project Explorer import-history branch.


### Import Operations Phase IV — completed

- cooperative cancellation between batch items;
- explicit resume of interrupted jobs;
- configurable history retention;
- age-based stale staging cleanup;
- durable per-item progress updates.

Next: expose Import History as a lazy Project Explorer branch and add a project-level readiness dashboard.


## v222.53 — Import History Explorer and Project Readiness Dashboard

- [x] Add a lazy `Import history` branch to Project Explorer.
- [x] Load compact import job metadata only when the branch is expanded.
- [x] Add a manifest-only project readiness aggregate.
- [x] Show average readiness and Ready/Review/Blocked/Unknown counts in Professional Import Wizard.
- [x] Aggregate registered source datasets by format without reading artifacts.
- [x] Add regression coverage for lazy history loading and readiness aggregation.

Next: add readiness filters to Dataset history, direct navigation from import jobs to registered datasets, and project-level correlation-readiness analysis.


## v222.54 — Readiness filters and correlation preparation

- Added manifest-only readiness filters by status and format.
- Import History jobs now expose links to datasets created by each job.
- Added project-level correlation-readiness analysis based on LAS manifests, shared curves and depth metadata.
- No LAS rows or SEG-Y/DLIS payloads are loaded by these projections.

### Completed in v222.56

- Initial UI Platform package and Streamlit adapter.
- Central design tokens and Theme Engine foundation.
- Framework-neutral button and empty-state contracts.
- Compact global language switcher migration.
- UI Platform quality check.

### Next stabilization increment

- Migrate common notifications and empty states to the UI SDK.
- Introduce icon and layout registries.
- Audit hardcoded user-facing strings and route smoke coverage.
- Measure Workbench render cost before Workbench 2.0 redesign.

## v222.57 — Report & Diagnostics UX Hardening

Completed:
- compact, collapsed-by-default Report & Print workspace;
- clear action-oriented report instructions instead of a long multicolour introduction;
- GAS RATIO PRO corporate print theme for Plotly-compatible report figures;
- larger PDF/DOCX typography and one-item-per-row printed legends;
- higher-resolution report chart export;
- concise developer diagnostics summary with detailed tables hidden by default.

Next:
- split Report Workspace into four guided steps: source, settings, preview, export;
- add an explicit operating-system print action after artifact generation;
- migrate report controls to UI Platform component contracts;
- standardize chart palettes and line semantics across all engineering workspaces.

### Document Platform / Print & Export Center

- [x] Компактная глобальная команда `🖨 Печать и экспорт` вместо постоянно раскрытой формы.
- [x] Независимый язык документа RU / KK / EN.
- [x] Базовый `PrintCenterSession` без зависимости от Streamlit.
- [x] Язык документа входит в экспортную сигнатуру и кэш-контекст.
- [ ] Полноэкранный/модальный предпросмотр страниц.
- [ ] Разделение настроек документа, графика и печати на независимые панели.
- [ ] Полная локализация таблиц, легенд, рекомендаций и заключений во всех renderer-ах.
- [ ] Явные действия `Сформировать`, `Скачать`, `Печать` после подготовки документа.
- [ ] Менеджер пользовательских шаблонов и история документов.

### M3-S01.1 — Plot Typography & Readability ✅
- крупные подписи треков и осей в PDF/DOCX;
- компактные отображаемые имена треков;
- отсутствие дублирующей микролегенды внутри печатного изображения;
- уменьшенная высота экранных depth-графиков;
- подготовка к адаптивному Track Layout Engine.

- [x] v222.64: ReportDesign schema compatibility and Print Center crash regression.
