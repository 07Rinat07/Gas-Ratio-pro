## v214 — Depth Panel collision and readability fix

- Added pixel-aware collision suppression for interval labels.
- Preserved the selected interval label even when neighboring intervals are dense.
- Removed full-width top/base boundaries for tiny unlabeled intervals.
- Reduced non-selected interval fill intensity and strengthened selected-interval emphasis.
- Replaced recommendation text blocks with compact QC markers and hover details.
- Removed repeated `Depth` titles from each subplot and retained one shared `Глубина, м` axis.
- Added regression tests for dense interval sets and y-axis title duplication.

## v214 — Interpretation 2.0 planning and engineer-facing summary

- Replaced the Data workspace `interpretation/count` table with the hydrocarbon interval registry.
- Added interval, thickness, probable fluid, confidence, data quality, geological support and engineering conclusion columns.
- Restricted dataframe row counters to diagnostics/developer contexts.
- Added the ordered Reservoir Intelligence / Interpretation 2.0 roadmap covering Pixler, ternary, depth panel, interval passport and print reporting.
- Defined Customer Summary, Engineering Report and Technical Report by purpose rather than job title.

# GAS RATIO PRO — Changelog

## v214 — Depth Panel 2.0 foundation

- Added a dedicated interpreted-interval track to the interactive well-log tablet.
- Added fluid-colored interval fills across all curve tracks.
- Added explicit top/base boundaries, interval IDs, thickness and confidence labels.
- Added a synchronized selected-depth line across the complete panel.
- Preserved NaN gaps instead of drawing absent measurements as zero.
- Added regression tests for interval overlays and backward compatibility.

## v214 — Contextual Properties actions

- Added a contextual action group to the right-hand Properties pane for LAS, datasets, calculations, reports and exports.
- Added command-backed action requests so the renderer never mutates repositories directly.
- Added explicit object-ID confirmation for archive and delete operations.
- Added automatic project backup before destructive Properties actions.
- Added integrity checks for datasets, LAS and saved calculations.
- Added technical-properties toggle while keeping IDs, paths and checksums hidden by default.
- Removed the architectural dependency on duplicated selectors for object actions.

## v214 — Project Explorer 2.0 foundation

- Replaced the flat Workbench Explorer list with the persisted metadata-only project hierarchy.
- Added expandable project, folder, well group, well, LAS version, calculation and export nodes.
- Added project-object search with automatic ancestor preservation.
- Routed node selection through WorkbenchSelectionService so Properties receives the selected object metadata.
- Added compact ready, warning, error and empty-state markers without loading heavy payloads.
- Added framework-neutral Explorer filtering and expansion tests.

## v214 — Workbench stabilization after live UI review

- Converted saved calculations into an explicit project archive instead of treating them as current session data.
- Prevented archived warning, integrity and export evaluation until the archive is explicitly opened.
- Removed duplicate navigation and dock commands from the ribbon; it now contains only contextual module actions.
- Hydrated Project Explorer calculation and artifact counters from the active project.
- Added regression tests for archive gating, ribbon information architecture and Explorer counters.

## v214 — Explicit multi-well correlation build

- Separated mutable LAS-correlation controls from the applied multi-well presentation snapshot.
- Added explicit `Построить корреляцию` action for synchronized well plots, curve comparison and Correlation Studio.
- Bound the applied correlation snapshot to exact content signatures for every loaded LAS well.
- Prevented well selection, depth range, X-scale, marker and grid edits from rebuilding Plotly figures before explicit apply.
- Added one-entry correlation figure cache, inline rendering status and duration logging.
- Added persistence, source-guard and static regression tests for the correlation workflow.

## v214 — Explicit presentation and tablet build

- Separated mutable graph and tablet controls from the applied presentation snapshot.
- Added explicit `Построить графики и планшет` action.
- Bound applied presentation settings to the exact calculated DataFrame signature and calculation revision.
- Prevented depth-range, height, color, fill, marker and zone edits from rebuilding Plotly figures before explicit apply.
- Reused cached figures only for the applied immutable settings snapshot.
- Added persistence and revision-guard tests for applied presentation state.

## v214 — Explicit mapping and interpretation actions

- Separated mutable mapping widgets from the committed mapping snapshot.
- Added explicit `Применить mapping` and `Запустить интерпретацию` actions.
- Bound committed mapping state to the exact prepared DataFrame signature.
- Prevented unrelated Streamlit reruns and draft widget edits from executing gas-ratio calculations.
- Preserved the last committed interpretation result while an invalid draft is being corrected.
- Added regression tests for applied-mapping persistence and source-signature guards.

## v214 — Presentation refactor foundation implementation

- Added independent monotonic revisions for data, calculation, presentation and export invalidation boundaries.
- Added a thread-safe SHA-256 LAS content cache that reloads only when file bytes change.
- Returned defensive DataFrame copies from the cache to prevent mutation leakage between reruns.
- Connected cached LAS parsing to the shared upload path and logged parse duration plus cache-hit state.
- Added immutable renderer-neutral `WellLogRenderModel` and `ReportDocumentModel` contracts.
- Invalidated the interpretation figure cache only when a new calculation dataset is stored.
- Added focused v214 tests for revision propagation, serializable session state, cache behavior, signatures and contracts.

## v214 — Presentation refactor plan approved

- Reopened the remaining Stage 4 work as a controlled Engineering Presentation Refactor after v213 live acceptance.
- Added a mandatory sequence for state/performance, Well Log Renderer, Pixler/Ternary, Correlation, Reports v4 and interval consolidation.
- Defined revision-based data/calculation/presentation boundaries and prohibited unrelated reruns from reading LAS or rebuilding figures.
- Defined independent PDF, DOCX and HTML renderers backed by shared typed presentation models.
- Kept Stage 5 blocked until live visual, document and performance acceptance passes.
- Updated only the existing roadmap, status and changelog; no new planning files were created.

## v211

- Блокирован расчет при неполном mapping обязательных газовых компонентов C1-C5.
- Предыдущие графики, расчетные данные и кэш очищаются при смене источника на некорректно сопоставленный файл.
- Исключена подстановка нулевых C-компонентов как допустимого основания для инженерного расчета.
- Плавающий spinner экспорта заменен на встроенное текстовое состояние подготовки формата.
- Добавлено логирование `calculation_blocked_invalid_mapping`.

## v210

- Fixed professional export controls so selecting DOCX/HTML/PDF no longer leaves a stale `Скачать PDF` button.
- Added an explicit `Подготовить выбранный формат` action; expensive export generation no longer runs during every Streamlit rerun.
- Cached the prepared download artifact in session state and added visible generation progress.
- Added structured export duration and failure logging to the existing `logs/app.log`.
- Added one-entry session caching for unchanged interpretation Plotly figures to reduce repeated 15-25 second rebuilds.

## v209

- Added dedicated Correlation navigation and Project Explorer route.
- Connected the existing multi-well LAS correlation workflow directly to Modern Workbench.
- Moved report figures before tabular sections.
- Reduced engineering report interval cards to the 15 strongest non-zero-thickness intervals.
- Moved full reasoning tables to the expert appendix.
- Added Plotly raster embedding for PDF reports with explicit Kaleido fallback.
- Connected Project Explorer selections to the central Workbench Selection Service.
- Replaced technical `None`/dash-only Properties output with contextual object metadata and a useful empty state.
- Fixed collapsed Properties rail so Developer Diagnostics no longer renders as vertical clipped text.
- Preserved collapse/restore state across reruns through the existing Dock Manager.

## v208

- Activated File and Project menus with project/session workflows.
- Added compact shared logo to the Workbench title bar.
- Removed duplicate Documentation logo overlay.

## v207 Functional navigation and report workflow restoration

- Restored Data Workspace as a first-class Modern Workbench route.
- Replaced decorative top-menu labels with command-backed buttons.
- Replaced static Project Explorer rows with route-aware controls.
- Added actionable Reports prerequisite flow back to Data Workspace.
- Added acceptance tests for Data, menu, tree and report bindings.

## v206 Functional visibility repair

- Removed the empty fixed-height HTML workspace shell that pushed native Streamlit workflow widgets below the visible central workspace.
- Production LAS, Interpretation, Reports, Exports and Documentation renderers now appear directly in the central Workbench column.
- Added regression tests for workspace visibility and existing production renderer bindings.
- Updated the existing roadmap and status documents only; no new planning files were created.

## v203 — Workbench module integration audit and runtime diagnostics

- Added centralized command and workspace-renderer exception capture.
- Added correlation IDs and rotating-log traceback references for user-visible failures.
- Added compact serializable runtime incidents and module-binding snapshots.
- Added optional Developer Diagnostics panel and `run_app.ps1 -Diagnostics`.
- Updated the existing roadmap/status only; no new planning documents were created.
- Stage 4 remains open until real LAS, graphs, reports, exports and documentation workflows pass live acceptance.

## v202 — Workbench functional integration

- Embedded existing LAS import/analysis, LAS editor and LAS correlation workflows in Modern Workbench.
- Routed interpretation graphs and printable reports through the central workspace.
- Connected project export archive and Documentation Center.
- Added Documentation to the single navigation/tool route table.
- Added functional integration regression tests without creating new planning documents.

## v201 — Workbench live interaction completion

- Replaced decorative empty-workspace cards with command-backed quick actions.
- Added visible active-workspace context and route-specific empty-state content.
- Verified quick-action transitions through the existing Command Framework.
- Kept Stage 4 open pending live visual acceptance.


## v200 — Workbench UX interaction stabilization

- Prevented Streamlit system header from clipping the Workbench title bar.
- Added active workspace highlighting and deterministic command feedback.
- Removed redundant tool activation from the ribbon.
- Made dock collapse/restore actions mutually exclusive and state-aware.
- Added production interaction tests for real application-state transitions.
# GAS RATIO PRO — Changelog

## v199 — Workbench UX redesign

- Redesigned the production Workbench title bar, menu and command ribbon.
- Removed empty ribbon groups and reduced label clipping.
- Increased typography and control sizes for desktop readability.
- Made the central workspace the dominant visual region.
- Added structured Project Explorer, Properties and compact status presentation.
- Replaced technical collapse/restore labels with compact dock controls.
- Preserved command-backed UI actions and renderer-neutral contracts.

## v198 — Technical audit, runtime identity and documentation consolidation

- Reopened Workbench UI Completion after live production acceptance failed.
- Identified stale Streamlit process / wrong extracted source as the most likely mismatch: the shown shell strings do not exist in the current renderer.
- Added visible build version and absolute runtime source path.
- Added port ownership checks and safe `-ForceRestart` launcher behavior.
- Consolidated active governance to ROADMAP, STATUS, ARCHITECTURE and DOCUMENTATION_INDEX.
- Archived redundant progress and versioned roadmap files.
- Added regression tests for build identity, launcher safety and documentation governance.

# v197 — Workbench Production Completion

- Fixed production crash caused by reading removed `CommandExecutionResult.success`; startup now uses `executed`.
- Replaced cross-call HTML shell composition with native Streamlit columns and containers.
- Made command ribbon, Project Explorer, central workspace, Properties and Status Bar render as real production regions.
- Added command-backed collapse/restore controls in native dock regions.
- Added runtime-oriented production smoke tests for layout and rerun behavior.
- Completed Stage 4 and activated Stage 5 Petrophysical Engine.

# Changelog

## v194 — Unified roadmap correction for Workbench UI Completion

