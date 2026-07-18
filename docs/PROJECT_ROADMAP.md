# Project Roadmap — v225.10 Stable

Обновлено: 18 июля 2026 года. Этот документ — единственная активная последовательность разработки Gas Ratio Pro.

## Stage 4 — Workbench UI Completion

Статус: **COMPLETED / Stable v225.8**. Live Workbench Acceptance: 14/14.

## Stage 5 — Petrophysical Engine Validation Foundation

Статус: **COMPLETED / Stable v225.9**. 10/10 numerical contracts, 9/10 final-report eligible.

## Stage 5.1 — Field Calibration & Report Authorization Integration

Статус: **COMPLETED / Stable v225.10**.

1. project-owned synthetic field-surrogate calibration dataset для 10 методов;
2. ownership/legal clearance и contract fingerprints;
3. RMSE/MAE/bias/max error;
4. parameter sensitivity и uncertainty envelopes;
5. blocking final-report authorization до model/renderer;
6. method context, artifact/history evidence;
7. read-only diagnostics на ru/kk/en;
8. foundation Dual Water остаётся `blocked_final_report`.

## Stabilization & Release Audit

Stable v225.8 Live Workbench Acceptance, architecture boundaries, controlled visual baselines, full-frame report layout, numerical validation and field-calibration/report-authorization gates remain mandatory and may not be bypassed.

## Stage 5.2 — Operator Dataset Import & Calibration Comparison

Статус: **NEXT AUTHORIZED**.

1. импортировать только operator-owned или legally cleared packages;
2. проверять data rights и immutable source fingerprint;
3. сравнивать project-scoped calibration versions;
4. формировать versioned authorization packages;
5. не изменять formulas без нового validation/calibration evidence.

## Reservoir Intelligence / Interpretation 2.0

Статус: **FROZEN AFTER ACCEPTANCE**. Pixler rehabilitation, Ternary rehabilitation, Depth engineering panel и единый calculation result изменяются только с explicit validation evidence.

## Definition of Done

- Live Workbench Acceptance воспроизводим;
- numerical и field-calibration gates проходят;
- final report не использует `blocked_final_report`;
- authorization выполняется до renderer;
- full regression suite не содержит failures;
- landscape отчёты используют фактический frame;
- документация синхронизирована на русском, казахском и английском.

## Open Standards and Legal Research Governance

Внешние методы, стандарты и datasets подключаются только через source/legal registry и изолированный adapter boundary.

Any third-party component requires a machine-readable license/source record and an isolated adapter boundary.
