# Архитектура page-aware печати

Revision: 1 · GAS RATIO PRO v225.3

## Граница системы

`VisualizationScenePipeline` вычисляет физический `VisualizationPrintLayout` версии 2.1. Каждая страница содержит `content_bounds`, `header_bounds`, `footer_bounds`, `legend_bounds`, `track_ids` и `chrome_primitives`.

`chrome_primitives` используют `coordinate_space=page_pt`. SVG и PDF обязаны рисовать их без повторного масштаба и без content clip. PNG создаётся из готовых SVG-страниц.

## Единый пакет

`VisualizationPageAwarePackageBuilder` формирует один пакет версии 1.1:

- все SVG-страницы;
- все PNG-страницы;
- один многостраничный PDF;
- geometry signature v3;
- page chrome contract;
- QA-результат.

`VisualizationPrintCenterService` формирует локализованную сводку ru/kk/en и один output contract для PDF, SVG, PNG и DOCX/HTML preview. Перестроение layout downstream запрещено.

## Инварианты

- один pipeline является единственным источником геометрии;
- номера страниц и легенда имеют одинаковые координаты во всех renderer-ах;
- page count и track partition совпадают во всех форматах;
- single-page fallback равен `false`;
- legacy-путь удаляется только после parity-тестов.
