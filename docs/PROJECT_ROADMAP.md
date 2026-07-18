# Project Roadmap — v225.9 Stable

Обновлено: 18 июля 2026 года. Этот документ — единственная активная последовательность разработки Gas Ratio Pro.

## Stage 4 — Workbench UI Completion

Статус: **COMPLETED / Stable v225.8**. Live Workbench Acceptance: 14/14.

## Stage 5 — Petrophysical Engine Validation Foundation

Статус: **COMPLETED / Stable v225.9**.

Завершено:

1. freeze 10 текущих production methods без изменения формул;
2. machine-readable provenance, source/legal metadata и report policy;
3. unit contracts для inputs, parameters и outputs;
4. 10 synthetic reference datasets с expected results;
5. absolute/relative tolerances и uncertainty metadata;
6. application-service gate, CLI и JSON evidence;
7. method provenance и contract fingerprint в calculation manifests;
8. final-report block для foundation Dual Water;
9. адаптивный full-frame layout для A3 landscape в PDF/DOCX/HTML с visual baseline v225.9.

## Stabilization & Release Audit

Stable v225.8 Live Workbench Acceptance remains mandatory: **14/14 passed**. Architecture boundaries, controlled visual baselines, replacement contracts, and the v225.9 petrophysical validation gate may not be bypassed.

## Stage 5.1 — Field Calibration & Report Authorization Integration

Статус: **NEXT AUTHORIZED**.

1. добавить только field-owned или legally cleared calibration datasets;
2. описать parameter distributions и sensitivity/uncertainty envelopes;
3. подключить final-report authorization к export application service;
4. добавить read-only validation diagnostics без изменения formulas;
5. повторить full regression и Live Workbench Acceptance.

## Reservoir Intelligence / Interpretation 2.0

Статус: **FROZEN AFTER ACCEPTANCE**. Pixler rehabilitation, Ternary rehabilitation, Depth engineering panel и единый calculation result изменяются только с explicit validation evidence.

## Definition of Done

- Stable v225.8 Workbench acceptance остаётся воспроизводимым;
- petrophysical gate проходит все method contracts;
- final report не может использовать `blocked_final_report`;
- full regression suite не содержит failures;
- landscape отчёты используют фактический frame без фиксированной узкой колонки;
- документация синхронизирована на русском, казахском и английском.

## Open Standards and Legal Research Governance

Внешние методы, стандарты и datasets подключаются только через source/legal registry и изолированный adapter boundary.

Any third-party component requires a machine-readable license/source record and an isolated adapter boundary.
