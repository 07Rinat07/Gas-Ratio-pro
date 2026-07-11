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

Remaining v214 scope:

- remove all widget default/session-state conflicts;
- complete remaining explicit apply coverage for export controls and secondary presentation workspaces;
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
