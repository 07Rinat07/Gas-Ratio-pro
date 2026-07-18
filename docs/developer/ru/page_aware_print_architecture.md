# Архитектура page-aware печати и прямого preview

Revision: 2 · GAS RATIO PRO v225.4

## Единый источник геометрии

`VisualizationScenePipeline` создаёт физический `VisualizationPrintLayout` v2.1. `VisualizationPageAwarePackageBuilder` формирует пакет v1.2 со всеми SVG/PNG-страницами, многостраничным PDF, geometry signature v3, page chrome и QA-результатом.

## Application bridge

`ReportPageAwarePreviewService` является единственной границей от текущего `DataFrame` отчёта к физическому пакету. Он вызывает `LasVisualizationPayloadService.build_from_frame()`, затем `VisualizationPrintCenterService.prepare()` и прикрепляет renderer-neutral payload к `PresentationModel`.

Сырые строки `DataFrame` downstream не передаются.

## Preview contract v1.1

Канонический контракт `visualization.preview.page-aware` содержит массив `pages`. Каждая страница включает `index`, `track_ids`, `width_pt`, `height_pt`, число chrome primitives и готовый SVG. Флаги `single_page_fallback=false` и `legacy_svg_fallback_allowed=false` являются обязательными.

`reports.visualization_preview.normalize_visualization_preview()` — общий строгий нормализатор для HTML, DOCX, PDF и asset export. Для page-aware схемы он не использует compatibility-поля `svg` или `page_svgs`, если отсутствует канонический `pages`.

## Видимый Print Center

`build_professional_print_center_view()` преобразует один prepared package в UI-контракт: точный профиль, статус, geometry signature и полный список preview-страниц. Streamlit хранит результат по сигнатуре параметров и передаёт тот же report payload при экспорте.

## Инварианты

- один pipeline и одна geometry signature;
- layout downstream не перестраивается;
- DOCX/HTML получают все физические страницы напрямую;
- формат `bundle` использует тот же пакет;
- подписи и сообщения синхронизированы для `ru/kk/en`;
- page count mismatch блокирует корректный статус preview;
- удаление legacy static-export веток допускается только после parity-аудита.
