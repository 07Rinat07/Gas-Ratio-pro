# Project Roadmap — v225.3

Обновлено: 18 июля 2026 года.

Этот документ — **единственная активная последовательность** разработки Gas Ratio Pro. Версионные roadmap-файлы, старые progress/next-step документы и параллельные планы хранятся только в `docs/archive/legacy_plans/`.

Локализованные версии: [Русский](PROJECT_ROADMAP.ru.md) · [Қазақша](PROJECT_ROADMAP.kk.md) · [English](PROJECT_ROADMAP.en.md).

## Stage 4 — Workbench UI Completion

Статус: **ACTIVE**.

Текущая цель — завершить единый пользовательский путь от рабочей области до Professional Print Center без независимых экспортных веток.

Завершено в v225.3:

- единые физические зоны header/footer/legend/content;
- page-space chrome для SVG и PDF;
- PNG из тех же SVG-страниц;
- geometry signature v3;
- единый `VisualizationPageAwarePackage`;
- UI-neutral `VisualizationPrintCenterService`;
- один page-aware pipeline для LAS Viewer SVG/PDF/PNG.

Следующие разрешённые работы:

1. подключить локализованную сводку пакета к видимому Professional Print Center;
2. передавать многостраничный page-aware preview непосредственно в DOCX/HTML;
3. удалить legacy static-export ветки только после автоматизированной parity-проверки;
4. добавить пользовательские шаблоны физических профилей и сохранить запрет уменьшения текста ниже допустимого минимума.

## Stabilization & Release Audit

Статус: **Release candidate v225.3**.

Перед каждым выпуском обязательны:

- полный regression-прогон;
- проверка SVG/PDF/PNG/DOCX/HTML parity;
- проверка A4/A3, ориентации, DPI, полей, page count и порядка треков;
- синхронизация README, инструкций, CHANGELOG, статуса и плана на русском, казахском и английском языках;
- проверка documentation manifest, относительных ссылок, версии сборки и архива релиза.

## Petrophysical Engine

Статус: **BLOCKED**.

Расширение петрофизического движка запрещено до завершения Stage 4 и Stabilization & Release Audit. Допускаются только исправления критических дефектов, не меняющие утверждённый расчётный контракт.

## Release gate

Релиз может считаться готовым только при выполнении всех условий:

- один layout и одна geometry signature для всех представлений;
- отсутствие silent fallback на первую страницу;
- воспроизводимые эталонные артефакты;
- тесты и документация соответствуют фактической реализации;
- три языковые версии не расходятся по функциям, ограничениям и следующему этапу.

## Reservoir Intelligence / Interpretation 2.0

Статус: **FROZEN AFTER ACCEPTANCE**. Контракт сохраняется как обязательный Definition of Done для регрессии существующей интерпретации:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- инженерная сводка интервалов и воспроизводимая визуальная классификация;
- Definition of Done: все утверждённые представления используют один расчётный результат, проходят регрессионные тесты и не изменяются в рамках print/export-инкремента.

## Open Standards and Legal Research Governance

Любая интеграция внешнего стандарта или third-party component выполняется только через утверждённые policy-документы, machine-readable registry, подтверждение лицензии и изолированный adapter boundary. Исследовательский прототип не становится production dependency без отдельного review status.
