# v225.7 Implementation Plan

## Objective

Remove nine architecture-boundary violations, replace brittle source assertions with executable behavior tests, and perform a controlled visual rebaseline without hiding regressions.

## Completed work

1. Moved lifecycle and infrastructure deletion from UI to an application service.
2. Moved session-scoped cache telemetry to the application container.
3. Assigned route/startup/cache-coherence lifecycle to the runtime diagnostics service.
4. Allowed rerun only through one gate.
5. Replaced 26 source assertions with behavior/view-model contracts (18 legacy, one Print Center contract, and seven PDF preview contracts).
6. Migrated 13 visual contracts to a SHA-256 semantic snapshot manifest.
7. Replaced historical version pins with current-build identity contracts.
8. Resolved all 51 legacy contracts with evidence and replacement tests.

## Definition of Done

- 9 of 9 architecture tests pass;
- 26 of 26 source-contract replacements pass;
- 13 of 13 visual snapshots validate;
- active legacy debt is zero;
- the complete regression suite reports **2855 passed, 0 failed**;
- the extended release set reports **480 passed**;
- `ru/kk/en` documentation is synchronized.