- Updated the single active roadmap after reviewing the real production Workbench screen.
- Inserted Workbench UI Completion as the active stage before Petrophysical Engine.
- Defined the required full-screen workspace host, command toolbar, Project Explorer, contextual Properties panel and operational Status Bar.
- Added a concrete Definition of Done preventing the minimal shell from being treated as a completed engineering UI.
- Deferred Petrophysical Engine to Stage 5 and Modeling Engine to Stage 6 without removing either scope.
- Kept the existing shell architecture, Command Framework, Event Bus, Dock Manager and production entry-point decisions unchanged.

## v193 — Modern Workbench production entry correction

- Made Modern Workbench the default Streamlit application entry point.
- Retained the previous main page only as an explicit `GAS_RATIO_PRO_LEGACY_UI` process-level fallback.
- Prevented session state from enabling legacy mode.
- Added startup regression tests for default, fallback and stale-session behavior.
- Corrected Stage 3 completion status before resuming Petrophysical Engine work.

## v189

- Added one atomic Workbench shell dispatcher for navigation, tool activation and dock lifecycle commands.
- Added rollback of the complete presentation state when any command in a coordinated transition fails.
- Published one normalized `workbench.shell.state_changed` event after each successful shell transition.
- Exposed a serializable renderer-facing shell event contract with final navigation, workspace, tool and dock focus state.
- Removed the architectural gap between independent command calls and coherent Workbench shell state.
- Added unit, integration, rollback and renderer-contract regression coverage.

## v188

- Added an application-level Dock Manager for pane open, close, collapse, restore and focus operations.
- Routed all dock mutations through Workbench commands and normalized Event Bus events.
- Persisted dock layout as presentation-only state with explicit opened/collapsed flags.
- Connected registered Workbench tools to serializable dock panes.
- Opened and focused a tool pane when its registered tool is activated.
- Extended the renderer contract with dock pane state and command-backed lifecycle actions.
- Added Dock Manager unit, controller integration and regression coverage.

## v187

- Added one deterministic application-level Workbench navigation router.
- Synchronized navigation selection with registered Workbench tool activation through the command framework.
- Connected LAS Workspace to the existing LAS Viewer service/view-model contract.
- Added renderer payload sections for module routes and the active module.
- Kept UI payloads free of DataFrame, storage and service objects.
- Added unit and integration coverage for all navigation-to-module routes.

## v184

- Added renderer-neutral LAS Viewer navigation controller for zoom, pan, fit and reset.
- Reused the existing shared viewport command/session contracts without UI-side depth calculations.
- Added compact navigation performance telemetry for source/visible points and bounded cache reuse.
- Added large-LAS regression coverage confirming viewport filtering and dataframe-free viewer state.
- Advanced the active roadmap to current-view SVG/PDF export.

## v183

- Added unified renderer-neutral LAS Viewer track configuration controller.
- Synchronized track visibility between viewer session and layout state.
- Added deterministic track ordering and width configuration through existing layout contracts.
- Added validated linear/log track scale with optional minimum and maximum bounds.
- Applied configured scale to both track and curve axis render contracts.
- Preserved configuration through viewer state serialization without raw DataFrame storage.
- Added unit, integration and regression coverage.

## v179

- Completed full-suite confirmation for the v178 large-LAS visualization regression.
- Updated the documentation-governance assertion to track the active PROJECT_STATUS increment instead of the superseded v178 wording.
- Verified all 1743 tests in four independent segments to avoid the environment execution ceiling.
- Closed Visualization Engine Stage 1 and activated LAS Viewer Stage 2.
- Set the next permitted increment to the real LAS-open workflow through the existing importer.
- Preflight: OK.

## v178

- Added deterministic large-LAS regression coverage for 150,000 source curve points.
- Verified adaptive downsampling, bounded render-model cache, repeat cache hits, peak-memory budget and SVG/PDF geometry parity.
- Fixed VisualizationPerformanceProfile source-point accounting for points stored inside scene layer payloads.
- Fixed fractional depth tick generation so grid primitives remain inside track clip regions.
- Added `VisualizationLargeLasRegression` serializable report contract and regression test.
- Targeted visualization regression: 20 tests passed. Preflight: OK. Full suite reached 75% without failures before the environment execution limit.

## v177

- Generated approved SVG/PDF reference artifacts for linear, Unicode and overlay multi-track scenes.
- Added SHA-256 manifest validation and renderer-neutral structural regression signatures.
- Added regeneration tests for geometry, primitive counts, clipping, page dimensions and Unicode labels.
- Updated the active roadmap and project status without creating additional planning documents.

## v176

- Added severity-aware renderer-neutral validation findings.
- Blocked SVG and PDF export when strict render validation finds fatal or error-level geometry defects.
- Added three reference multi-track LAS fixtures covering linear curves, Unicode labels and interval overlays.
- Added renderer parity and export-enforcement regression tests.

## v88 Visualization PDF Render Model Renderer

- Added a ReportLab PDF adapter that consumes the shared Visualization Render Model.
- Added print-layout coordinate transformation, clipping, rectangle, line, polyline and text primitive support.
- Added Unicode font discovery and machine-readable PDF artifact metadata.
- Added shared renderer parity validation for PDF primitive and clip counts.

## v84 Curve Quality Engine

- Added gap-aware curve segmentation and depth viewport clipping.
- Render Model now emits separate polyline primitives for valid curve segments.
- Added quality diagnostics for missing values, logarithmic invalid values and depth gaps.


## v79 Visualization Render Model Roadmap

- Added the renderer-neutral Render Model as a required architectural layer between Layout and renderers.
- Defined responsibility boundaries for Domain Model, Scene, Layout, Render Model and concrete renderers.
- Reordered the Visualization Engine roadmap so Axis, Grid, Track, Curve, Label and Legend work is built on stable drawing primitives.
- Kept the current SVG scene renderer as a compatibility path until migration to Render Model is complete.

## v78 Visualization Layout Engine

- Added renderer-neutral visualization layout contract.
- Added deterministic track, header, axis and plot geometry.
- Added shared depth coordinate mapping.
- Integrated layout stage into scene pipeline and SVG renderer.
- Added layout validation and regression tests.
## Visualization Asset Index v71

- Added a machine-readable visualization asset index for bundle exports.
- Bundle manifests now reference the index through `files.visualization_asset_index` and `visualization.asset_index`.
- Asset index entries include relative path, size, SHA-256 digest and renderer metadata.
- Release export QA now exposes a compact visualization asset summary while preserving existing smoke checks.

## LAS Visualization Report Integration v68

- Attached prepared Visualization Engine SVG previews to the PresentationModel and EngineeringDocument flow.
- Added DocumentVisualizationPreview so HTML/PDF/DOCX renderers consume the same report contract.
- HTML reports can embed SVG previews without rebuilding LAS curves or interval overlays in UI/renderers.
- Added regression coverage for report integration and raw-data isolation.

## Workbench LAS Metadata Provider v61

- Added lightweight LAS curve metadata service for renderer-safe Workbench summaries.
- LAS Viewer now exposes curve count, row count, depth range, curve units and quality flags through the tool view contract.
- Metadata is loaded through the LAS manager service boundary and does not expose raw dataframes to UI state.
- Added regression tests for metadata service and Workbench LAS Viewer provider.

# Changelog

## v188

- Added an application-level Dock Manager for pane open, close, collapse, restore and focus operations.
- Routed all dock mutations through Workbench commands and normalized Event Bus events.
- Persisted dock layout as presentation-only state with explicit opened/collapsed flags.
- Connected registered Workbench tools to serializable dock panes.
- Opened and focused a tool pane when its registered tool is activated.
- Extended the renderer contract with dock pane state and command-backed lifecycle actions.
- Added Dock Manager unit, controller integration and regression coverage.

## Visualization Bundle Assets v70

- Added stable SVG visualization assets under export bundle `assets/`.
- Bundle manifests now reference visualization preview asset files as the single shared source for HTML/PDF/DOCX audit.
- Bundle validation now checks visualization asset files for existence and non-empty payloads.
- Added regression tests while preserving release export QA.


## LAS Visualization Renderer Ready Payload v66

- Added renderer-ready legend entries for LAS curves and interval overlays.
- Added lightweight SVG preview payload for LAS visualization.
- Added default visible track ids for printable LAS rendering.
- Added compact plot summary metadata for Workbench cards and renderer headers.
- Added regression tests while preserving release export QA.


## LAS Visualization Styling Contract v64

- Added renderer-neutral axis metadata for LAS curve payloads.
- Added track and curve style hints with palette keys, stroke, fill and line width metadata.
- Added fluid overlay style hints for printable interval bands.
- Added print profile metadata for SVG/PDF-ready LAS rendering.
- Added regression tests for the visualization styling contract while preserving release export QA.


## Workbench Tool Workflow State v60

- Connected accepted Workbench tool actions to lightweight workflow state updates.
- LAS open actions now update active LAS context, Workbench selection and active tool focus through core services.
- Gas ratio actions now persist selected interval ids and focus the analysis tool without running calculations in UI state.
- Report preview and export actions now persist active report context and recent export descriptors.
- Added regression tests for action-driven context, selection, active tool and session updates while preserving release export QA.


## Modern Workbench Tool Actions v59

- Added command-backed Workbench tool action requests for LAS open, gas ratio analysis, report preview refresh and report bundle export.
- Added `core.workbench_tool_actions` with lightweight context validation and event publication.
- Exposed concrete tool actions through tool view payloads without moving business logic into Streamlit.
- Added regression tests for tool action dispatch and preserved release export QA.

## Modern Workbench Tool Content Providers v58

- Added provider-based Workbench tool view enrichment for LAS Viewer, Gas Ratio Analysis and Report Preview.
- Added lightweight `content` payloads to the renderer-neutral tool view contract.
- Exposed selected LAS, selected interval and active report references without moving calculations into UI state.
- Added regression tests for provider-enriched tool views and preserved release export QA.

## Modern Workbench Tool View Contract v57

- Added renderer-neutral tool view models for Workbench tools.
- Added tool readiness statuses, empty states, renderer hints and command-backed tool actions.
- Exposed `tool_views` through the Workbench controller and Streamlit adapter payloads.
- Added regression tests for tool view payloads and controller integration.

## Modern Workbench Controller Layer v54

- Added `core.workbench_controller` as the coordination boundary between renderer adapters, command execution, shell state and renderer contracts.
- Added controller-level validation for navigation and dock-pane targets before state changes are executed.
- Updated the Streamlit Workbench adapter to build from the controller while preserving its public compatibility surface.
- Added regression tests for controller view-model creation, renderer action dispatch and invalid target rejection.


## v35 - Presentation UI export bridge

- Added download-ready UI export artifacts for HTML/PDF/DOCX/bundle reports.
- Connected Streamlit report controls to `reports.presentation_ui`.
- Kept renderer internals out of the UI layer.


## Modern Workbench Command Actions v51

- Added command-layer actions for Workbench navigation selection.
- Added command-layer actions for Workbench dock-pane activation.
- Registered interaction commands in the Workbench shell builder.
- Added regression tests for state updates, command execution events and shell-model reflection.

## Modern Workbench Session Persistence v50

- Added workspace-session persistence for Workbench navigation entries.
- Added workspace-session persistence for Workbench dock layout panes.
- Added restore support for active Workbench navigation and active dock pane selections.
- Added regression tests for Workbench state roundtrip through WorkspaceSessionManager.

## Modern Workbench Interaction State v49

