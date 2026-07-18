# Gas Ratio Pro Project Plan

Updated: July 18, 2026. Active build: `v225.8 stable`.

## Completed increment — Stable Promotion & Live Workbench Acceptance

- added a cross-platform acceptance runner;
- a temporary Streamlit server passes the health gate;
- official AppTest executes a real Workbench session;
- verified build version, stable channel, absolute source path, and entry-point SHA-256;
- verified Toolbar, Project Explorer, Workspace Host, Properties, and Status Bar;
- the LAS command and LAS Workspace complete without a traceback;
- result: **14/14 acceptance checks passed**;
- the Windows launcher supports `run_app.ps1 -Acceptance`;
- documentation and instructions are synchronized in Russian, Kazakh, and English.

## Next authorized increment — Petrophysical Engine Validation Foundation

1. Freeze the current Method Registry and formula inventory.
2. Link every method ID to its source, license, units, and applicability domain.
3. Prepare reference datasets and expected results.
4. Define numerical tolerances and uncertainty metadata.
5. Implement an application-service validation gate and regression tests.
6. Do not modify Interpretation 2.0 or visual baselines without separately approved evidence.

## Definition of Done

- the build channel remains `stable`;
- live acceptance is locally reproducible and passes 14/14;
- every petrophysical method has machine-readable provenance;
- validation datasets contain no unverified or unlawfully obtained data;
- results are reproducible within the approved tolerance;
- README, instructions, status, roadmap, changelog, release notes, and manifest are synchronized in `ru/kk/en`.
