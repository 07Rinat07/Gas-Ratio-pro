# GAS RATIO PRO — Current Project Status

Baseline: v213
Current stage: **Stage 4R — Engineering Presentation Refactor**
Decision: **controlled refactor approved after live acceptance failure**
Stage 5: **BLOCKED**

## 1. Confirmed production state

Рабочими и сохраняемыми считаются:

- LAS parsing, header detection and manual mapping;
- calculation engine and hydrocarbon interval engine;
- Modern Workbench shell, command dispatch, docks and route framework;
- project/session infrastructure and runtime diagnostics;
- correlation route registration in v213.

Не прошли пользовательскую приемку:

- профессиональный well-log планшет;
- Pixler and ternary presentation;
- multi-well correlation layout;
- PDF/DOCX/HTML report quality;
- runtime responsiveness and Streamlit rerun behavior.

## 2. Evidence from v213 live test

- `interpretation_tablet_marker_count` still has a widget default/session-state conflict.
- Interpretation rebuilds five figures repeatedly; cached rerender remains approximately 7–13 seconds.
- Export plus rerender takes approximately 16–17 seconds.
- LAS is reread and recalculated during mapping-related reruns.
- Printed tablet still uses excessive empty depth space and weak track readability.
- DOCX/PDF tables remain too wide and produce narrow or vertically broken text.
- Expert report still exposes excessive detail and zero-thickness interval rows.
- Correlation route now opens, but correlation presentation is not yet production-ready.

## 3. Active plan

The single active roadmap now contains **Stage 4R — Engineering Presentation Refactor** with this mandatory order:

1. R1 — state and performance foundation;
2. R2 — professional Well Log Renderer;
3. R3 — Pixler and ternary models;
4. R4 — Correlation Workspace;
5. R5 — Reports v4;
6. R6 — interval consolidation and live acceptance.

No petrophysics, geomodeling, 3D or new domain modules are authorized before Stage 4R Definition of Done.

## 4. Next authorized increment

**v214 — Presentation Refactor Foundation (implementation started)**

Implemented in the current increment:

- added independent data/calculation/presentation/export revision controller;
- added SHA-256 content cache for parsed LAS with defensive DataFrame copies;
- connected cached LAS loading to the shared upload path;
- added initial immutable `WellLogRenderModel` and `ReportDocumentModel` contracts;
- added parse timing and cache-hit logging;
- added focused characterization, cache, revision and contract tests.
- separated draft mapping widgets from the applied mapping snapshot;
- added explicit `Применить mapping` and `Запустить интерпретацию` actions;
- prevented draft widget changes from triggering calculations or replacing committed results;
- tied an applied mapping to the exact prepared-data signature and invalidated it when source content changes;
- separated draft graph/tablet widgets from the applied presentation snapshot;
- added explicit `Построить графики и планшет` action;
- bound the applied presentation to the exact calculated-data signature and calculation revision;
- prevented color, scale, marker and zone edits from rebuilding Plotly figures before explicit apply.
- added compact inline operation statuses for mapping, calculation, rendering and export;
- removed spinner/overlay behavior from the engineering workflow;
- added calculation and render duration logging plus user-visible completion timings;
- added regression coverage preventing reintroduction of `st.spinner` and legacy export alert placeholders.
- routed v214 runtime, cache and widget-state access through `ApplicationStateController`;
- passed the final direct-session-state architecture audit for the Streamlit application.
- separated LAS-correlation draft controls from an applied multi-well presentation snapshot;
- added explicit `Построить корреляцию` action for Correlation Studio, curve comparison and synchronized multi-well plots;
- tied correlation rendering to the exact content signatures of all loaded LAS wells;
- added one-entry correlation figure cache and render timing diagnostics.
- moved PNG/PDF/SVG static rendering behind an explicit preparation action and artifact cache;
- moved interpretation HTML, printable interval report and interval CSV serialization behind explicit actions;
- moved LAS-correlation HTML serialization behind an explicit action;
- added immutable export snapshots bound to source signature and presentation revision;
- connected completed artifact generation to the independent export revision and timing log.

Workbench stabilization added after live UI review:

- saved project calculations are treated as an archive, not as current session data;
- archived warnings and exports are not evaluated until the user explicitly opens the archive;
- the command ribbon is limited to contextual module actions and no longer duplicates top navigation or dock controls;
- Project Explorer counts are hydrated from the active project instead of remaining decorative zeroes.

Remaining v214 scope:

- remove all widget default/session-state conflicts;
- complete remaining explicit apply coverage for secondary export controls; **completed for interpretation and LAS correlation exports**;
- stop unrelated reruns from rebuilding figures or exports;
- replace floating/blank Streamlit activity artifact with inline status; **completed for mapping, calculation, rendering and export**;
- extend characterization and performance tests.

