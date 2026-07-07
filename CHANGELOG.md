# Changelog

## gas-ratio-pro-phase2-specification

- Started Phase II — Engineering Specification & Architecture.
- Added Project Design Principles as the controlling project philosophy document.
- Added Master Project Specification v2.0 draft.
- Added Roadmap v3.0 with block-based planning instead of linear numeric stages.
- Added draft SRS, SAD, LAS Platform, Calculation Engine, Geological Modeling, UI/UX, Database and Testing specifications.
- Marked AI Assistant as excluded from the current roadmap.
- Marked Licensing / Hardware ID / Activation as deferred and optional.
- Reprioritized LAS Platform Professional as the first implementation block after documentation approval.

## gas-ratio-pro-updated-135

- Added Performance & Optimization Foundation backend module.
- Added project-level `performance_optimization.json` with normalized metrics, cache entries and optimization recommendations.
- Added timer measurement context manager, lightweight project cache with TTL/invalidation, memory estimation helpers and performance manifest builder.
- Added UI helper tables and regression tests for performance metrics, cache behavior, recommendations and manifest generation.


## gas-ratio-pro-updated-97

- Added `docs/eula.md` as the application End User License Agreement.
- Replaced the licensing page EULA placeholder with a real in-app EULA document panel.
- Updated project plan and user guide to point to License manager as the next licensing item.

## Application Licensing Page

- Added a dedicated `Лицензия` application tab for proprietary licensing and commercial-use rules.
- Connected dashboard quick action, main navigation and command palette to the license page.
- Rendered product identity, owner, copyright, contact, EULA placeholder and full `LICENSE` text in high-contrast adaptive panels.


## Dashboard 3.0

- Replaced the failed sparse dashboard regression with a complete Dashboard 3.0 layout.
- Restored useful information panels: project statistics, recent projects, recent LAS files, recent calculations, recent activity, project health and license status.
- Added a product-style left navigation rail and a compact overview header.
- Centered and constrained the branded background image for the dashboard shell.
- Kept duplicate `Open...` buttons out of the dashboard.


## Unreleased

- Added Curve Manager category tools for LAS curves with automatic category suggestions, manual overrides, category history, undo support, UI summary tables, metadata references and tests.


- Добавлена индексация файлов Project Database: `project_index.json` хранит metadata файлов активного проекта, SHA-256 и проверку отсутствующих/измененных файлов без копирования данных.

## Unreleased

- Добавлено месторождение в Well Manager: значение хранится как metadata `field`, нормализуется как короткая строка и отображается в карточке скважины и Project Explorer без изменения LAS-версий.

- Добавлена отметка GL в Well Manager: значение хранится как metadata `gl_m`, валидируется в метрах, отображается рядом с KB и показывает разницу `KB-GL` при наличии обеих отметок.

- Добавлена metadata-only карточка скважины Well Manager: статус, комментарий и отображение состояния карточки в Project Explorer без чтения LAS-пayload.

- Добавлено metadata-only перемещение объектов в Project Explorer: скважины можно переносить между группами, а скважины, LAS-версии, расчеты и экспорты добавлять в пользовательские папки без копирования данных.

- Добавлены пользовательские папки Project Explorer: `project_folders.json` хранит metadata-ссылки на объекты дерева без копирования LAS или расчетных таблиц.

- Добавлен компактный журнал действий по сохраненным расчетам проекта: сохранение snapshot, открытие snapshot в графиках, сравнение snapshots и скачивание CSV/XLSX/HTML-выгрузок.

- Added project calculation open warnings for saved snapshots that have no depth/DEPT/MD column or incomplete key gas mapping before sending them to interpretation graphs.
# Gas Ratio Interpreter v0.3

Локальное инженерное приложение для импорта газовых данных, сопоставления колонок,
расчета газовых коэффициентов, построения Pixler/ternary палеток, LAS-корреляции
и предварительной интерпретации интервалов по правилам.


## Быстрый старт

Требования:

- Windows 10/11, Linux или macOS
- Python 3.11+
- Git

Команды для Windows PowerShell:

```powershell
git clone <repo-url> gas-ratio-pro
cd gas-ratio-pro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest
python scripts/preflight.py
python -m streamlit run app/streamlit_app.py
```

После запуска Streamlit откроет локальный адрес вида:

```text
http://localhost:8501
```

Если проект уже находится на компьютере:

```powershell
cd C:\OSPanel\home\gas-ratio-pro
.\.venv\Scripts\Activate.ps1
python -m streamlit run app/streamlit_app.py
```

## Как проверить без рабочих данных

В проекте есть тестовые файлы:

```text
examples/sample_gas_data.csv
examples/sample_gas_data.las
```

Запустите приложение, загрузите LAS или CSV и оставьте автоматически найденную
строку заголовков. В интерфейсе должны появиться таблица расчетов, сводка
классификации, Pixler/ternary палетки и графики по глубине.

## Что умеет v0.3