- Added framework-neutral interaction state for active Workbench navigation and active dock pane.
- Added safe fallback behavior for stale saved navigation and dock-pane selections.
- Added helper functions for persisting selected navigation and focused dock pane identifiers.
- Added regression tests for default state, restored state, stale-state fallback and selection helpers.

## Export Release QA v46

- Added bundle-manifest validation for professional presentation exports.
- Added `scripts/release_export_qa.py` as the release-level HTML/PDF/DOCX export QA command.
- Verified referenced bundle files, non-empty artifacts and cross-format consistency flags.
- Added regression tests for successful bundle validation, missing artifact detection and CLI JSON output.

## Export Reliability v45

- Added a single renderer-neutral export facade for professional presentation reports.
- Normalized HTML, PDF, DOCX and bundle manifest creation through one helper.
- Preserved backward-compatible manifest fields used by existing UI/tests.
- Added regression tests for the unified export facade and unsupported export kinds.

## Professional Reporting System v21

- Added `reports.interval_cards` with engineer-facing interval report cards.
- Added compact interval overview cards for report front matter.
- Added detailed interval reasoning table with grounds, recommendations and limitations.
- Integrated interval cards into `HydrocarbonReportPayload.professional_tables`.
- Preserved backward-compatible technical report tables.
- Added regression tests for interval card generation and report integration.


## Hydrocarbon Interpretation Engine v16

- Added structured `InterpretationLimitation` model.
- Added structured `InterpretationRecommendation` model.
- Added public builders for limitations and recommendations.
- Extended `InterpretationExplanation` with structured limitation/recommendation payloads.
- Updated Hydrocarbon Interval Engine schema to v16.

# Formula Source Audit

- Added formula/source audit for mud-gas and petrophysical calculations.
- Corrected core `CH` calculation to Haworth Character Ratio `(ΣC4 + ΣC5) / C3`.
- Updated formula documentation with bibliography, authorship and copyright/patent handling rules.
- Added regression tests for `CH` in the core calculation path and mud-gas interpretation path.

## Phase II → C.11 Model Validation & Audit Workspace Foundation

- Added `projects/model_validation_audit_workspace.py`.
- Added integrated geological model audit based on the C.10 dependency graph.
- Added checks for missing required model components, broken dependencies, orphan objects and metadata gaps.
- Added severity levels: `error`, `warning`, `info`.
- Added model readiness score and readiness status.
- Added audit manifest, UI-ready check/issue/coverage tables and Markdown audit report.
- Added profile tests for seeded models, missing components, broken dependencies, metadata warnings and saved audit records.

## Phase II → C.4 Interpolation Engine Foundation

- Added `projects/interpolation_engine.py`.
- Added regular grid generation for property modeling targets.
- Added interpolation samples, grid nodes and interpolated cell models.
- Implemented `nearest` interpolation.
- Implemented deterministic IDW interpolation with power, neighbor count, radius and optional Z support.
- Added conservative `simple_kriging_foundation` method as API-compatible placeholder for future full covariance-matrix kriging.
- Added interpolation job registry, seed data, manifest, UI-ready tables and Markdown reporting.
- Updated Roadmap and Geological/Property Modeling specifications.
- Added profile tests for grid generation, interpolation methods, job persistence, reporting and method validation.

## Phase II → B.15 Well Interval & Pay Zone Manager Foundation

- Added `las_editor/well_interval_manager.py`.
- Added deterministic interval classification from Formation Evaluation Summary results.
- Added gross/net/pay interval flags, reservoir flags, pay flags and configurable cutoffs.
- Added gross, net and pay thickness calculations with Net/Gross, Pay/Gross and Pay/Net ratios.
- Added interval split/merge helpers for professional interval editing workflows.
- Added UI-ready interval/issue tables, audit manifest and Markdown pay-zone report.
- Added profile tests for interval derivation, custom cutoffs, thickness summary, split, merge and reporting.

## Phase II → B.14 Formation Evaluation Summary Foundation

- Added `las_editor/formation_evaluation_summary.py`.
- Added integrated well/interval summary based on LAS QC, mud-gas interpretation and curve statistics.
- Added interval-level reservoir flags, dominant fluid character, confidence, QC counters and property averages.
- Added UI-ready interval/issue tables, audit manifest and Markdown engineering report.
- Added source reference support for evidence-backed interpretation reports.
- Added profile tests for summary generation, explicit intervals, manifest, UI helpers and Markdown report.

## Phase II — B.8 Documentation Evidence & Citation Audit Foundation

- Added `projects/documentation_evidence.py`.
- Added audit for `docs/sources/source_registry.json`, registered PDF files and documentation references.
- Added detection of local Windows paths such as `C:\Users\...` in committed documentation.
- Added checks for missing registered sources, missing referenced PDFs, unregistered PDF references and orphan source files.
- Added UI-ready source/reference/issue tables, evidence manifest and Markdown audit report.
- Added profile tests for documentation evidence validation and reporting.


## Phase II — B.7 Reference Sources Manager Foundation

- Added `projects/reference_sources.py`.
- Added project PDF source registry support.
- Added source copying/compression workflow for PDF evidence files.
- Added validation for missing sources and local Windows path references.
- Added UI-ready source and validation tables.
- Added `docs/sources/` with registered project reference PDFs.
- Added Reference Sources specification draft.

## Phase II B.5 — LAS Validator Professional Foundation

- Добавлен модуль `las_editor/las_validator.py`.
- Реализована проверка обязательных LAS-секций `~Version`, `~Well`, `~Curve`, `~Parameter`, `~ASCII`.
- Добавлена проверка LAS header cards, обязательных depth/header элементов и дубликатов.
- Добавлена сверка секции `~Curve` с колонками ASCII-таблицы.
- Добавлена проверка ASCII-данных: глубина, дубликаты, шаг, STRT/STOP, NULL-значения.
- Добавлены validation report, summary, UI-ready таблицы и markdown-render отчета качества.
- Модуль экспортирован через `las_editor/__init__.py`.
- Добавлены профильные тесты `tests/test_las_validator_professional.py`.

## Phase II B.3 — LAS Header Editor Professional Foundation
## Phase II B.4 — LAS ASCII Data Editor Professional Foundation

- Добавлен модуль `las_editor/ascii_data_editor.py`.
- Реализованы операции редактирования секции `~ASCII`: изменение ячейки, массовое редактирование диапазона, вставка и удаление строк.
- Добавлены сортировка по глубине, поиск/замена значений, проверка дубликатов глубины и нарушений шага.
- Добавлены UI-ready таблицы, сводка ASCII-данных, preview изменений и render ASCII body.
- README переписан в кратком пользовательском формате на русском языке без внутренних Roadmap и правил разработки.
- Добавлены профильные тесты `tests/test_las_ascii_data_editor_professional.py`.


- Added `las_editor/header_editor.py` for professional LAS header metadata editing.
- Added normalized header cards for `~Version`, `~Well`, `~Curve` and `~Parameter` sections.
- Added default header card builder for newly created LAS files.
- Added add/update/delete operations with protection for mandatory cards such as `VERS`, `WRAP`, `STRT`, `STOP`, `STEP`, `NULL` and `DEPT`.
- Added header validation for mandatory LAS items, positive depth step and reversed depth ranges.
- Added render helpers for LAS header sections and UI-ready header tables.
- Added operation history entries and safe header-only diagnostics.
- Added regression tests for Header Editor backend operations, validation, rendering and protected item behavior.


## Phase II B.2 — LAS Curve Manager Professional Foundation

- Added `las_editor/curve_manager.py` as a unified metadata-safe Curve Manager layer.
- Added curve manifest generation with order, protected flag, aliases, groups, categories, units, quality, status and sample statistics.
- Added managed add/delete/reorder/update operations for LAS curves without overwriting source LAS files.
- Added UI-ready Curve Manager table helpers.
- Updated `README.md` with project summary, author, setup, launch and testing instructions.
- Added tests for Curve Manager Professional foundation.


## Modern Workbench Command Actions v51

- Added command-layer actions for Workbench navigation selection.
- Added command-layer actions for Workbench dock-pane activation.
- Registered interaction commands in the Workbench shell builder.
- Added regression tests for state updates, command execution events and shell-model reflection.

## Modern Workbench Interaction State v49

- Added framework-neutral interaction state for active Workbench navigation and active dock pane.
- Added safe fallback behavior for stale saved navigation and dock-pane selections.
- Added helper functions for persisting selected navigation and focused dock pane identifiers.
- Added regression tests for default state, restored state, stale-state fallback and selection helpers.

## Export Release QA v46

- Added bundle-manifest validation for professional presentation exports.
- Added `scripts/release_export_qa.py` as the release-level HTML/PDF/DOCX export QA command.
- Verified referenced bundle files, non-empty artifacts and cross-format consistency flags.
- Added regression tests for successful bundle validation, missing artifact detection and CLI JSON output.

## gas-ratio-pro-phase2-specification

- Started Phase II — Engineering Specification & Architecture.
- Added Project Design Principles as the controlling project philosophy document.
- Added Master Project Specification v2.0 draft.
- Added Roadmap v3.0 with block-based planning instead of linear numeric stages.
- Added draft SRS, SAD, LAS Platform, Calculation Engine, Geological Modeling, UI/UX, Database and Testing specifications.
- Marked AI Assistant as excluded from the current roadmap.
- Marked Licensing / Hardware ID / Activation as deferred and optional.
- Reprioritized LAS Platform Professional as the first implementation block after documentation approval.

## gas-ratio-pro-updated-135

- Added Performance & Optimization Foundation backend module.
- Added project-level `performance_optimization.json` with normalized metrics, cache entries and optimization recommendations.
- Added timer measurement context manager, lightweight project cache with TTL/invalidation, memory estimation helpers and performance manifest builder.
- Added UI helper tables and regression tests for performance metrics, cache behavior, recommendations and manifest generation.


## gas-ratio-pro-updated-97

- Added `docs/eula.md` as the application End User License Agreement.
- Replaced the licensing page EULA placeholder with a real in-app EULA document panel.
- Updated project plan and user guide to point to License manager as the next licensing item.

## Application Licensing Page

- Added a dedicated `Лицензия` application tab for proprietary licensing and commercial-use rules.
- Connected dashboard quick action, main navigation and command palette to the license page.
- Rendered product identity, owner, copyright, contact, EULA placeholder and full `LICENSE` text in high-contrast adaptive panels.


## Dashboard 3.0

- Replaced the failed sparse dashboard regression with a complete Dashboard 3.0 layout.
- Restored useful information panels: project statistics, recent projects, recent LAS files, recent calculations, recent activity, project health and license status.
- Added a product-style left navigation rail and a compact overview header.
- Centered and constrained the branded background image for the dashboard shell.
- Kept duplicate `Open...` buttons out of the dashboard.


## Unreleased

- Added LAS visualization quality metadata for sampling, missing points and depth gaps.

- Added Curve Manager category tools for LAS curves with automatic category suggestions, manual overrides, category history, undo support, UI summary tables, metadata references and tests.


- Добавлена индексация файлов Project Database: `project_index.json` хранит metadata файлов активного проекта, SHA-256 и проверку отсутствующих/измененных файлов без копирования данных.

## Unreleased

- Добавлено месторождение в Well Manager: значение хранится как metadata `field`, нормализуется как короткая строка и отображается в карточке скважины и Project Explorer без изменения LAS-версий.

- Добавлена отметка GL в Well Manager: значение хранится как metadata `gl_m`, валидируется в метрах, отображается рядом с KB и показывает разницу `KB-GL` при наличии обеих отметок.

