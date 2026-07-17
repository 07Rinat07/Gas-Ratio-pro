# Unified Page-Aware Package v225.2

## Цель

Передавать из Visualization Engine в Professional Print Center один проверяемый физический пакет страниц вместо независимых SVG/PDF/PNG веток.

## Реализовано

1. `VisualizationPageAwarePackageBuilder` принимает только `visualization.scene.pipeline.result`.
2. Пакет сохраняет профиль A4/A3, ориентацию, DPI, геометрическую подпись и разбиение треков.
3. Каждая страница содержит согласованные SVG и PNG представления.
4. PDF содержит то же количество физических страниц.
5. `preview_contract()` передаёт DOCX/HTML все SVG-страницы без повторного layout.
6. Одностраничный fallback отключён контрактно.
7. Asset Registry записывает артефакты из единого пакета.

## Критерии приёмки

- page count одинаков для print layout, SVG, PNG и PDF;
- порядок и покрытие track IDs не меняются;
- geometry signature одинакова во всех renderer-ах;
- PDF открывается и содержит ожидаемое число страниц;
- DOCX preview получает `page_svgs`, а не только первую страницу;
- invalid pipeline не запускает fallback.

## Следующий инкремент

Подключить пакет непосредственно к one-click Print Center UI, добавить общий page chrome (заголовок, номер страницы, footer, повторяемая легенда) как primitives render model.
