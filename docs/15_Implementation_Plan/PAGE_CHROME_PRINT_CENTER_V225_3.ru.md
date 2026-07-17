# Page Chrome & Print Center Contract v225.3

## Цель

Добавить общие физические колонтитулы, номер страницы и повторяемую легенду, а также предоставить центру печати точный профиль и page count из одного page-aware пакета.

## Реализовано

1. `VisualizationPrintLayout` v2.1 резервирует header/footer/legend области.
2. `chrome_primitives` строятся один раз в `page_pt`.
3. SVG и PDF рисуют одинаковые primitives, PNG создаётся из SVG.
4. Geometry signature v3 включает page chrome.
5. `VisualizationPageAwarePackage` v1.1 передаёт chrome contract и counts.
6. `VisualizationPrintCenterService` формирует локализованную сводку ru/kk/en.
7. LAS Viewer export использует один пакет для SVG/PDF/PNG.
8. QA проверяет общую совокупность render-model и page-chrome primitives.

## Критерии приёмки

- page number присутствует на каждой физической странице;
- легенда повторяется без пересчёта layout;
- PDF/SVG/PNG имеют одинаковый page count и signature;
- A4/A3 readability floors сохранены;
- single-page fallback отключён;
- документация ru/kk/en синхронизирована.