- Добавлена metadata-only карточка скважины Well Manager: статус, комментарий и отображение состояния карточки в Project Explorer без чтения LAS-пayload.

- Добавлено metadata-only перемещение объектов в Project Explorer: скважины можно переносить между группами, а скважины, LAS-версии, расчеты и экспорты добавлять в пользовательские папки без копирования данных.

- Добавлены пользовательские папки Project Explorer: `project_folders.json` хранит metadata-ссылки на объекты дерева без копирования LAS или расчетных таблиц.

- Добавлен компактный журнал действий по сохраненным расчетам проекта: сохранение snapshot, открытие snapshot в графиках, сравнение snapshots и скачивание CSV/XLSX/HTML-выгрузок.

- Added project calculation open warnings for saved snapshots that have no depth/DEPT/MD column or incomplete key gas mapping before sending them to interpretation graphs.
# Gas Ratio Interpreter v0.3

Локальное инженерное приложение для импорта газовых данных, сопоставления колонок,
расчета газовых коэффициентов, построения Pixler/ternary палеток, LAS-корреляции
и предварительной интерпретации интервалов по правилам.


## Быстрый старт

Требования:

- Windows 10/11, Linux или macOS
- Python 3.11+
- Git

Команды для Windows PowerShell:

```powershell
git clone <repo-url> gas-ratio-pro
cd gas-ratio-pro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest
python scripts/preflight.py
python -m streamlit run app/streamlit_app.py
```

После запуска Streamlit откроет локальный адрес вида:

```text
http://localhost:8501
```

Если проект уже находится на компьютере:

```powershell
cd C:\OSPanel\home\gas-ratio-pro
.\.venv\Scripts\Activate.ps1
python -m streamlit run app/streamlit_app.py
```

## Как проверить без рабочих данных

В проекте есть тестовые файлы:

```text
examples/sample_gas_data.csv
examples/sample_gas_data.las
```

Запустите приложение, загрузите LAS или CSV и оставьте автоматически найденную
строку заголовков. В интерфейсе должны появиться таблица расчетов, сводка
классификации, Pixler/ternary палетки и графики по глубине.

## Что умеет v0.3

- Импорт LAS, CSV, XLSX, XLSM.
- Мультизагрузка файлов в рабочем workflow с выбором набора данных.
- LAS-корреляция: загрузка нескольких LAS, распознавание ГИС/газовых кривых, сохранение настроек в локальный проект, соседние depth-треки, сравнение одной выбранной кривой между скважинами, печатный HTML-отчет, PNG/PDF/SVG экспорт и таблица выбранного интервала с CSV/XLSX/LAS-экспортом.
- LAS-редактор: проверка глубины, исправление убывающего порядка глубины, изменение шага, добавление строк, ручная правка, передача подготовленных данных в расчеты, точечное добавление строк по выбранному интервалу и сохранение подготовленного LAS в активный проект.
- Локальное хранение скважин в `data/wells/` с версиями и выгрузкой `CSV`, `XLSX`, `LAS`.
- Локальные проекты в `data/projects/<project_id>/`: карточка `project.json`, карточки скважин, версии исходных и подготовленных LAS проекта, открытие сохраненных LAS без повторной загрузки, расчетные snapshots с mapping/предупреждениями/CSV/XLSX, CSV/HTML-экспорт сравнения snapshots, настройки интерпретационных графиков, сохраненные версии экспортов и HTML-отчетов, ZIP-выгрузка выбранных версий в `LAS`, `XLSX`, `CSV`, архивирование ошибочно сохраненных версий и настройки LAS-корреляции `correlation_settings.json`.
- Чтение всех листов Excel.
- Автоматический поиск строки заголовков среди первых 50 строк.
- Ручной выбор строки заголовков.
- Автоматическое и ручное сопоставление колонок.
- Поддержка разных названий кривых: `Depth`, `DEPT`, `MD`, `CH4`, `Methane`, `i-C4`, `n-C4`, русские названия и другие алиасы.
- Расчет `Wh`, `Bh`, `BAR2`, Pixler ratios, ternary ratios, `oil_indicator`, `inverse_oil_indicator` и настраиваемого `Ch`.
- Предварительная инженерная классификация интервалов по проверяемым правилам.
- Pixler palette, ternary palette и depth tracks.
- Интерпретационные depth-графики с ручным диапазоном глубины, ручным X-масштабом, режимом `Планшет` для любых числовых параметров, LAS units в шапках треков, индивидуальными цветами треков, маркерами глубины и HTML-выгрузкой для печати, отдельным печатным отчетом выбранного интервала, таблицей маркеров и таблицей интерпретационных зон.
- Настройка Pixler/ternary палеток через `config/palettes.json`.
- Локальное диагностическое логирование в `logs/app.log`.
- Экспорт расчетной таблицы в CSV.
- Проектная выгрузка выбранных LAS-версий в ZIP с файлами `LAS`, `XLSX` и `CSV`.
- Сохранение расчетных snapshots проекта: расчетная таблица, mapping, режим `Ch`, предупреждения, выгрузки `CSV`/`XLSX` и CSV/HTML-экспорт сравнения двух snapshots.
- Сохранение настроек интерпретационных графиков проекта: треки, высота, диапазон глубины и X-scale.
- Сохранение версий экспортов проекта: HTML-отчеты графиков, печатные HTML-отчеты выбранных интервалов и CSV выбранных интервалов с последующим скачиванием из проекта.
- Pytest-набор для проверки расчетов, mapping, импорта, LAS, палеток, логирования и Streamlit-smoke.

## Важные ограничения

- Интерпретация является предварительной инженерной подсказкой.
- Результат требует проверки по ГИС, литологии, буровому контексту, фону, СПО, наращиваниям и рециркуляции.
- Формула `Ch` требует подтверждения по корпоративной методике.
- Границы зон Pixler/ternary в текущем конфиге являются черновыми и должны быть заменены на подтвержденные корпоративные линии.
- Планшетный renderer расширен: LAS units выводятся в шапке треков, порядок параметров берется из выбора пользователя, цвета и режимы заливки треков настраиваются, mud-gas preset добавляет типовые треки/маркеры, ручные интерпретационные зоны/интервалы включаются в печатный HTML-отчет. В плане остается дальнейшее уточнение расчетной методики и формул.
- PNG/PDF/SVG экспорт требует установленного `kaleido` из `requirements.txt`; полноценная база проектов планируется в следующих версиях.

## Карта документации

- [Установка и запуск](docs/setup.md)
- [План проекта](docs/project_plan.md)
- [Руководство пользователя](docs/user_guide.md)
- [Формат входных данных](docs/data_format.md)
- [План LAS-редактора](docs/las_editor_plan.md)
- [План multi-LAS корреляции](docs/las_correlation_plan.md)
- [Формулы](docs/formulas.md)
- [Mud gas analysis: литературный источник](docs/mud_gas_analysis_literature.md)
- [Конфигурация палеток](docs/palettes.md)
- [Логирование](docs/logging.md)
- [Архитектура и разработка](docs/development.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Правила ведения документации](docs/documentation_policy.md)
- [История изменений](CHANGELOG.md)

## Основные команды

```powershell
# Запуск тестов
python -m pytest

# Проверка готовности окружения
python scripts/preflight.py

# Запуск приложения
python -m streamlit run app/streamlit_app.py

# Просмотр последних строк лога
Get-Content logs/app.log -Tail 80

# Проверка текущего git-состояния
git status --short
```

- Добавлены координаты скважины в Well Manager: X/Y, широта/долгота, проверка диапазонов и отображение в Project Explorer.

## Dashboard responsive correction

- Reduced the low-content welcome rail on laptop widths so project statistics and activity panels fit without horizontal clipping.
- Centered the branded dashboard background and reduced its visual footprint for better readability.
- Added regression checks for laptop dashboard layout CSS rules.

## Dashboard UX Refactoring → Background Refinement

- Centered and contained the Dashboard 3.0 branded background artwork.
- Reduced dashboard background scale for notebook breakpoints.
- Added explicit 1366px, 1440px and 1600px background rules.
- Switched sidebar brand art from cover to contain to prevent cropping.

## Этап 128 — Geological Modeling Professional: Zone Manager

- Добавлен backend-слой Zone Manager для Geological Modeling Professional.
- Реализовано хранение инженерно утвержденных геологических зон в `geological_modeling.json` внутри проекта.
- Добавлены операции создания/обновления, удаления, фильтрации по скважине и типу зоны.
- Добавлены операции объединения смежных зон и разделения зоны по глубине.
- Добавлены цветовые схемы зон и табличное представление Zone Manager.
- Расширены тесты `tests/test_geological_modeling.py` для CRUD, merge/split, color scheme и валидации входных данных.


## gas-ratio-pro-updated-129

- Added Data Exchange Center foundation with project-level import/export records, exchange profiles, CSV/JSON/GeoJSON/XLSX helpers and project ZIP manifest export.
- Added validation tables for exchange issues and summary tables for Data Exchange records.
- Registered DLIS/LIS as planned professional exchange formats while keeping their binary parser/exporter for a later dedicated stage.
- Added tests for exchange CRUD, CSV/JSON/GeoJSON conversion, XLSX roundtrip, profiles, validation and project ZIP export.

## gas-ratio-pro-updated-130

- Added Advanced Plot Studio foundation: built-in professional layout presets for Triple Combo and Mud Gas Interpretation.
- Added template cloning for safe layout reuse across wells without overwriting source templates.
- Added renderer-independent preview specification with normalized track width percentages, curve payloads and annotation mapping.
- Added template validation issues and issue table helpers for export/rendering pre-checks.
- Added regression tests for presets, cloning, preview spec and validation.

## gas-ratio-pro-updated-131

- Added Advanced Correlation Studio Professional persistence layer with project-level correlation sessions in `correlation_studio.json`.
- Added session CRUD, status validation, table/summary helpers and project history integration.
- Added JSON import/export roundtrip for correlation sessions and export manifest generation for JSON/PNG/SVG/PDF targets.
- Connected persistent sessions with existing professional correlation primitives: markers, tie lines and depth alignments.
- Added regression tests for session CRUD, validation, JSON roundtrip, export manifest and marker object compatibility.

## gas-ratio-pro-updated-132

- Added Advanced Report Studio Professional backend layer.
- Added report packages with ordered reusable content blocks and report variables.
- Added package validation for missing sections, empty paragraphs and missing visual/table sources.
- Added renderer-independent render preview and render manifest for future PDF/DOCX/HTML adapters.
- Added deterministic lightweight HTML preview generation without Streamlit dependency.
- Added report export job status updates with project history integration.
- Added UI helper tables for packages, blocks and validation issues.
- Added regression tests for professional report packages, manifests, validation and job statuses.

## gas-ratio-pro-updated-133

- Added Plugin SDK foundation backend layer with project-level `plugin_sdk.json` registry.
- Added validated plugin manifests, SDK schema marker, SemVer checks, permission scopes and extension-point validation.
- Added plugin CRUD/status management with project history integration and safe enablement checks.
- Added plugin hook registry for supported application events and renderer/workflow/importer extension points.
- Added scaffold generator with `plugin.json`, `plugin.py` and README template for external plugin developers.
- Added API registry manifest for enabled plugins and UI helper tables for plugins, hooks and validation issues.
- Added JSON import/export helpers and regression tests for manifest roundtrip, registry, hooks, scaffold and validation.


## 134
- Added Scripting API foundation.

