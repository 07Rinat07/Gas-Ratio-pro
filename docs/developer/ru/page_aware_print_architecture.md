# Архитектура page-aware печати и прямого preview

Revision: 4 · GAS RATIO PRO v225.6

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

## Cross-format parity gate v1.0

`VisualizationCrossFormatParityGate` выполняется внутри `VisualizationPageAwarePackageBuilder`. Он сверяет layout, package pages, SVG root dimensions, PNG IHDR dimensions, фактическое число PDF-страниц, canonical preview pages, track partition и geometry signature. `VisualizationPageAwarePackage.export_ready` требует `parity_gate.ok=true`.

`VisualizationPageAwarePackage` обновлён до v1.3. `VisualizationPrintCenterSummary` и UI view model публикуют `parity_gate_id` и `cross_format_parity_passed`.

## Пользовательские физические профили

`UserPhysicalPrintProfileStore` хранит JSON schema `gas-ratio-pro.physical-print-profiles` в `data/user_preferences/physical_print_profiles.json`. `VisualizationPrintLayoutEngine` принимает сериализованный `physical_profile`. Пользовательские A4/A3 профили могут усиливать readability floors и уменьшать page capacity, но не могут ослаблять базовые ограничения.

## Retirement static-export

Professional report и LAS Viewer используют `build_page_aware_static_artifact()`. Одностраничный SVG/PNG выдаётся напрямую, многостраничный — ZIP с manifest. Независимая CompositeLog SVG/PNG/PDF ветка в `reports.export_static` удалена и заменена явным запретом legacy path. Обычные Plotly-графики остаются на Kaleido и не считаются физическим Print Center документом.

## Physical golden artifacts v225.6

`VisualizationPhysicalGoldenArtifactService` строит один десятидорожечный renderer-neutral fixture для `a4_portrait`, `a4_landscape`, `a3_portrait` и `a3_landscape`. Для каждой физической страницы сохраняются SVG и PNG, для профиля — один многостраничный PDF. `manifest.json` фиксирует SHA-256, размеры в points/pixels, track partition, chrome primitive count, geometry signature и parity gate id.

Эталон обновляется только командой `python scripts/regenerate_physical_golden_artifacts.py` после визуального review. Тест повторной генерации сравнивает structural signature и визуальные checksums.

## End-to-end Print Center acceptance

`ProfessionalPrintCenterAcceptanceRunner` выполняет application-level путь без raw DataFrame downstream: profile store → `ReportPageAwarePreviewService` → visible view model → `PresentationModel` → HTML/PDF/DOCX bundle → SVG/PNG static delivery. Результат сохраняется как `print-center-acceptance-report.json`.

Для PDF добавлен `_AutoScaleRasterImage`. Размер физического preview определяется в `wrap()` по фактическим `avail_width` и `avail_height`, поэтому portrait/landscape комбинации не вызывают ReportLab `LayoutError`.

## Legacy regression audit

`config/legacy_regression_contracts_v225_6.json` содержит все 51 inherited failure. Каждый contract имеет category, disposition, severity, rationale и replacement contract. Политика запрещает silent `xfail`, скрытие architecture debt и удаление тестов без замены.
