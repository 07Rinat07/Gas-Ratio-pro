# Gas Ratio Pro Project Plan

Updated: July 18, 2026. Active build: `v225.7`.

## Completed increment — v225.7

- removed all 9 architecture-boundary violations;
- moved lifecycle, cache telemetry, route/startup/cache coherence, and rerun ownership to the correct layers;
- replaced 26 source assertions with behavior contracts (18 legacy, one Print Center contract, and seven PDF preview contracts);
- migrated 13 visual contracts to a semantic snapshot manifest;
- replaced obsolete version pins with current-build identity contracts;
- resolved all 51 legacy contracts with evidence and replacement tests;
- made `BUILD_VERSION` the single version source;
- synchronized documentation and instructions in Russian, Kazakh, and English;
- completed the regression suite: **2855 passed, 0 failed**.

## Next authorized increment — Stable Promotion & Live Workbench Acceptance

1. Start the application through `run_app.ps1 -ForceRestart`.
2. Confirm the build and absolute runtime source path.
3. Inspect the toolbar, Project Explorer, Workspace Host, Properties, and Status Bar.
4. Exercise command-backed actions and LAS Viewer without a traceback.
5. Promote v225.7 to stable only when no release-blocking failures remain.

## Definition of Done

- all 51 legacy contracts are resolved;
- active architecture-boundary debt is zero;
- semantic visual snapshots pass SHA-256 validation;
- the full suite has no new failures;
- live Workbench acceptance is confirmed;
- version, README, instructions, status, roadmap, changelog, release notes, and manifest are synchronized in `ru/kk/en`.
