# Project Roadmap — v225.8 Stable

Обновлено: 18 июля 2026 года.

Этот документ — единственная активная последовательность разработки Gas Ratio Pro.

## Stage 4 — Workbench UI Completion

Статус: **COMPLETED / Stable v225.8**.

Завершено:

1. page-aware package, physical profiles и cross-format parity gate;
2. A4/A3 visual golden-artifacts и Print Center E2E acceptance;
3. устранение 9 architecture-boundary violations;
4. замена brittle source assertions поведенческими контрактами;
5. controlled visual rebaseline и закрытие всех 51 legacy regression contracts;
6. полный v225.8 regression suite: **2858 passed, 0 failed**;
7. Live Workbench Acceptance: реальный server health + executable Streamlit session;
8. подтверждены build/source identity и пять областей Workbench;
9. команда LAS и LAS Workspace выполнены без traceback;
10. stable promotion `v225.8`: **14/14 acceptance checks passed**.

## Stage 5 — Petrophysical Engine Validation Foundation

Статус: **NEXT AUTHORIZED**.

Разрешённый порядок:

1. инвентаризация и freeze текущего Method Registry;
2. machine-readable provenance формул и источников;
3. эталонные validation datasets с известными ожидаемыми результатами;
4. численные tolerance, unit contracts и uncertainty metadata;
5. единый application-service validation gate;
6. regression evidence до подключения новых UI-представлений.

Формулы нельзя изменять на основании UI-пожелания или незафиксированного источника. Любая новая формула должна иметь method ID, legal/source record, единицы, область применимости, эталонный dataset и tolerance.

## Stabilization & Release Audit

Architecture boundary ослаблять запрещено. Visual baseline изменяется только через approved semantic manifest. Silent `xfail`, скрытие failures и удаление теста без replacement contract запрещены. Stable promotion подтверждается `gas-ratio-pro/live-workbench-acceptance/v1`.

## Reservoir Intelligence / Interpretation 2.0

Статус: **FROZEN AFTER ACCEPTANCE**. Обязательный regression contract:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- инженерная сводка интервалов и воспроизводимая визуальная классификация;
- все утверждённые представления используют один calculation result.

## Definition of Done

- Stage 4 stable acceptance remains reproducible and passes all required checks;
- Stage 5 methods have machine-readable provenance, units, applicability domains, datasets, and tolerances;
- no approved Interpretation 2.0 or visual contract changes without explicit validation evidence;
- full regression suite contains no failures;
- documentation remains synchronized in Russian, Kazakh, and English.

## Open Standards and Legal Research Governance

Внешние стандарты и third-party components подключаются только через policy, machine-readable registry, лицензионное подтверждение и изолированный adapter boundary.