## Этап 136 — Release Candidate Stabilization

- Добавлен backend-слой `projects/release_candidate.py` для подготовки Release Candidate без включения лицензирования.
- Добавлена схема `gas-ratio-pro.release-candidate.v1` и проектный файл `release_candidate.json`.
- Реализованы release quality gates: source, documentation, tests, configuration, artifacts, performance, security и release.
- Добавлены проверки обязательных файлов, CHANGELOG, test inventory и py_compile для ключевых каталогов проекта.
- Добавлен release manifest со сводкой статусов, checklist и детерминированным file inventory fingerprint.
- Добавлена валидация release manifest и сохранение manifest в проект с записью в историю.
- Добавлены UI helper tables для будущей страницы Release Candidate Audit.
- Модуль экспортирован через `projects/__init__.py`.
- Добавлены regression-тесты Release Candidate.
## Phase II Implementation — LAS Platform Professional B.1

- Started implementation from `ROADMAP_v3.0` using Specification First workflow.
- Added `las_editor/las_creator.py` for LAS creation from scratch.
- Added `LasCreationSpec`, `LasCurveSpec`, `LasCreationResult` and LAS validation issue objects.
- Added built-in LAS templates: `empty`, `mud_gas`, `petrophysics`.
- Added depth index generation, mandatory LAS sections and UTF-8 LAS writer text/bytes output.
- Added basic professional curve operations: add non-depth curve, delete non-depth curve, mnemonic/unit normalization.
- Exported LAS creation API through `las_editor/__init__.py`.
- Added regression tests for LAS Creation Wizard backend, templates, validation and curve add/delete operations.
## Phase II Implementation — LAS Platform Professional B.6

- Added LAS Safe Export Professional foundation with safe destination validation.
- Added built-in LAS template profiles for empty, mud gas and petrophysical LAS workflows.
- Added export manifests with schema marker, status, target/source paths, data size, row/curve counts and validation summary.
- Added source-overwrite protection: exported LAS files cannot be saved over the original source LAS path.
- Added existing-target protection unless overwrite is explicitly enabled for a non-source target.
- Added safe LAS text/document export helpers and UI-ready export/template tables.
- Exported safe export API through `las_editor/__init__.py`.
- Added regression tests for template profiles, safe path validation, source overwrite blocking and safe LAS writing.

## Phase II — B.9 LAS Curve Import Professional Foundation

- Added `las_editor/curve_importer.py`.
- Added safe CSV/XLSX curve import helpers.
- Added curve import planning before merge.
- Added exact, nearest and interpolation depth matching policies.
- Added conflict policies: skip, suffix and replace.
- Added import manifest, UI-ready plan tables and issue tables.
- Added tests for curve import workflow.

## Phase II — B.10 LAS Curve Calculator Professional Foundation

- Added `las_editor/curve_calculator.py`.
- Added safe formula validation without Python `eval`/`exec`.
- Added calculated curve workflow for working copies of LAS ASCII tables.
- Added built-in formula templates for Haworth wetness/balance/character ratios, Pixler C1/C2, oil indicator, inverse oil indicator, Net/Gross and porosity percent.
- Added supported formula functions: `IF`, `ABS`, `SQRT`, `LOG`, `LOG10`, `EXP`, `ROUND`, `MIN`, `MAX`.
- Added preview rows, calculated curve specs, UI-ready issue/template tables and calculation manifest.
- Exported Curve Calculator API through `las_editor/__init__.py`.
- Added regression tests for formula validation, calculation, templates, IF logic, manifest and safe non-destructive behavior.

## Phase II — B.11 LAS Quality Control Professional Foundation

- Added `las_editor/las_quality_control.py`.
- Added LAS quality-control profiles for common well-log curves.
- Added depth QC: duplicate samples, non-monotonic depth and missing/irregular depth intervals.
- Added curve QC: missing values, negative values, expected range checks, spikes, flat-line segments, statistical outliers and unit mismatch warnings.
- Added UI-ready issue/profile tables.
- Added quality-control manifest and Markdown report renderer.
- Exported LAS Quality Control API through `las_editor/__init__.py`.
- Added regression tests for the new QC foundation.

## Phase II B.12 — LAS Processing Pipeline Professional Foundation

- Added `las_editor/las_processing_pipeline.py`.
- Added reproducible non-destructive LAS curve processing pipelines.
- Added operations: moving average, median filter, despike, null filling, min-max normalization, z-score normalization, clipping and depth resampling.
- Added processing plan validation, operation history, processing manifest, preview data and Markdown processing report.
- Exported the processing API through `las_editor/__init__.py`.
- Added regression tests in `tests/test_las_processing_pipeline_professional.py`.

## Phase II B.13 — Mud Gas Interpretation Toolkit Foundation

- Added `las_editor/mud_gas_interpretation.py`.
- Added Haworth wetness, balance and character ratio calculation support.
- Added Pixler C1/C2 fluid-character classification support.
- Added Oil Indicator and Inverse Oil Indicator classification support.
- Added combined per-depth mud-gas interpretation rows.
- Added interval summaries, UI-ready tables, Markdown report and interpretation manifest.
- Exported the mud gas interpretation API through `las_editor/__init__.py`.
- Added regression tests in `tests/test_mud_gas_interpretation_professional.py`.

## Phase II - B.16 Petrophysical Workspace Foundation

- Added `las_editor/petrophysical_workspace.py`.
- Added transparent petrophysical calculations for Vsh, PHIE, Archie Sw, SO, RES/NET/PAY and NG flags.
- Added petrophysical interval summaries, manifest generation and Markdown report rendering.
- Added profile tests for the new Petrophysical Workspace foundation.

## Phase II - B.17 Advanced Saturation Models Foundation

- Added `las_editor/advanced_saturation_models.py`.
- Added advanced water-saturation calculations: Archie, Simandoux, Indonesia and Dual Water foundation.
- Added deterministic model comparison by interval with average Vsh, model spread, recommendation and confidence.
- Added validation for required curves, numeric model parameters and output curve conflicts.
- Added manifest generation, UI-ready issue/comparison tables and Markdown report rendering.
- Exported Advanced Saturation Models API through `las_editor/__init__.py`.
- Added regression tests in `tests/test_advanced_saturation_models.py`.

## Phase II - B.18 Petrophysical Crossplot Workspace Foundation

- Added `las_editor/petrophysical_crossplot_workspace.py`.
- Added backend crossplot specifications for Pickett, Hingle, Buckles, Density-Neutron, Sonic-Density and GR-Resistivity plots.
- Added depth-window filtering, linear trend summaries, deterministic cluster summaries and UI-ready tables.
- Added crossplot manifest generation and Markdown report rendering.
- Exported Petrophysical Crossplot Workspace API through `las_editor/__init__.py`.
- Added regression tests in `tests/test_petrophysical_crossplot_workspace.py`.

## Phase II — B.19 Reservoir Property Calculator Foundation

- Added `las_editor/reservoir_property_calculator.py`.
- Added deterministic BRV, NRV, PV, HCPV, OOIP and OGIP foundation calculations.
- Added interval summaries, recovery estimates, manifests, Markdown reporting and UI-ready tables.
- Added tests for reservoir volumetric calculations.

## Phase II — B.20 Petrophysical Report Package Foundation

- Added `las_editor/petrophysical_report_package.py`.
- Added normalized report sections for Petrophysical Workspace, Advanced Saturation Models, Petrophysical Crossplots, Well Intervals and Reservoir Volumes.
- Added deterministic package manifest, Markdown report renderer and UI-ready section/issue tables.
- Added evidence source aggregation for report packages.
- Exported Petrophysical Report Package API through `las_editor/__init__.py`.
- Added regression tests in `tests/test_petrophysical_report_package.py`.

## Phase II — C.1 Property Modeling Workspace Foundation

- Added `projects/property_modeling_workspace.py`.
- Added property cube metadata registry for facies, lithology, NG, porosity, permeability and saturation properties.
- Added fluid contact and geometry property foundation.
- Added Net/Gross calculation from facies labels.
- Added property statistics, manifest, UI-ready tables and Markdown report.
- Added profile tests for Property Modeling Workspace.

## Phase II — C.2 Facies Modeling Workspace Foundation

- Added `projects/facies_modeling_workspace.py`.
- Added facies registry with reservoir/pay candidate flags and color metadata.
- Added zone-based facies modeling settings.
- Added vertical proportion curve calculation.
- Added discrete facies statistics and run-length summary.
- Added facies simulation job manifest foundation.
- Added UI-ready tables and Markdown reporting.
- Added profile tests for Facies Modeling Workspace.

## Phase II — C.3 Geostatistics Workspace Foundation

- Added `projects/geostatistics_workspace.py`.
- Added experimental variogram calculation from spatial samples.
- Added theoretical variogram models: spherical, exponential, gaussian, linear and nugget.
- Added deterministic foundation model fitting for experimental variogram bins.
- Added search ellipsoid metadata for future Kriging/SGS workflows.
- Added geostatistics jobs, manifest generation, UI-ready tables and Markdown report rendering.
- Exported Geostatistics Workspace API through `projects/__init__.py`.
- Added regression tests in `tests/test_geostatistics_workspace.py`.

## Phase II — C.5 Property Simulation Engine Foundation

- Added `projects/property_simulation_engine.py`.
- Added Sequential Gaussian Simulation foundation for continuous property realizations.
- Added Sequential Indicator Simulation foundation for facies/discrete property realizations.
- Added reproducible seed-based simulation, realization metadata, uncertainty and confidence fields.
- Added simulation job registry, manifest generation, UI-ready tables and Markdown report rendering.
- Exported Property Simulation Engine API through `projects/__init__.py`.
- Added regression tests in `tests/test_property_simulation_engine.py`.

## Phase II - C.6 Fluid Contacts & Geometrical Properties Foundation

- Added `projects/fluid_contacts_geometry.py`.
- Added fluid contact registry for OWC, GOC, GWC, FWL and custom contacts.
- Added constant/surface contact metadata with confidence and source tracking.
- Added geometry calculations: Cell Height, Cell Volume, Bulk Volume, Depth, Elevation, Relative Depth and Above Contact.
- Added contact set coding for gas/oil/water zones.
- Added job registry, manifest, Markdown report and UI-ready tables.
- Added tests for contact classification, geometry properties, manifest and reports.

## Phase II — C.7 Reservoir Volumetrics Workspace Foundation

- Added `projects/reservoir_volumetrics_workspace.py`.
- Added grid/property-level volumetric calculations: BRV, NRV, PV, HCPV.
- Added foundation OOIP/OGIP and recoverable estimates.
- Added cutoffs for porosity, water saturation, net flag and pay flag.
- Added zone summaries, uncertainty summary, manifest, Markdown report and UI-ready tables.
- Added tests for reservoir volumetrics workspace.

## Phase II - C.8 Geological Model Workspace Foundation

- Added `projects/geological_model_workspace.py`.
- Added Geological Model Workspace foundation with model/grid/horizon/zone/surface/fault registries.
- Added model links for wells, intervals, facies, property cubes and volumetrics.
- Added workspace validation, manifest, Markdown report and UI-ready helper tables.
- Added tests for C.8 workspace persistence, validation and reporting.

## Phase II - C.9 Structural Modeling Workspace Foundation

