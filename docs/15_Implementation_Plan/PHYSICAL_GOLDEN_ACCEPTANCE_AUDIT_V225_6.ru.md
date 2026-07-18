# План реализации v225.6 — Golden artifacts, Print Center acceptance и legacy audit

## Цель

Закрепить физическую компоновку A4/A3, проверить реальный пользовательский экспортный путь и превратить 51 известное падение в управляемый реестр решений.

## Выполнено

1. Добавлен десятидорожечный fixture с интервалами.
2. Сформированы SVG/PNG/PDF golden-artifacts для четырёх профилей.
3. Добавлены generate/verify service и regeneration script.
4. Реализован end-to-end acceptance runner с profile persistence.
5. Проверены HTML/PDF/DOCX bundle и multi-page SVG/PNG ZIP.
6. Исправлено масштабирование raster preview в PDF frame.
7. Все 51 legacy contract классифицированы без silent `xfail`.
8. Документация и release metadata синхронизированы на трёх языках.

## Результат проверки

- 150 целевых тестов проходят.
- Полный suite: 2853 теста, 2802 проходят, 51 унаследованное падение.
- Реестр и фактический набор падений совпадают 1:1; новых регрессий нет.