- Импорт LAS, CSV, XLSX, XLSM.
- Мультизагрузка файлов в рабочем workflow с выбором набора данных.
- LAS-корреляция: загрузка нескольких LAS, распознавание ГИС/газовых кривых, сохранение настроек в локальный проект, соседние depth-треки, сравнение одной выбранной кривой между скважинами, печатный HTML-отчет, PNG/PDF/SVG экспорт и таблица выбранного интервала с CSV/XLSX/LAS-экспортом.
- LAS-редактор: проверка глубины, исправление убывающего порядка глубины, изменение шага, добавление строк, ручная правка, передача подготовленных данных в расчеты, точечное добавление строк по выбранному интервалу и сохранение подготовленного LAS в активный проект.
- Локальное хранение скважин в `data/wells/` с версиями и выгрузкой `CSV`, `XLSX`, `LAS`.
- Локальные проекты в `data/projects/<project_id>/`: карточка `project.json`, карточки скважин, версии исходных и подготовленных LAS проекта, открытие сохраненных LAS без повторной загрузки, расчетные snapshots с mapping/предупреждениями/CSV/XLSX, CSV/HTML-экспорт сравнения snapshots, настройки интерпретационных графиков, сохраненные версии экспортов и HTML-отчетов, ZIP-выгрузка выбранных версий в `LAS`, `XLSX`, `CSV`, архивирование ошибочно сохраненных версий и настройки LAS-корреляции `correlation_settings.json`.
- Чтение всех листов Excel.
- Автоматический поиск строки заголовков среди первых 50 строк.
- Ручной выбор строки заголовков.
- Автоматическое и ручное сопоставление колонок.
- Поддержка разных названий кривых: `Depth`, `DEPT`, `MD`, `CH4`, `Methane`, `i-C4`, `n-C4`, русские названия и другие алиасы.
- Расчет `Wh`, `Bh`, `BAR2`, Pixler ratios, ternary ratios, `oil_indicator`, `inverse_oil_indicator` и настраиваемого `Ch`.
- Предварительная инженерная классификация интервалов по проверяемым правилам.
- Pixler palette, ternary palette и depth tracks.
- Интерпретационные depth-графики с ручным диапазоном глубины, ручным X-масштабом, режимом `Планшет` для любых числовых параметров, LAS units в шапках треков, индивидуальными цветами треков, маркерами глубины и HTML-выгрузкой для печати, отдельным печатным отчетом выбранного интервала, таблицей маркеров и таблицей интерпретационных зон.
- Настройка Pixler/ternary палеток через `config/palettes.json`.
- Локальное диагностическое логирование в `logs/app.log`.
- Экспорт расчетной таблицы в CSV.
- Проектная выгрузка выбранных LAS-версий в ZIP с файлами `LAS`, `XLSX` и `CSV`.
- Сохранение расчетных snapshots проекта: расчетная таблица, mapping, режим `Ch`, предупреждения, выгрузки `CSV`/`XLSX` и CSV/HTML-экспорт сравнения двух snapshots.
- Сохранение настроек интерпретационных графиков проекта: треки, высота, диапазон глубины и X-scale.
- Сохранение версий экспортов проекта: HTML-отчеты графиков, печатные HTML-отчеты выбранных интервалов и CSV выбранных интервалов с последующим скачиванием из проекта.
- Pytest-набор для проверки расчетов, mapping, импорта, LAS, палеток, логирования и Streamlit-smoke.

## Важные ограничения

- Интерпретация является предварительной инженерной подсказкой.
- Результат требует проверки по ГИС, литологии, буровому контексту, фону, СПО, наращиваниям и рециркуляции.
- Формула `Ch` требует подтверждения по корпоративной методике.
- Границы зон Pixler/ternary в текущем конфиге являются черновыми и должны быть заменены на подтвержденные корпоративные линии.
- Планшетный renderer расширен: LAS units выводятся в шапке треков, порядок параметров берется из выбора пользователя, цвета и режимы заливки треков настраиваются, mud-gas preset добавляет типовые треки/маркеры, ручные интерпретационные зоны/интервалы включаются в печатный HTML-отчет. В плане остается дальнейшее уточнение расчетной методики и формул.
- PNG/PDF/SVG экспорт требует установленного `kaleido` из `requirements.txt`; полноценная база проектов планируется в следующих версиях.

## Карта документации

- [Установка и запуск](docs/setup.md)
- [План проекта](docs/project_plan.md)
- [Руководство пользователя](docs/user_guide.md)
- [Формат входных данных](docs/data_format.md)
- [План LAS-редактора](docs/las_editor_plan.md)
- [План multi-LAS корреляции](docs/las_correlation_plan.md)
- [Формулы](docs/formulas.md)
- [Mud gas analysis: литературный источник](docs/mud_gas_analysis_literature.md)
- [Конфигурация палеток](docs/palettes.md)
- [Логирование](docs/logging.md)
- [Архитектура и разработка](docs/development.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Правила ведения документации](docs/documentation_policy.md)
- [История изменений](CHANGELOG.md)

## Основные команды

```powershell
# Запуск тестов
python -m pytest

# Проверка готовности окружения
python scripts/preflight.py

# Запуск приложения
python -m streamlit run app/streamlit_app.py

# Просмотр последних строк лога
Get-Content logs/app.log -Tail 80

# Проверка текущего git-состояния
git status --short
```

