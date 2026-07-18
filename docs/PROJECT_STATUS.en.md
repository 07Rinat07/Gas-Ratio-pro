# Current status — v225.11 Stable

Updated: July 18, 2026.

## Active stage

**Stage 5.2 — Operator Dataset Import & Calibration Comparison is complete.** Production formulas were not changed.

- ZIP packages contain only `manifest.json`, `calibration_registry.json`, and `calibration_dataset.json`;
- only `operator_owned`, `licensed`, or `public_domain` data are accepted;
- project scope, owner, legal basis, processing/derivative permissions, and expiration are blocking;
- package, file, and rights fingerprints are verified on import and every later use;
- `package_id + version` is immutable;
- private operator data stays in the project repository and is excluded from release archives;
- baseline and package versions are compared across all 10 methods;
- a versioned project authorization package is created before rendering;
- export-history schema v5 records the authorization package ID and operator fingerprint;
- export caches are cleared when the active authorization/rights context changes;
- foundation Dual Water remains `blocked_final_report`.

Evidence: `artifacts/validation/petrophysical_operator_calibration_v225_11.json`; Stage 5.2 gate — import 1/1, comparison 10/10, authorization 9/9; full regression **2915 passed, 0 failed**; Live Workbench **14/14**.

## Stabilization & Release Audit

Stage 5/5.1 gates, architecture boundaries, controlled visual baselines, and full-frame report layout remain mandatory. `.github/workflows` is excluded from the user archive.

Reservoir Intelligence / Interpretation 2.0, Pixler rehabilitation, Ternary rehabilitation, and the Depth engineering panel cannot change without explicit validation evidence.

## Next stage

**Stage 5.3 — Calibration Package Trust & Review Workflow:** detached signatures, a trust registry, reviewer approval, package revocation, and controlled promotion between projects.
