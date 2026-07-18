# Current Status — v225.7

Updated: July 18, 2026.

## Active stage

**Stage 4 — Workbench UI Completion / Stabilization & Release Audit.** The build remains **release candidate v225.7**.

## Implemented

- all nine confirmed architecture-boundary violations were removed without weakening the audit policy;
- temporary-file destruction now belongs to an application lifecycle service and uses `DeleteEngine`;
- cache telemetry is created once by the application container and injected through service boundaries;
- route lifecycle, startup diagnostics, and cache coherence belong to the application service;
- direct `st.rerun()` is allowed only inside the unified rerun gate;
- 26 brittle source assertions were replaced with executable behavior contracts (18 from the legacy registry, one Print Center contract, and seven PDF preview contracts);
- 13 visual legacy checks were migrated to approved semantic snapshots;
- `visual_rebaseline_contracts_v225_7.json` and SHA-256 validation were added;
- six historical version pins were replaced with current-build identity contracts;
- five obsolete Workbench compatibility assertions were replaced with runtime/view-model checks;
- all 51 legacy regression contracts now contain `resolved_in`, evidence, and a replacement contract;
- the root `BUILD_VERSION` file is the single build-version source;
- the user release archive excludes `.github/workflows`.

## Legacy regression state

- registered contracts: **51**;
- resolved in v225.7: **51**;
- active legacy contracts: **0**;
- silent `xfail` and test deletion without a replacement contract remain prohibited.

## Release verification

- extended architecture/renderer/export/documentation set: **480 passed**;
- complete regression suite: **2855 passed, 0 failed**;
- all 51 legacy nodeids are included in the full suite and pass their replacement contracts;
- new v225.7 regression failures: **0**;
- Python compileall: **passed**; 92 relative Markdown links and 36 manifest paths: **valid**.

The automated release gate has passed. Stable promotion remains blocked only by live Workbench acceptance.

## Next stage

Run the full regression audit, start the application through `run_app.ps1 -ForceRestart`, inspect all five Workbench regions, and only then decide whether v225.7 may move from release candidate to stable.
