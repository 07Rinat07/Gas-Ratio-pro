# Project Roadmap — v225.7

Обновлено: 18 июля 2026 года.

Этот документ — единственная активная последовательность разработки Gas Ratio Pro.

## Stage 4 — Workbench UI Completion

Статус: **ACTIVE / Release candidate v225.7**.

Завершено:

1. единый page-aware package, physical profiles и cross-format parity gate;
2. visual golden-artifacts для A4/A3 portrait/landscape и Print Center E2E acceptance;
3. устранение девяти architecture-boundary violations;
4. замена 26 brittle source assertions исполняемыми behavior contracts (18 legacy, Print Center contract и 7 PDF preview contracts);
5. controlled visual rebaseline 13 контрактов через semantic snapshot manifest;
6. замена исторических version pins и устаревших Workbench assertions;
7. закрытие всех 51 legacy regression contracts с evidence и replacement contract;
8. единый `BUILD_VERSION` и синхронная документация `ru/kk/en`;
9. полный regression suite: **2855 passed, 0 failed**.

Следующие разрешённые работы:

1. провести live acceptance через `run_app.ps1 -ForceRestart`;
2. проверить build/source identity и пять областей Workbench;
3. при успешной проверке выполнить stable promotion v225.7;
4. после stable promotion открыть следующий инженерный этап.

## Stabilization & Release Audit

Architecture boundary ослаблять запрещено. Visual baseline изменяется только через утверждённый semantic manifest и controlled rebaseline. Silent `xfail`, скрытие failures и удаление теста без replacement contract запрещены.

## Reservoir Intelligence / Interpretation 2.0

Статус: **FROZEN AFTER ACCEPTANCE**. Принятый Definition of Done остаётся обязательным регрессионным контрактом:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- инженерная сводка интервалов и воспроизводимая визуальная классификация;
- все утверждённые представления используют один расчётный результат и не изменяются print/export-инкрементами.

## Open Standards and Legal Research Governance

Внешние стандарты и third-party components подключаются только через policy, machine-readable registry, лицензионное подтверждение и изолированный adapter boundary.

## Petrophysical Engine

Статус: **BLOCKED** до stable promotion Stage 4. Допускаются только критические исправления без изменения утверждённого расчётного контракта.
