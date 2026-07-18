# Дорожная карта проекта — v225.10 Stable

Обновлено: 18 июля 2026 года. Единственная активная последовательность разработки Gas Ratio Pro.

## Stage 4 — Workbench UI Completion

Статус: **COMPLETED / Stable v225.8**. Live Workbench Acceptance: 14/14.

## Stage 5 — Petrophysical Engine Validation Foundation

Статус: **COMPLETED / Stable v225.9**. Numerical contracts: 10/10; final-report eligible: 9/10.

## Stage 5.1 — Field Calibration & Report Authorization Integration

Статус: **COMPLETED / Stable v225.10**.

- project-owned synthetic field-surrogate calibration dataset для 10 методов;
- ownership/legal clearance и fingerprints;
- RMSE, MAE, bias, max error;
- parameter sensitivity и uncertainty envelopes;
- blocking authorization до PresentationModel и renderer;
- evidence в method context, artifact и export history;
- read-only diagnostics на ru/kk/en;
- foundation Dual Water остаётся `blocked_final_report`.

## Stabilization & Release Audit

Stable v225.8 Live Workbench Acceptance, architecture boundaries, controlled visual baselines, full-frame report layout, numerical validation и field-calibration/report-authorization gates обязательны и не могут быть обойдены.

## Stage 5.2 — Operator Dataset Import & Calibration Comparison

Статус: **NEXT AUTHORIZED**.

- импорт только operator-owned или legally cleared packages;
- data-rights и immutable source fingerprint;
- project-scoped comparison;
- versioned authorization packages;
- запрет изменения formulas без validation/calibration evidence.

## Reservoir Intelligence / Interpretation 2.0

Статус: **FROZEN AFTER ACCEPTANCE**. Pixler rehabilitation, Ternary rehabilitation, Depth engineering panel и единый calculation result изменяются только с explicit validation evidence.

## Definition of Done

Live Workbench Acceptance, numerical gate, field-calibration gate, authorization до renderer, full regression без failures, full-frame landscape layout и синхронная документация ru/kk/en обязательны.

## Open Standards and Legal Research Governance

Внешние методы, стандарты и datasets подключаются только через source/legal registry и изолированный adapter boundary.

Any third-party component requires a machine-readable license/source record and an isolated adapter boundary.
