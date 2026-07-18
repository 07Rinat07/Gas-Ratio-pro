# План проекта Gas Ratio Pro

Обновлено: 18 июля 2026 года. Активная сборка: `v225.4`.

Языковые версии: [Русский](PROJECT_PLAN.ru.md) · [Қазақша](PROJECT_PLAN.kk.md) · [English](PROJECT_PLAN.en.md).

## Обязательные инженерные принципы

- один pipeline является единственным источником page geometry;
- UI, PDF, DOCX, HTML, SVG и PNG используют renderer-neutral contracts;
- A4/A3 и пользовательские профили соблюдают минимальную читаемую типографику;
- multi-page preview не может молча сокращаться до первой страницы;
- документация и инструкции обновляются синхронно на `ru / kk / en`.

## Завершённый этап — v225.4

- видимый Print Center подключён к физическому пакету;
- добавлен просмотр каждой страницы и точная preflight-сводка;
- page-aware package v1.2 и preview contract v1.1;
- прямой multi-page preview для DOCX/HTML;
- общий strict normalizer для HTML/DOCX/PDF/assets;
- локализованные подписи и сообщения;
- `bundle` использует тот же payload.

## Следующий разрешённый инкремент — Parity Gate & Legacy Export Retirement

1. Сформировать автоматическую parity-матрицу для UI, PDF, DOCX, HTML, SVG и PNG.
2. Проверить A4/A3, обе ориентации, track partition, page count, geometry signature и page chrome.
3. Удалить независимые static/Plotly fallback-ветки только после успешной parity-проверки.
4. Добавить пользовательские физические профили с валидацией минимальных размеров.
5. Обновить тесты и всю документацию на трёх языках.

## Definition of Done

- физический пакет виден до запуска;
- все форматы используют канонический `pages` contract;
- повторный layout отсутствует;
- single-page fallback отсутствует;
- parity подтверждена тестами и эталонными артефактами;
- version metadata, README, инструкции, status, roadmap, changelog и manifest синхронизированы.
