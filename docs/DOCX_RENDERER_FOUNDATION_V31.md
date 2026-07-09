# DOCX Renderer Foundation v31

## Назначение

`reports/presentation_docx.py` добавляет базовый DOCX-рендерер для Professional Reporting System.

Ключевое архитектурное правило сохраняется:

> инженерское содержание собирается один раз в `EngineeringDocument`, а HTML/PDF/DOCX только отображают его.

DOCX-рендерер не вызывает расчет коэффициентов, не запускает Rule Engine и не перестраивает карточки интервалов. Он принимает готовый `EngineeringDocument` и формирует `.docx` пакет.

## Реализовано

- `PresentationDocxOptions` — параметры DOCX-вывода;
- `PresentationDocxResult` — результат рендера;
- `render_engineering_document_docx()` — рендер `EngineeringDocument` в DOCX bytes;
- `build_presentation_docx_report()` — сборка DOCX из `PresentationModel` через `EngineeringDocument`;
- `export_presentation_docx_package()` — запись `.docx` и `.docx.manifest.json`;
- поддержка A4/A3/Letter и portrait/landscape;
- защита полей страницы от некорректных значений;
- таблицы, заметки и plot placeholder используют общую Document Model.

## Что пока намеренно не реализовано

- встраивание реального изображения планшета в DOCX;
- фирменные стили титульной страницы;
- DOCX-шаблоны организации;
- автоматическое содержание;
- колонтитулы и нумерация страниц.

Эти пункты должны развиваться после стабилизации общего Document Model и PDF/DOCX pipeline.

## Следующий шаг

Следующий логичный инкремент — унификация export package для HTML/PDF/DOCX или подключение реального plot image renderer, чтобы планшет один раз генерировался и одинаково вставлялся в PDF/DOCX.
