# План проекта Gas Ratio Pro

Обновлено: 18 июля 2026 года. Активная сборка: `v225.3`.

Языковые версии: [Русский](PROJECT_PLAN.ru.md) · [Қазақша](PROJECT_PLAN.kk.md) · [English](PROJECT_PLAN.en.md).

## Обязательные инженерные принципы

- инженерные данные, треки и шкалы не сокращаются ради печати;
- UI, PDF, DOCX, SVG и PNG используют renderer-neutral contracts;
- один pipeline является единственным источником page geometry;
- A4/A3 используют физические параметры и минимальную читаемую типографику;
- экспорт запускается одним действием и блокирует повторный запуск до завершения пакета;
- пользовательские и developer-инструкции обновляются синхронно на русском, казахском и английском языках.

## Завершённый этап — v225.3

- общие page-space колонтитулы и нумерация;
- повторяемая легенда из renderer-neutral label/legend model;
- geometry signature v3;
- page-aware package v1.1;
- локализованная Print Center summary;
- LAS Viewer SVG/PDF/PNG через один пакет;
- QA учитывает render-model и page-chrome primitives.

## Следующий инкремент — Visible Print Center Integration

1. Показывать физический профиль и точное число страниц в Professional Print Center до запуска.
2. Передавать существующий page-aware output contract в PDF, DOCX, SVG и PNG.
3. Подключить `page_svgs` к DOCX/HTML без повторного layout.
4. Сохранить блокировку повторного запуска на время всего пакета.
5. Удалить независимые Plotly/static fallback-ветки после подтверждённой parity-проверки.
6. Обновить код, тесты, README, инструкции, статус, changelog и планы на `ru / kk / en`.

## Definition of Done

- фактический page count виден до запуска;
- все форматы используют одну geometry signature;
- page chrome и легенда совпадают между SVG/PDF/PNG/DOCX preview;
- single-page fallback отсутствует;
- целевые и регрессионные тесты проходят;
- документация и version metadata полностью синхронизированы.
