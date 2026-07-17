# Текущее состояние — v225.3

Обновлено: 18 июля 2026 года.

Завершён инкремент **Page Chrome & Print Center Contract**:

- `VisualizationPrintLayout` обновлён до версии 2.1;
- физическая страница получила отдельные `header_bounds`, `footer_bounds`, `legend_bounds` и `chrome_primitives`;
- заголовок, подзаголовок, классификация, код документа, footer, номер страницы и повторяемая легенда строятся один раз в координатах `page_pt`;
- русский, казахский и английский варианты нумерации и заголовка легенды синхронизированы;
- SVG и PDF рисуют одни и те же page-space primitives, PNG растеризуется из тех же SVG-страниц;
- geometry signature обновлена до v3 и включает физические зоны страницы и page chrome;
- `VisualizationPageAwarePackage` обновлён до версии 1.1;
- добавлен `VisualizationPrintCenterService`, показывающий точный профиль, ориентацию, DPI и число страниц до передачи форматов;
- LAS Viewer export переведён на один page-aware пакет для SVG/PDF/PNG;
- single-page fallback остаётся отключённым.
- фоновый экспорт снова запускается через `ThreadPoolExecutor`, поэтому progress и cooperative cancellation работают во время выполнения;

Документация пользователя и разработчика обновлена синхронно на `ru / kk / en`, manifest дополнен.

Локализованные статусы: [Русский](PROJECT_STATUS.ru.md) · [Қазақша](PROJECT_STATUS.kk.md) · [English](PROJECT_STATUS.en.md).

Следующий разрешённый инкремент: подключить локализованную сводку физического пакета непосредственно к видимому Professional Print Center, передавать page-aware preview в DOCX/HTML без legacy-пути и после parity-проверки удалить оставшиеся независимые static-export ветки.

## Управление выпуском

Текущая стадия: **Stabilization & Release Audit**. Сборка **release candidate v225.3** проходит проверку единого page-aware pipeline, трёхъязычной документации и воспроизводимых эталонных артефактов.

## Проверка v225.3

- 362 профильных, renderer, Print Center, background-export и documentation governance теста проходят;
- Python compileall и проверка относительных ссылок проходят;
- полный suite из 2831 теста не завершился в доступном окне выполнения; первая диагностическая выборка из 20 падений была сопоставлена с исходным архивом v225.2;
- 2 roadmap-contract падения устранены в v225.3, остальные 18 падений этой выборки без изменений воспроизводятся в v225.2; возможные более поздние legacy-падения не классифицированы;
- сборка остаётся release candidate до отдельного полного аудита устаревших legacy-UI тестовых контрактов.