v214 does not claim visual completion. It creates the safe boundary required to replace renderers without breaking calculation behavior.

## 5. Acceptance gates for v214

- no Streamlit widget state warnings in diagnostics log;
- selecting report format does not read LAS, calculate, or build figures;
- switching routes does not read LAS again;
- unchanged Interpretation uses cached presentation artifacts;
- no unexplained blank floating square during normal navigation;
- logs contain separate parse/calculation/model/render/export timings;
- existing calculation regression remains green.

## 6. Governance

Active governance remains limited to:

- `PROJECT_ROADMAP.md`;
- `PROJECT_STATUS.md`;
- `ARCHITECTURE.md`;
- `DOCUMENTATION_INDEX.md`;
- `CHANGELOG.md` for history only.

No new roadmap, sprint-status or progress files are created.

## Dataset Manager cleanup stabilization
- Dataset tables now distinguish active records from archived records and orphan physical folders.
- Hidden archived datasets no longer remain invisible without diagnostics.
- Cleanup is explicit, project-scoped and backup-protected.

### Workbench stabilization — Project Database maintenance

Completed:
- Project Database tables can be synchronized from actual storage.
- File-version metadata can be compacted without touching source files.
- Index, version and UUID metadata can be safely reset and regenerated after automatic backup.
- Real file deletion is restricted to explicitly selected exact SHA-256 duplicates; metadata JSON files are protected.
- Every destructive operation rebuilds the file index, versions and UUID registry.

- Project Database tables now use a shared compact view with search, type/status filters, sorting, pagination, and technical columns hidden by default.

### Unified Workbench Data Grid

Status: implemented for Project Database, Dataset Manager, saved calculations and project exports. Report files are represented through the project export catalog until a dedicated persisted report repository is introduced.

### Current increment — Data Grid to Properties integration

Completed:
- shared row selection contract for Workbench Data Grid;
- Dataset, Calculation and Export selection routed through WorkbenchSelectionService;
- duplicate selectors removed from the affected panels;
- stable technical identifiers retained but hidden by default;
- selected object metadata prepared for the Properties pane.

Completed additionally:
- object-specific actions moved into a contextual Properties action group;
- destructive actions require exact object-ID confirmation and automatic ZIP backup;
- technical properties are hidden by default and can be toggled in Properties;
- integrity checks are available for selected LAS, dataset and calculation objects.

Next:
- add multi-row selection and bulk action contracts;
- complete the same selection behavior for remaining Project Database tables.

### Current increment — Project Explorer 2.0 foundation

Completed:
- Modern Workbench now consumes the persisted metadata-only project tree instead of a flat counter list.
- Project, folders, well groups, wells, LAS versions, calculations and exports are represented as hierarchical selectable nodes.
- Explorer search preserves ancestors of every matching object.
- Expansion state is stored independently from domain data and does not load LAS/calculation payloads.
- Selection is synchronized through WorkbenchSelectionService and reflected in Properties.
- Status markers distinguish ready, warning, error and empty nodes without treating missing data as an application error.

Next:
- add persisted reports and correlation objects to the project tree;
- add context actions and optional multi-selection without introducing destructive right-click shortcuts.

### Unified Workbench Data Grid — bulk actions completed
Multi-selection is available for datasets, calculations and exports. Bulk destructive actions require exact project confirmation and create a project backup before mutation.

### Calculation Diagnostics 2.0 foundation

Implemented a structured diagnostics report for mapped gas components and calculated ratios. The interpretation workflow now presents compact diagnostic tables instead of one warning banner per formula. Formula and data-quality causes are separated, and the UI Ch reference matches the calculation core.

### Persisted diagnostics snapshot and Workbench contract stabilization

Completed:
- fixed the startup regression caused by an incomplete `WorkbenchUILayoutContract` definition;
- new saved calculations include `diagnostics.json` with column quality, formula diagnostics, recommendations and sampled problem rows;
- diagnostics snapshots can be restored without recalculating source LAS data;
- integrity checks validate diagnostics JSON and row-count consistency;
- legacy snapshots without diagnostics remain supported.

Next:
- expose persisted diagnostics inside the saved-calculation card and Properties diagnostics section;
- add LAS NULL metadata and gas-sampling density analysis.

- Workbench Data route startup regression fixed: methodology notices now import both CH_WARNING and METHODOLOGY_WARNING.

### Active calculation handoff
- Committed calculation survives ordinary Workbench navigation.
- Interpretation and Reports read the same project-bound result without recalculation.
- Cross-project reuse is blocked by project id guard.


## Interpretation workspace durable calculation fix
- Active calculation is now stored in a durable `workbench_active_calculation` contract.
- Workspace navigation no longer clears the last explicitly calculated DataFrame.
- Added commit/restore/missing diagnostics to application logs.
