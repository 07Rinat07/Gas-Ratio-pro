# Project Roadmap — v225.4

Обновлено: 18 июля 2026 года.

Этот документ — **единственная активная последовательность** разработки Gas Ratio Pro. Версионные roadmap-файлы и параллельные progress/next-step документы хранятся только в `docs/archive/legacy_plans/`.

Локализованные версии: [Русский](PROJECT_ROADMAP.ru.md) · [Қазақша](PROJECT_ROADMAP.kk.md) · [English](PROJECT_ROADMAP.en.md).

## Stage 4 — Workbench UI Completion

Статус: **ACTIVE**.

Завершено в v225.4:

- видимый Professional Print Center использует один физический page-aware package;
- точный профиль и все preview-страницы доступны до запуска;
- DOCX/HTML получают канонический multi-page preview напрямую;
- общий strict normalizer исключает silent first-page fallback;
- `bundle` включён в единый экспортный путь;
- `ru/kk/en` локализация preview синхронизирована.

Следующие разрешённые работы:

1. автоматизированная parity-матрица UI/PDF/DOCX/HTML/SVG/PNG для A4/A3 portrait/landscape;
2. удаление legacy static-export веток после прохождения parity gate;
3. пользовательские физические профили без уменьшения текста ниже утверждённого минимума;
4. завершение Stage 4 после проверки реального пользовательского пути.

## Stabilization & Release Audit

Статус: **Release candidate v225.4**.

Перед каждым выпуском обязательны regression-прогон, format parity, физическая проверка A4/A3, синхронизация документации `ru/kk/en`, проверка manifest/ссылок/version metadata и целостности архива.

## Petrophysical Engine

Статус: **BLOCKED**.

Расширение петрофизического движка запрещено до завершения Stage 4 и Stabilization & Release Audit. Допускаются только критические исправления без изменения утверждённого расчётного контракта.

## Release gate

Релиз готов только при одном layout и geometry signature, полном multi-page contract, отсутствии silent fallback, воспроизводимых артефактах, соответствии тестов и документации фактическому коду и синхронности трёх языков.

## Reservoir Intelligence / Interpretation 2.0

Статус: **FROZEN AFTER ACCEPTANCE**. Принятый Definition of Done остаётся обязательным регрессионным контрактом:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- инженерная сводка интервалов и воспроизводимая визуальная классификация;
- Definition of Done: все утверждённые представления используют один расчётный результат и не изменяются print/export-инкрементами.

## Open Standards and Legal Research Governance

Внешние стандарты и third-party components подключаются только через policy, machine-readable registry, лицензионное подтверждение и изолированный adapter boundary.
