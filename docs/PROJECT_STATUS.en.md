# Current Status — v225.6

Updated: 18 July 2026.

## Active stage

**Stage 4 — Acceptance, Visual Baseline & Legacy Contract Audit / Stabilization & Release Audit.** The build is **release candidate v225.6**.

## Implemented

- visual golden artifacts are frozen for A4/A3 portrait and landscape;
- the manifest verifies SVG, PNG, PDF, physical dimensions, pagination, track partition, page chrome, and SHA-256;
- reproducible regeneration is provided by `scripts/regenerate_physical_golden_artifacts.py`;
- an end-to-end `ProfessionalPrintCenterAcceptanceRunner` is implemented;
- the acceptance path covers persisted profile selection, visible preview, parity gate, HTML/PDF/DOCX bundle, and SVG/PNG delivery;
- fixed `LayoutError` when a portrait physical preview is embedded in a landscape PDF report;
- all 51 legacy regression contracts are registered in a machine-readable audit;
- the audit forbids silent `xfail` and test deletion without a replacement contract;
- user release archives exclude `.github/workflows`.

## Release verification

- targeted v225.6 acceptance/golden/audit and compatible renderer/export set: **150 passed**;
- full regression suite: **2853 tests, 2802 passed, 51 failed**;
- the 51 failures remain visible in the inherited registry;
- new v225.6 regression failures: **0**;
- Python compileall, documentation links, manifest, and archive: **passed**.

## Next stage

Resolve the nine confirmed architecture-boundary debts and replace brittle source/visual assertions with approved behavior/golden contracts. Stable promotion requires zero release-blocking debt.