- Added `projects/structural_modeling_workspace.py`.
- Added Structural Framework registry, Horizon Manager, Horizon Groups, Fault Manager Foundation, Zone/Layer Framework and Surface registry.
- Added structural validation for missing horizons/surfaces, invalid depth ranges, top/base consistency and fault horizon links.
- Added layer generation helper, manifest, Markdown report and UI-ready helper tables.
- Exported Structural Modeling Workspace API through `projects/__init__.py`.
- Added regression tests in `tests/test_structural_modeling_workspace.py`.

## Phase II - C.10 Geological Model Integration Workspace Foundation

- Added `projects/geological_model_integration_workspace.py`.
- Added integrated model object registry for geological model, structural model, grids, facies, property cubes, volumetrics, wells, LAS datasets, reports and source documents.
- Added dependency graph foundation for tracing model inputs, outputs, derived objects and documentation references.
- Added integration views, validation, manifest, Markdown report and UI-ready helper tables.
- Exported Geological Model Integration Workspace API through `projects/__init__.py`.
- Added regression tests in `tests/test_geological_model_integration_workspace.py`.

## Engineering Review & Project Redesign — Roadmap v4.0

- Added full project audit document.
- Added ROADMAP_v4.0 focused on UI/UX, Plot Studio, Report Studio, LAS visibility and Geological Modeling UI.
- Added MASTER_PROJECT_SPECIFICATION_v3.0.
- Added LAS Workspace Redesign specification.
- Added Plot Studio Professional Redesign specification.
- Added Report Studio 2.0 specification.
- Added Geological Modeling Workspace Redesign specification.
- Added implementation plan after Roadmap v4.0.
- Marked triangular diagram as requiring repair/redesign.
- Deferred project packaging until core workflows and UI are corrected.

## Project Manager 2.0 backup restore foundation

- Added managed project backup restore from Project Manager 2.0 ZIP archives.
- Added safe ZIP extraction with path traversal protection.
- Added overwrite protection for existing project directories.
- Added service-layer backup, restore and recovery checkpoint methods.
- Added tests for restore workflow, overwrite protection and service integration.

## Application State Controller cleanup foundation

- Added generic application-owned session value helpers to `ApplicationStateController`.
- Routed interpretation dataset storage through the application-state controller.
- Added regression tests preventing direct `st.session_state` writes in the interpretation storage helper.

## Architecture Review LTS Freeze Checklist

- Added Architecture Review documentation for the post-Sprint 1.5 gate.
- Added Core LTS Freeze checklist before Sprint 2 Workspace Framework.
- Added regression tests for required freeze-gate sections and core architecture rules.


## Hydrocarbon Interval Engine v9

- Added Method Registry for report-facing calculation methods.
- Added interval evidence provenance metadata.
- Added method/source fields to structured evidence records.
- Updated hydrocarbon interval schema to v9.

## Hydrocarbon Interval Engine v11

- Added auditable interpretation rule model.
- Added rule traces for interval-level decision explanation.
- Added applied rule IDs to interval/table/marker payloads.
- Added interpretation status for practical reporting workflows.
- Added rule-based confidence adjustment factors.
- Updated interval schema to `gas-ratio-pro/hydrocarbon-intervals/v11`.


## Hydrocarbon Interval Engine v12

- Added validation case model for practical geology scenarios.
- Added validation result export rows for QA tables.
- Added public API contract for report, plot, UI and export consumers.
- Updated schema to `gas-ratio-pro/hydrocarbon-intervals/v12`.

## Hydrocarbon Interval Engine v13

- Added `HydrocarbonInterpretationContext`.
- Added data/geological confidence split.
- Added engineer-facing `decision_level`.
- Added grouped `evidence_tree` for UI/report explanations.
- Added neighbor/barrier context enrichment.
- Updated schema to `gas-ratio-pro/hydrocarbon-intervals/v13`.

## Hydrocarbon Interpretation Engine v15

- Added `InterpretationExplanation` as the engineer-facing explanation package for every interval.
- Added explanation summaries to interval, marker and public API payloads.
- Added cautious preliminary interpretation wording and recommendation/limitation blocks.
- Updated schema to `gas-ratio-pro/hydrocarbon-intervals/v15`.

## Hydrocarbon Interval Engine v14

- Stabilized the public Hydrocarbon Interval Engine payload for downstream UI, plot, report and export consumers.
- Added engineer-facing result summary that focuses on intervals, fluid type, confidence and review status instead of internal row counters.
- Added technical payload opt-in for diagnostics, row counts, method registry and expert/debug views.
- Updated schema to `gas-ratio-pro/hydrocarbon-intervals/v14`.

## Hydrocarbon Interpretation Engine v17

- Added built-in Validation Dataset v2 for regression checks of practical geological scenarios.
- Added validation catalog helpers: `hydrocarbon_validation_cases`, `hydrocarbon_validation_case_frame`, `hydrocarbon_validation_catalog_rows`.
- Added `run_hydrocarbon_validation_suite` as a public regression suite entry point.
- Added no-numeric-data interpretation rule for missing gas-ratio evidence.
- Updated public API contract and schema to `gas-ratio-pro/hydrocarbon-intervals/v17`.


## v19 - Hydrocarbon Interpretation Engine v1.0 Freeze Gate

- Added `HYDROCARBON_ENGINE_VERSION = HIE v1.0`.
- Added `HYDROCARBON_ENGINE_STATUS = frozen`.
- Added `hydrocarbon_engine_freeze_status()` as the public release gate.
- Updated schema to `gas-ratio-pro/hydrocarbon-intervals/v19`.
- Updated freeze and architecture audit documentation.
- Added regression test for freeze status.
## PRS-1 — Executive Summary Engine foundation

- Added engineer-first Executive Summary model for Professional Reporting System.
- Added professional report table sequence without breaking legacy technical table payloads.
- Updated print report header to focus on project and analysis interval instead of technical row counters.
- Added regression tests for summary behavior and report header noise reduction.


## v22 — Engineering report profile

### Added
- Added an engineer-first print/report profile for interval reports.
- Added an expert profile for technical appendices with row-count-oriented tables, statistics, and raw bounded data.

### Changed
- Default interval print reports now prioritize executive summary, interval cards, recommendations and limitations.
- Technical row counters, preliminary class counts, numeric statistics and raw row tables are no longer printed in the default engineering profile.

### Validation
- Regression suite: 1071 passed.

## v23 — Professional Well Log Plot Engine foundation

### Added
- Added `reports/well_log_plot.py` as the first implementation of the Professional Plot/Tablet Engine.
- Added deterministic depth-based downsampling to avoid unreadable fence-like plots on large LAS datasets.
- Added a report-ready well-log tablet builder with one common reversed depth axis.
- Added an interpreted interval track with interval labels, fluid type and confidence.
- Added interval zone overlays across all tracks using the frozen Hydrocarbon Interpretation Engine interval model.

### Changed
- Professional plotting now consumes interpreted intervals from HIE instead of recomputing interval logic in visualization code.
- The plotting layer now has a clear separation between engineering interpretation data and visual rendering.

### Validation
- Added regression tests for downsampling, interval overlays and safe track filtering.

## v24 — README cleanup and documentation policy

### Changed
- Reworked `README.md` into a stable project overview instead of a development diary.
- Removed sprint/version-specific implementation notes from the README.
- Added a README policy document to keep progress notes, release notes and technical history out of the public project introduction.

### Rationale
- README should explain what GAS RATIO PRO is, what it does, how to install and run it, and where to find documentation.
- Development history belongs in changelog, roadmap, progress and architecture documents.

## v25 — Presentation Model foundation

### Added
- Added `reports/presentation_model.py` as the single source of presentation data for reports, plots, UI and future PDF/DOCX export.
- Added `PresentationModel` and `PresentationMetadata`.
- Connected `HydrocarbonReportPayload` to the presentation model.
- Added optional professional well-log plot composition through the same model.
- Added documentation for the Presentation Model contract.

### Changed
- Report payloads can now pass one composed presentation object downstream instead of letting each renderer rebuild executive summary, interval cards and plots independently.

### Rationale
- Reports, plots, PDF/DOCX exports and UI cards must use the same interpreted intervals, confidence, explanations, recommendations and limitations.

## v26 — Presentation HTML renderer

### Added
- Added `reports/presentation_html.py` as a print-ready renderer on top of `PresentationModel`.
- Added engineering/expert table profile selection without rebuilding report data.
- Added optional professional well-log plot embedding from the same presentation model.
- Added documentation for the Presentation HTML renderer contract.

### Changed
- The report presentation layer now has a dedicated HTML renderer that can become the basis for browser print/PDF export.
- Engineering reports continue to hide technical diagnostics from the first report pages, while expert reports can include them explicitly.

### Rationale
- HTML, PDF, DOCX and UI exports must consume the same `PresentationModel` so report outputs stay consistent with HIE, interval cards and professional plots.

## v29 — Document Model foundation

Added:
- Renderer-neutral `EngineeringDocument` document object model.
- `DocumentTable`, `DocumentPlot`, `DocumentNotice` blocks.
- HTML renderer now consumes the document model instead of composing sections directly from `PresentationModel`.

Purpose:
- Keep one source of engineering interpretation for HTML, future PDF, DOCX and UI renderers.

## v30 - PDF Renderer Foundation

### Added
- Added `reports/presentation_pdf.py` for PDF rendering from `EngineeringDocument`.
- Added PDF export package support with manifest JSON.
- Added documentation for the PDF renderer foundation.

### Notes
- Plot blocks are preserved as document blocks; raster/SVG plot embedding is planned as the next renderer backend increment.

## v32 — Presentation Bundle Export

### Added
- Added `export_presentation_bundle_package()` for HTML, PDF and DOCX export from one `PresentationModel`.
- Added `PresentationBundleExportResult`.
- Added one bundle manifest with exported files, report profile, table titles, figure count and consistency flags.
- Added consistency checks to prevent HTML/PDF/DOCX report divergence.

### Rationale
- Engineering interpretation must exist once and be rendered consistently across all report formats.
- If one format starts showing different tables or figures, the export package now fails loudly instead of producing conflicting reports.

### Validation
- Presentation export, HTML, PDF, DOCX and Document Model tests passed together.

## v33 - Presentation Layer Freeze

### Added

- Added `reports/presentation_freeze.py`.
- Added a Presentation Layer v1 freeze gate.
- Added consistency checks for PresentationModel, EngineeringDocument and HTML/PDF/DOCX renderers.
- Added `docs/PRESENTATION_LAYER_FREEZE_V33.md`.

### Changed

- Documented the rule that engineering presentation content must be assembled once and rendered by format-specific backends without duplicated interpretation logic.

### Next

- Start Modern UI / Workspace integration on top of the frozen Presentation Layer.

## v34 - Presentation UI Integration Foundation

### Added

- Added `reports/presentation_ui.py` as a renderer-neutral adapter for report/export controls.
- Added stable engineering/expert report profile options for UI selectors.
- Added stable HTML/PDF/DOCX/bundle export format options.
- Added safe report basename generation for user/project/well labels.
- Added tests for profile normalization, export format normalization and export options mapping.

### Rationale

The Streamlit UI must not duplicate presentation/export rules. It should pass normalized user choices to the Presentation Layer, while HTML/PDF/DOCX continue to render from one `PresentationModel`.

## v36 - Workspace Reset Foundation

### Added
- Framework-neutral workspace reset controller for Modern UI.
- Safe preview of affected session-state keys before reset.
- Reset modes for derived results, active LAS, active workspace and full active context.
- Confirmation requirement for context-changing reset actions.

### Notes
- Reset clears temporary application state only and does not delete project files from disk.