- Добавлены координаты скважины в Well Manager: X/Y, широта/долгота, проверка диапазонов и отображение в Project Explorer.

## Dashboard responsive correction

- Reduced the low-content welcome rail on laptop widths so project statistics and activity panels fit without horizontal clipping.
- Centered the branded dashboard background and reduced its visual footprint for better readability.
- Added regression checks for laptop dashboard layout CSS rules.

## Dashboard UX Refactoring → Background Refinement

- Centered and contained the Dashboard 3.0 branded background artwork.
- Reduced dashboard background scale for notebook breakpoints.
- Added explicit 1366px, 1440px and 1600px background rules.
- Switched sidebar brand art from cover to contain to prevent cropping.

## Этап 128 — Geological Modeling Professional: Zone Manager

- Добавлен backend-слой Zone Manager для Geological Modeling Professional.
- Реализовано хранение инженерно утвержденных геологических зон в `geological_modeling.json` внутри проекта.
- Добавлены операции создания/обновления, удаления, фильтрации по скважине и типу зоны.
- Добавлены операции объединения смежных зон и разделения зоны по глубине.
- Добавлены цветовые схемы зон и табличное представление Zone Manager.
- Расширены тесты `tests/test_geological_modeling.py` для CRUD, merge/split, color scheme и валидации входных данных.


## gas-ratio-pro-updated-129

- Added Data Exchange Center foundation with project-level import/export records, exchange profiles, CSV/JSON/GeoJSON/XLSX helpers and project ZIP manifest export.
- Added validation tables for exchange issues and summary tables for Data Exchange records.
- Registered DLIS/LIS as planned professional exchange formats while keeping their binary parser/exporter for a later dedicated stage.
- Added tests for exchange CRUD, CSV/JSON/GeoJSON conversion, XLSX roundtrip, profiles, validation and project ZIP export.

## gas-ratio-pro-updated-130

- Added Advanced Plot Studio foundation: built-in professional layout presets for Triple Combo and Mud Gas Interpretation.
- Added template cloning for safe layout reuse across wells without overwriting source templates.
- Added renderer-independent preview specification with normalized track width percentages, curve payloads and annotation mapping.
- Added template validation issues and issue table helpers for export/rendering pre-checks.
- Added regression tests for presets, cloning, preview spec and validation.

## gas-ratio-pro-updated-131

- Added Advanced Correlation Studio Professional persistence layer with project-level correlation sessions in `correlation_studio.json`.
- Added session CRUD, status validation, table/summary helpers and project history integration.
- Added JSON import/export roundtrip for correlation sessions and export manifest generation for JSON/PNG/SVG/PDF targets.
- Connected persistent sessions with existing professional correlation primitives: markers, tie lines and depth alignments.
- Added regression tests for session CRUD, validation, JSON roundtrip, export manifest and marker object compatibility.

## gas-ratio-pro-updated-132

- Added Advanced Report Studio Professional backend layer.
- Added report packages with ordered reusable content blocks and report variables.
- Added package validation for missing sections, empty paragraphs and missing visual/table sources.
- Added renderer-independent render preview and render manifest for future PDF/DOCX/HTML adapters.
- Added deterministic lightweight HTML preview generation without Streamlit dependency.
- Added report export job status updates with project history integration.
- Added UI helper tables for packages, blocks and validation issues.
- Added regression tests for professional report packages, manifests, validation and job statuses.

## gas-ratio-pro-updated-133

- Added Plugin SDK foundation backend layer with project-level `plugin_sdk.json` registry.
- Added validated plugin manifests, SDK schema marker, SemVer checks, permission scopes and extension-point validation.
- Added plugin CRUD/status management with project history integration and safe enablement checks.
- Added plugin hook registry for supported application events and renderer/workflow/importer extension points.
- Added scaffold generator with `plugin.json`, `plugin.py` and README template for external plugin developers.
- Added API registry manifest for enabled plugins and UI helper tables for plugins, hooks and validation issues.
- Added JSON import/export helpers and regression tests for manifest roundtrip, registry, hooks, scaffold and validation.


## 134
- Added Scripting API foundation.

## Этап 136 — Release Candidate Stabilization

- Добавлен backend-слой `projects/release_candidate.py` для подготовки Release Candidate без включения лицензирования.
- Добавлена схема `gas-ratio-pro.release-candidate.v1` и проектный файл `release_candidate.json`.
- Реализованы release quality gates: source, documentation, tests, configuration, artifacts, performance, security и release.
- Добавлены проверки обязательных файлов, CHANGELOG, test inventory и py_compile для ключевых каталогов проекта.
- Добавлен release manifest со сводкой статусов, checklist и детерминированным file inventory fingerprint.
- Добавлена валидация release manifest и сохранение manifest в проект с записью в историю.
- Добавлены UI helper tables для будущей страницы Release Candidate Audit.
- Модуль экспортирован через `projects/__init__.py`.
- Добавлены regression-тесты Release Candidate.