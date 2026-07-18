# Current status — v225.9 Stable

Updated: July 18, 2026.

## Active stage

**Stage 5 — Petrophysical Engine Validation Foundation is complete.** No formulas were changed; a mandatory machine-readable validation gate now protects the engine.

## Validation foundation

- 10 methods are registered in `config/petrophysical_method_registry_v225_9.json`;
- 10 synthetic reference cases live in `data/validation/petrophysics/petrophysical_validation_cases_v225_9.json`;
- every method defines provenance, units, applicability, limitations, absolute/relative tolerance, and uncertainty metadata;
- the application service executes the real production functions;
- gate result: **10/10 passed**, final-report eligible: **9/10**;
- `petrophysics.sw_dual_water_foundation` is numerically reproducible but remains `blocked_final_report`;
- evidence: `artifacts/validation/petrophysical_validation_v225_9.json`.

## Adaptive report layout

- A3 landscape PDF uses the actual ReportLab frame width and height;
- metadata, legends, statistics, and narrative tables span the full working frame;
- DOCX uses the current section width and HTML uses responsive 100% width;
- `print-readability/v1.1` and the v225.9 visual baseline prevent a regression to a narrow left column.

## Stabilization & Release Audit

Stage 4 Live Workbench Acceptance (**14/14 passed**), architecture boundaries, controlled visual semantic snapshots, and resolved legacy contracts remain mandatory. Silent `xfail`, hidden failures, and formula changes without evidence are prohibited.

Final v225.9 verification: **2881 passed, 0 failed**; extended report/export contour: **338 passed**; Live Workbench Acceptance: **14/14**; petrophysical validation: **10/10**.

## Next stage

**Stage 5.1 — Field Calibration & Report Authorization Integration.** Authorized work includes field-owned calibration datasets, parameter uncertainty/sensitivity, read-only diagnostics, and wiring `authorize_methods(..., final_report=True)` into the final export boundary.