## v37 - Workspace Session Manager

### Added
- Added `core/workspace_session.py` for lightweight workspace session capture, save, load and restore.
- Added `WorkspaceSession` descriptor for active project, well, LAS, workspace, selected intervals, active report/plot, recent exports and window layout.
- Added restore conflict policies: `overwrite` and `preserve`.
- Added JSON persistence for sessions without storing heavy LAS dataframes, rendered plots or calculation dumps.
- Added documentation `docs/WORKSPACE_SESSION_MANAGER_V37.md`.

### Rationale
- Users should be able to close and reopen Gas Ratio Pro and continue work from the same well, report, tablet and interval context.
- Workspace sessions are UI/workflow descriptors, not geological data stores.

## v55 Workbench lifecycle foundation

- Added framework-neutral Workbench lifecycle manager for initialization, workspace opening and workspace closing.
- Added lightweight WorkspaceContext payload for project, well, LAS, workspace, navigation, dock pane, selection and renderer state.
- Added Workbench Selection Service for selected report, plot and interval references.
- Added typed Workbench events for navigation, active panel, lifecycle and selection changes.
- Added regression tests for lifecycle operations, context serialization and selection behavior.

## V56 Modern Workbench Tool Registry

- Added Workbench tool registry and tool manager.
- Added default engineering tool descriptors.
- Added command-backed tool activation and renderer action support.
- Added Workbench tool state persistence in workspace sessions.
- Added Workbench tool registry tests and kept release export QA green.


## v63 - LAS Visualization Interval Overlays

### Added
- Added renderer-neutral interval overlay payloads for LAS visualization.
- Added selected interval bands with depth range, label, fluid type, confidence and track scope.
- Added invalid interval safety flag for overlay generation.
- Added tests for overlay payload generation and invalid interval handling.

### Notes
- Plotting backend code is still not part of the service layer.
- Workbench UI state still receives only lightweight serializable payloads, not raw LAS dataframes.

## v69 - Visualization Export Manifest Contract

### Added
- Added export manifest metadata for prepared Visualization Engine previews.
- Added bundle consistency flag for visualization preview propagation.
- Added tests proving visualization previews are tracked in report bundles without exposing raw dataframe content.

### Notes
- HTML can embed SVG directly.
- PDF and DOCX still preserve renderer-safe placeholders; binary/vector insertion remains a dedicated renderer backend task.

## v74 Visualization Engine Core Foundation

- Added renderer-neutral Visualization Engine scene contracts.
- Added layer manager for curve layers and interval overlay layers.
- Added shared depth synchronization contract across LAS tracks.
- Exposed `engine_scene` from LAS visualization payloads for future UI and export renderers.

## v76
- Added the first Visualization Engine SVG scene renderer adapter.
- Added scene-renderer output to LAS visualization payloads.
- Added SVG renderer regression coverage and empty-scene diagnostics.

## v77
- Added a source-neutral Visualization Domain Model and LAS payload adapter.
- Inserted the domain-model stage into the Visualization Scene Pipeline.
- Added roadmap and architecture documentation for the domain-first Layout Engine sequence.
- Added regression tests for normalized tracks, curves, intervals and raw-data safety.

## v80
- Added the renderer-neutral Visualization Render Model foundation.
- Added deterministic drawing primitive and clipping contracts.
- Added Render Model to the Visualization Scene Pipeline.
- Added safe empty-layout diagnostics and regression tests.
- Kept the existing SVG scene renderer as a compatibility path during migration.

## v81
- Added renderer-neutral axis and grid contracts.
- Added linear depth and curve ticks plus logarithmic curve ticks.
- Added printable major/minor grid and axis label primitives to Render Model.
- Added the `axis_grid` stage to Visualization Scene Pipeline.
- Added regression tests for linear, logarithmic and invalid-axis scenarios.

## v82
- Added renderer-neutral Visualization Track Engine contracts.
- Added ordered track models with visibility, printable, pinned and grouping state.
- Added track/header/axis/plot region contracts and shared depth viewports.
- Added the `track_model` stage to Visualization Scene Pipeline.
- Connected Render Model metadata and visible-track filtering to Track Model.
- Added regression tests for ordering, visibility fallback and empty contracts.


## v83
- Moved LAS curve geometry into renderer-neutral polyline primitives.
- Moved interpreted interval bands and labels into clipped Render Model primitives.
- Updated the SVG renderer to serialize `VisualizationRenderModel` primitives for pipeline inputs.
- Kept direct Scene rendering only as a temporary compatibility fallback.
- Added regression coverage for curve, overlay and Render Model SVG output.

## v85
- Added renderer-neutral Label and Legend Engine contracts.
- Added prepared track titles and curve labels with engineering units.
- Added curve and interval legend metadata with deterministic ordering.
- Added label overflow limits, truncation and basic collision spacing.
- Added the `label_legend` stage to Visualization Scene Pipeline.
- Connected prepared labels to Render Model text primitives.
- Added regression tests and kept export release QA green.
## v86
- Added renderer-neutral Visualization Print Layout Engine contracts.
- Added A4, A3, A2 and A1 page sizes with portrait and landscape orientation.
- Added millimetre margins, fit-page, fit-width and actual-size scale modes.
- Added printable, content and legend regions in physical point geometry.
- Added the `print_layout` stage to Visualization Scene Pipeline.
- Connected print-layout metadata to Visualization Render Model.
- Added regression tests and kept release export QA green.


## Visualization SVG Renderer Parity Foundation v87

- Added a renderer-neutral parity validator for concrete visualization artifacts.
- SVG renderer now applies Print Layout page geometry and content transforms.
- SVG results now expose primitive and clip counts for automated contract validation.
- Added parity regression tests for Render Model counts and print-layout application.

## v89 Visualization Geometry Signature

- Added a canonical SHA-256 geometry signature for printable Render Model primitives, clip regions and first-page print transform.
- SVG and PDF renderer results now publish the same geometry signature when they consume the same pipeline result.
- Renderer parity validation now detects missing or mismatched geometry signatures in addition to primitive and clip counts.
- Added regression tests for cross-renderer signature equality and tamper detection.
## v90

- Added Visualization Asset Registry for SVG, PDF, Render Model and geometry contract assets built from one pipeline result.
- Added shared geometry signature and SHA-256 metadata for every visualization asset.
- Added tests proving that bundle creation does not require rebuilding Scene or Layout.


## v91 Visualization Performance Engine

- Added deterministic cache keys for renderer-neutral visualization contracts.
- Added a bounded LRU Render Model cache and typed cache restoration.
- Added performance metadata to the scene pipeline and validation output.
- Added tests for cache hits, cache bypass, LRU eviction and cache-key invalidation.

## v92 Visualization Adaptive Downsampling

- Added viewport-aware extrema-preserving reduction for dense LAS curves.
- Added configurable sampling density and minimum point budgets.
- Added sampling options to deterministic Render Model cache keys.
- Added targeted Render Model cache invalidation.
- Added regression tests for dense curves, cache-key changes and exact invalidation.

## v175 Documentation consolidation

- Added a single active roadmap in `docs/PROJECT_ROADMAP.md`.
- Added factual current status and next permitted increment in `docs/PROJECT_STATUS.md`.
- Added `docs/README.md` as the documentation entry point and precedence map.
- Archived version-specific implementation notes under `docs/archive/releases/`.
- Archived replaced project plans and progress logs under `docs/archive/legacy_plans/`.
- Converted legacy `project_plan.md` and `PROJECT_PROGRESS_NEXT_STEP.md` into compatibility entry points.
- Defined a policy that future version notes belong in `CHANGELOG.md` unless they describe a stable public contract.

## v180 LAS Viewer open workflow

- Added a real LAS-open application workflow using the existing LAS importer.
- Validated LAS content and supported depth channels before mutating project storage.
- Persisted accepted LAS files through the existing `LasManagerService`.
- Connected imported LAS data to visualization payload and compact `LasViewerSession` contracts.
- Prevented raw DataFrame storage in UI/session contracts.
- Added rollback and regression coverage for invalid LAS, missing depth channels and unsupported extensions.

## v181 LAS Viewer multi-track construction

- Added a renderer-neutral application service that builds a complete multi-track viewer from the LAS-open payload.
- Excluded empty, fully null and non-finite curves before viewer session and render-model construction.
- Rebuilt deterministic track membership and created missing track descriptors without UI logic.
- Connected normalized tracks and curves to the existing `LasViewerSession` and `LasViewerRenderPipeline`.
- Preserved compact serializable state and guaranteed that raw DataFrames are not retained.
- Added unit, integration and real-LAS regression coverage.

## v182 LAS Viewer shared interaction

- Added a renderer-neutral application controller for one shared depth viewport across all visible LAS Viewer tracks.
- Integrated synchronized cursor overlays for every visible track region using the existing track synchronization engine.
- Integrated one logical selection state and non-printable selection overlays through the existing selection synchronization engine.
- Ensured viewport changes clear stale cursor state while preserving logical selection.
- Added compact serializable interaction snapshots without retaining raw DataFrames.
- Added unit and regression coverage for shared viewport, cursor, selection and renderer-neutral contracts.


## v185 LAS Viewer current-view export

- Added a renderer-neutral LAS Viewer export service for the already computed current viewport.
- Reused the existing Visualization Engine pipeline without rebuilding layout in UI code.
- Exported matching SVG and PDF artifacts with one canonical geometry signature.
- Applied strict Render Validation blocking before artifact creation.
- Added cross-renderer Export QA and compact artifact metadata without raw DataFrames.
- Added unit, integration and invalid-layout regression coverage.


## v186 LAS Viewer curve validation and error handling

- Added one renderer-neutral curve validation contract before LAS Viewer layout/render construction.
- Classified missing identifiers, invalid depth samples, empty curves, all-null curves, partial null values and unsupported units.
- Excluded non-renderable curves without leaving empty tracks or corrupting track widths/order.
- Preserved recoverable curves, recorded contiguous null intervals and exposed compact per-curve quality metadata.
- Normalized supported units and downgraded unsupported units to `unknown` with explicit diagnostics instead of crashing the viewer.
- Preserved export/render compatibility and guaranteed that validation state contains no raw DataFrame.
- Completed LAS Viewer Stage 2 and activated Modern Workbench Stage 3.


## v190 Workbench primary LAS Viewer module

- Added one application-level lifecycle for LAS Viewer as the primary Workbench module.
- Synchronized active project/LAS context, LAS Workspace navigation, active tool and dock focus.
- Added renderer-facing activation, zoom, pan, fit, reset, cursor, selection and SVG/PDF export actions.
- Reused existing LAS visualization, interaction, navigation and export services without UI-side parsing or calculations.
- Persisted only compact serializable viewer state and export metadata; raw DataFrames and artifact bytes are not stored in UI state.
- Added integration and regression coverage for lifecycle, navigation and current-view export.


## v191 Workbench project and recent-session entry points

- Added command-backed project and recent-session entry contracts for the existing Workbench shell.
- Kept project repository, recent-history and session-file access inside application command handlers.
- Routed project opening and restored sessions through the existing navigation model and tool activation flow.
- Restored lightweight session state without retaining raw DataFrames in presentation state.
- Added renderer-safe entry descriptors and unit/integration regression coverage.

## v192 Modern Workbench responsive and accessibility audit

