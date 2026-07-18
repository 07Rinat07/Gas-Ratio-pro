# Project Roadmap — v225.9 Stable

Updated: July 18, 2026. This is the single active development sequence for Gas Ratio Pro.

## Stage 4 — Workbench UI Completion

Status: **COMPLETED / Stable v225.8**. Live Workbench Acceptance: 14/14.

## Stage 5 — Petrophysical Engine Validation Foundation

Status: **COMPLETED / Stable v225.9**.

Completed:

1. froze 10 current production methods without changing formulas;
2. added machine-readable provenance, source/legal metadata, and report policy;
3. added unit contracts for inputs, parameters, and outputs;
4. added 10 synthetic reference datasets with expected results;
5. defined absolute/relative tolerances and uncertainty metadata;
6. added an application-service gate, CLI, and JSON evidence;
7. embedded method provenance and the contract fingerprint in calculation manifests;
8. blocked foundation Dual Water from final reports;
9. added adaptive full-frame A3 landscape layout for PDF/DOCX/HTML with the v225.9 visual baseline.

## Stabilization & Release Audit

Stable v225.8 Live Workbench Acceptance remains mandatory: **14/14 passed**. Architecture boundaries, controlled visual baselines, replacement contracts, and the v225.9 petrophysical validation gate may not be bypassed.

## Stage 5.1 — Field Calibration & Report Authorization Integration

Status: **NEXT AUTHORIZED**.

1. add only field-owned or legally cleared calibration datasets;
2. define parameter distributions and sensitivity/uncertainty envelopes;
3. wire final-report authorization into the export application service;
4. add read-only validation diagnostics without changing formulas;
5. repeat full regression and Live Workbench Acceptance.

## Reservoir Intelligence / Interpretation 2.0

Status: **FROZEN AFTER ACCEPTANCE**. Pixler, Ternary, the Depth engineering panel, and the shared calculation result may change only with explicit validation evidence.

## Definition of Done

- Stable v225.8 Workbench acceptance remains reproducible;
- the petrophysical gate passes every method contract;
- final reports cannot use `blocked_final_report` methods;
- the full regression suite has no failures;
- landscape reports use the actual frame without a fixed narrow column;
- documentation remains synchronized in Russian, Kazakh, and English.

## Open Standards and Legal Research Governance

External methods, standards, and datasets enter only through the source/legal registry and an isolated adapter boundary.

Any third-party component requires a machine-readable license/source record and an isolated adapter boundary.
