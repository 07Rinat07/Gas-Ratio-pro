# Current status — v225.10 Stable

Updated: July 18, 2026.

## Active stage

**Stage 5.1 — Field Calibration & Report Authorization Integration is complete.** Production formulas were not changed.

## Field Calibration

- 10 methods use a project-owned synthetic field-surrogate dataset;
- registry and dataset carry ownership/legal clearance, units, acceptance thresholds, and fingerprints;
- the gate calculates RMSE, MAE, bias, maximum error, sensitivity, and uncertainty envelopes;
- field-calibration gate: **10/10 passed**;
- final-report calibrated/authorised: **9/10**;
- evidence: `artifacts/validation/petrophysical_calibration_v225_10.json`.

## Report Authorization

- numerical validation, calibration, and report policy are composed in an application service;
- method IDs propagate through a machine-readable DataFrame context;
- export authorization runs before PresentationModel and renderer construction;
- authorization IDs and gate IDs are persisted in artifacts and export history;
- Professional Print Center exposes read-only diagnostics in ru/kk/en;
- foundation Dual Water remains `blocked_final_report`.

## Stable contracts

Live Workbench Acceptance, full-frame A3 landscape layout, architecture boundaries, controlled visual baselines, and Open Standards and Legal Research Governance remain mandatory. Pixler rehabilitation, Ternary rehabilitation, Depth engineering panel, and Reservoir Intelligence / Interpretation 2.0 require explicit evidence before changes.

Final v225.10 verification: **2896 passed, 0 failed**; Live Workbench Acceptance: **14/14**; numerical validation: **10/10**; field calibration: **10/10**; final-report authorization: **9/10**.

## Stabilization & Release Audit

Stable v225.8 Live Workbench Acceptance remains mandatory and passes **14/14** checks. Architecture boundaries, controlled visual baselines, full-frame report layout, and numerical/calibration/authorization gates remain blocking.

## Next stage

**Stage 5.2 — Operator Dataset Import & Calibration Comparison.** Authorised work includes operator-owned calibration-package import, data-rights validation, project-scoped comparison, and versioned authorization packages. Formula changes without validation/calibration evidence remain prohibited.