- Added renderer-neutral responsive profiles for phone, tablet, laptop and wide viewports.
- Declared no-horizontal-scroll behavior and a 44 px minimum interactive target.
- Added deterministic keyboard focus order, keyboard semantics and accessible landmarks.
- Added labels, roles and action descriptions to the Workbench renderer accessibility contract.
- Added WCAG 2.2 AA contrast/readability checks for active presentation tokens.
- Added responsive Streamlit adapter CSS with overflow and focus-visible guards.
- Preserved a serializable presentation-only boundary without DataFrames or runtime service objects.
- Completed Modern Workbench Stage 3 and activated Petrophysical Engine Stage 4.


## v195 Workbench production engineering layout

- Replaced the linear shell-button presentation with a full-screen five-region engineering layout.
- Added a renderer-neutral `WorkbenchUILayoutContract` for toolbar, project tree, workspace host, Properties and Status Bar.
- Added desktop three-column and responsive single-column layouts without horizontal overflow.
- Connected the active module view model to the central workspace host without moving domain calculations or repository access into Streamlit.
- Preserved command-backed navigation and dock focus controls.
- Added production renderer, serialization, responsive and smoke regression coverage.


## v196 Interactive Workbench panes and embedded LAS workspace

- Added application-level providers for hydrated Project Explorer, selection-driven Properties and operational Status Bar payloads.
- Connected toolbar groups to real renderer actions routed through `WorkbenchController` and the Command Framework.
- Embedded the existing LAS visualization payload in the central workspace host without exposing raw DataFrames or repository objects.
- Added viewport, scale, track and curve status metadata.
- Added supported dock pane resizing with validation, command dispatch and Event Bus notification.
- Preserved responsive/accessibility contracts and presentation-only Streamlit boundaries.
- Added unit, integration and regression coverage for the interactive Workbench panes.


## v204 Runtime rendering repair

- Normalized mixed object columns before Streamlit/Arrow presentation serialization.
- Made project calculation comparison values consistently textual for UI and export parity.
- Replaced the deprecated raw HTML component path with `st.html` where supported.
- Routed Streamlit, PyArrow and Python warnings into the existing rotating `logs/app.log`.
- Added regression coverage for Arrow-safe tables and runtime log capture.


## v205 Module render audit and Streamlit compatibility

- Removed all direct and fallback `streamlit.components.v1.html` usage.
- Added route-level renderer/provider/view audit events with start/completed/failed phases.
- Added duration and expected-control metadata to Developer Diagnostics.
- Made Workbench binding status depend on successful render completion.
- Updated the existing roadmap and status documents without creating new planning files.

## v212 — Printable reports and stable UI state
- Fixed the keyed `interpretation_tablet_columns` widget state conflict that caused repeated reruns and the floating empty status box.
- Removed raw diagnostic structures from printable PDF/DOCX/HTML tables and translated user-facing quality flags.
- Added real Plotly image embedding to DOCX with a clear Kaleido fallback instead of the old `DocumentPlot renderer` placeholder.
- Cropped printable well-log tablets to the active data interval, limited interval overlays, and improved typography and margins.
- Corrected Russian collector wording in printable report cells and bounded technical appendices for readable reports.

## v213
- Registered nav.correlation in shell and navigation router.
- Cropped printable tablets to interpreted depth envelope and reduced overlays.
- Limited technical print tables to readable dimensions.
- Defaulted interval selection to the first row with valid ratios.

## v214 Inline engineering operation status

- Added compact in-flow statuses for mapping, calculation, visualization rendering and report export.
- Removed spinner/overlay activity behavior from the explicit engineering actions.
- Added user-visible calculation/render durations and separate timing records in the application log.
- Preserved explicit apply boundaries so status rendering does not trigger LAS parsing, calculation or Plotly construction.
- Added regression coverage against spinner reintroduction and legacy export status placeholders.
- Routed revision, applied mapping, presentation cache and export state through `ApplicationStateController`.
- Restored compliance with the final direct-session-state architecture audit.

## v214 Explicit export preparation

- Replaced rerun-driven PNG/PDF/SVG serialization with an explicit prepare action and cached static artifacts.
- Added an immutable export snapshot bound to the exact source signature and presentation revision.
- Moved interpretation HTML, interval print report and selected-interval CSV generation behind explicit actions.
- Moved LAS-correlation HTML generation behind an explicit action.
- Incremented the independent export revision only when a new artifact is actually generated.
- Added export timing records and regression coverage preventing implicit serialization from returning.

### Dataset Manager storage lifecycle audit
- Added per-section counters for active, archived and orphan dataset storage.
- Added safe cleanup actions for selected datasets, archived records, orphan directories, one section and all dataset sections.
- Destructive bulk actions now require exact project ID confirmation and create a project ZIP backup before deletion.
- Dataset manifests and Project Database index are synchronized after cleanup so deleted records do not return after rerun or restart.

## Project Database maintenance and duplicate safety

- Added safe Project Database synchronization, metadata compaction and metadata reset actions.
- Metadata reset regenerates `project_index.json`, `project_file_versions.json` and `project_uuids.json` from actual project storage without deleting user files.
- Metadata compaction keeps one active metadata version per current file and removes obsolete non-restorable history rows.
- Added exact SHA-256 duplicate removal with project ID confirmation, automatic ZIP backup, protected metadata files and post-delete index/UUID synchronization.
- Added regression tests for preservation of source data, version compaction and duplicate deletion guards.

- Improved Project Database tables: added search, type/status filters, stable sorting, pagination, compact paths, and an opt-in technical data mode.

## Unified Workbench Data Grid

- Renamed the reusable Project Database table renderer into the shared Workbench Data Grid.
- Applied the same search, filtering, sorting, pagination and technical-column mode to Dataset Manager, saved calculations and project exports.
- Preserved the former Project Database renderer as a compatibility alias to avoid regressions in existing routes.
- Kept report generation views unchanged where no persisted report catalog exists; report artifacts continue to appear in the unified export catalog.

## Workbench Data Grid selection and Properties integration

- Connected Dataset Manager, calculation archive and project export grids to the central Workbench selection service.
- Added stable hidden identifiers for dataset rows.
- Removed duplicate object selectors below Data Grid tables.
- Selected grid records now populate the right-hand Properties pane through one shared selection boundary.
- Preserved existing filters, sorting, pagination and technical-column visibility.

## Workbench bulk operations
- Added multi-selection to Dataset Manager, calculation archive and project exports.
- Added bulk verification, safe deletion with project-ID confirmation and automatic ZIP backup.
- Added bulk ZIP/package generation through the project export repository.

## 2026-07-12 — Calculation Diagnostics 2.0 foundation

- Added structured calculation diagnostics for C1–nC5 data quality and formula validity.
- Replaced repeated NaN warning banners with Summary, Quality, Formulas, Problem Rows and Recommendations tabs.
- Added exact counts for missing inputs, zero denominators and non-numeric values.
- Added first-problem-row preview without modifying source data.
- Corrected the Ch formula shown in the UI to Haworth Character Ratio `(ΣC4 + ΣC5) / C3`.
- Removed duplicated methodology notices from the warning stream while preserving a single documented notice.

## 2026-07-12 — Persisted calculation diagnostics and Workbench layout fix

- Fixed `WorkbenchUILayoutContract` so contextual `property_actions`, action results and technical-property mode are valid contract fields instead of causing a startup `TypeError`.
- Added JSON serialization and restoration for `CalculationDiagnosticsReport`.
- Saved `diagnostics.json` together with new calculation snapshots.
- Added integrity validation for the persisted diagnostics snapshot while preserving compatibility with legacy calculations that do not contain it.
- Connected calculation saving to the structured diagnostics engine so reopening a snapshot does not require recalculating the source dataset.

- Fixed Workbench startup regression caused by a missing METHODOLOGY_WARNING import in app/streamlit_app.py.

## 2026-07-12 — Active calculation cross-workspace state
- Fixed loss of committed calculation when navigating from Data to Interpretation or Reports.
- Added a project-bound active calculation contract shared across Workbench modules.
- Added regression coverage for workspace cleanup and cross-project isolation.


- Fixed repeated loss of calculated data when moving from Data to Interpretation by introducing a durable active-calculation contract.
- Added explicit lifecycle logging for calculation commit, restore, migration and missing-state diagnostics.

- Fixed active calculation persistence after mapping and calculation: `RevisionSnapshot.calculation` is now used instead of the removed `calculation_revision` attribute.
- Added a regression test covering the full revision snapshot contract used by the Data → Interpretation handoff.

- Added backward-compatible `*_revision` aliases to `RevisionSnapshot` and fixed active calculation handoff across mixed cached/runtime module versions.
- Removed Python bytecode caches from the delivery archive to prevent stale revision contracts after replacement.

- Interpretation first-render fix: initial graphs/tablet now auto-commit on first valid calculation; explicit button remains for later settings changes. Streamlit marker/zone count widgets now use Session State as the single source of truth.

### Interpretation full-interval export hotfix
- Fixed `TypeError: 'NoneType' object is not iterable` after successful graph rendering when the full depth interval is selected.
- Added a concrete effective depth interval for export metadata while preserving `None` as the plotting signal for the full interval.
- Removed duplicate Streamlit widget default/session-state warnings for tablet markers and zones.

## 2026-07-12 — Interpretation concrete depth range hotfix
- Resolved persisted full-interval `None` into a concrete depth range before report/export metadata is built.
- Added regression coverage for full and manual depth intervals.

## Engineer-facing interpretation summaries
- Replaced row-count interpretation summary with interval-oriented oil, gas, condensate and review tables.
- Added scrollable engineering interval grid with depth, thickness, confidence, data quality, geology support and conclusion.
- Increased raw calculation table viewport and enabled horizontal/vertical inspection without index noise.
- Reworked printable executive summary around depth ranges, cumulative interpreted thickness and best interval by fluid.
- Renamed and expanded the printable interval registry for engineering review.

### Changed — Pixler 2.0 foundation
- Replaced the single-row Pixler line with an interval-aware measurement cloud.
- Added interval median, selected-depth marker, zone support calculation and engineer-facing conclusion.
- Connected the selected depth to the detected hydrocarbon interval when available.
- Added interval-aware Ternary 2.0 with normalized measurement cloud, median center, selected-depth marker, configured regions, completeness metrics and an engineering conclusion.


## 2026-07-12 — Depth Panel 2.0 engineering tracks

- Replaced the single interval strip with separate Reservoir Type, Confidence and Recommendations tracks.
- Added 0–100% confidence bars and decision-level labels for every interpreted interval.
- Added one concise engineer-facing verification action per interval, sourced from the common interpretation explanation/rule model.
- Preserved shared depth alignment, top/base boundaries, selected-depth marker and backward compatibility when no intervals are detected.

### Changed
- Depth charts and the well-log tablet now use the actual LAS top and base instead of rounded automatic depth limits.
- Added independent depth interval selection for professional PDF/DOCX export.
- Added manual logarithmic Y limits and a visible probable-fluid badge to Pixler.
- Added a visible probable-fluid badge to the ternary plot.


## Removed HTML report export

- Removed HTML from user-facing report and print formats.
- Professional export now offers PDF, DOCX, or a PDF + DOCX ZIP package.
- Removed the legacy quick HTML graph/interval-report controls from Interpretation.

## Interpretation workspace view modes

- Added `Обзор всей скважины` and `Детальный интервал` modes for the professional depth panel.
- Added adaptive tablet height based on the displayed depth span.
- Added a minimum interval thickness display filter without modifying source data.
- Added a shared selected interval state for the interval selector, depth panel and interval passport.
- Added a compact selected interval passport below the graphs.
