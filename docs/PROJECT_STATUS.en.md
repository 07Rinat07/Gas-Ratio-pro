# Current status — v225.8 Stable

Updated: July 18, 2026.

## Active stage

**Stage 4 — Workbench UI Completion is complete.** Build `v225.8` was promoted to the **stable** channel after automated Live Workbench Acceptance.

## Stable promotion

- a real temporary Streamlit server returns `ok` from `/_stcore/health`;
- the build badge, `BUILD_VERSION`, `BUILD_CHANNEL`, absolute runtime source path, and entry point agree;
- Toolbar, Project Explorer, Workspace Host, Properties, and Status Bar render without a traceback;
- the command-backed LAS action selects `nav.las_workspace`;
- LAS Viewer and the LAS Workspace open action complete without a traceback;
- acceptance result: **14/14 passed**;
- acceptance contract: `config/live_workbench_acceptance_contract_v225_8.json`;
- machine-readable evidence: `artifacts/acceptance/live_workbench_acceptance_v225_8.json`.

## Stabilization & Release Audit

Architecture boundaries, the 51 resolved legacy contracts, controlled visual semantic snapshots, and the live acceptance contract remain mandatory stable-release gates. Silent `xfail`, hidden failures, and test deletion without a replacement contract are prohibited.

## Regression state

- full v225.8 regression suite: **2858 passed, 0 failed**;
- acceptance and stable-promotion tests extend that baseline;
- architecture-boundary debt: **0**;
- active legacy regression contracts: **0**;
- controlled visual semantic snapshots remain mandatory.

## Next stage

**Stage 5 — Petrophysical Engine Validation Foundation.** Only the method registry, formula provenance, reference datasets, numerical tolerances, and the application-service validation gate are authorized. Approved formulas, Interpretation 2.0, and visual baselines may not change without validation evidence.
