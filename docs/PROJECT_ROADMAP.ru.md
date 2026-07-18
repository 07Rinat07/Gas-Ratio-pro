# Project Roadmap — v225.5

Обновлено: 18 июля 2026 года.

Этот документ — единственная активная последовательность разработки Gas Ratio Pro.

## Stage 4 — Workbench UI Completion

Статус: **ACTIVE / Release candidate v225.5**.

Завершено:

1. единый page-aware package для SVG/PNG/PDF/DOCX/HTML;
2. видимый многостраничный Professional Print Center;
3. блокирующий cross-format parity gate;
4. пользовательские физические профили A4/A3 с safety floors;
5. retirement legacy CompositeLog static-export;
6. manifest-backed ZIP для multi-page SVG/PNG;
7. синхронная документация `ru/kk/en`.

Следующие разрешённые работы:

1. пользовательский acceptance-test полного Print Center workflow;
2. визуальные golden artifacts для A4/A3 portrait/landscape и пользовательских профилей;
3. аудит оставшихся legacy regression contracts;
4. финализация Stage 4 и перевод release candidate в stable.

## Stabilization & Release Audit

Перед каждым выпуском обязательны parity gate, regression-прогон, физическая проверка A4/A3, документация `ru/kk/en`, manifest/links/version metadata и целостность архива.

## Reservoir Intelligence / Interpretation 2.0

Статус: **FROZEN AFTER ACCEPTANCE**. Принятый Definition of Done остаётся обязательным регрессионным контрактом:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- инженерная сводка интервалов и воспроизводимая визуальная классификация;
- Definition of Done: все утверждённые представления используют один расчётный результат и не изменяются print/export-инкрементами.

## Open Standards and Legal Research Governance

Внешние стандарты и third-party components подключаются только через policy, machine-readable registry, лицензионное подтверждение и изолированный adapter boundary.

## Petrophysical Engine

Статус: **BLOCKED** до завершения Stage 4. Допускаются только критические исправления без изменения утверждённого расчётного контракта.
