
## Hydrocarbon Interpretation Engine v16

- Added structured `InterpretationLimitation` model.
- Added structured `InterpretationRecommendation` model.
- Added public builders for limitations and recommendations.
- Extended `InterpretationExplanation` with structured limitation/recommendation payloads.
- Updated Hydrocarbon Interval Engine schema to v16.

# Formula Source Audit

- Added formula/source audit for mud-gas and petrophysical calculations.
- Corrected core `CH` calculation to Haworth Character Ratio `(ΣC4 + ΣC5) / C3`.
- Updated formula documentation with bibliography, authorship and copyright/patent handling rules.
- Added regression tests for `CH` in the core calculation path and mud-gas interpretation path.

## Phase II → C.11 Model Validation & Audit Workspace Foundation

- Added `projects/model_validation_audit_workspace.py`.
- Added integrated geological model audit based on the C.10 dependency graph.
- Added checks for missing required model components, broken dependencies, orphan objects and metadata gaps.
- Added severity levels: `error`, `warning`, `info`.
- Added model readiness score and readiness status.
- Added audit manifest, UI-ready check/issue/coverage tables and Markdown audit report.
- Added profile tests for seeded models, missing components, broken dependencies, metadata warnings and saved audit records.

## Phase II → C.4 Interpolation Engine Foundation

- Added `projects/interpolation_engine.py`.
- Added regular grid generation for property modeling targets.
- Added interpolation samples, grid nodes and interpolated cell models.
- Implemented `nearest` interpolation.
- Implemented deterministic IDW interpolation with power, neighbor count, radius and optional Z support.
- Added conservative `simple_kriging_foundation` method as API-compatible placeholder for future full covariance-matrix kriging.
- Added interpolation job registry, seed data, manifest, UI-ready tables and Markdown reporting.
- Updated Roadmap and Geological/Property Modeling specifications.
- Added profile tests for grid generation, interpolation methods, job persistence, reporting and method validation.

## Phase II → B.15 Well Interval & Pay Zone Manager Foundation

- Added `las_editor/well_interval_manager.py`.
- Added deterministic interval classification from Formation Evaluation Summary results.
- Added gross/net/pay interval flags, reservoir flags, pay flags and configurable cutoffs.
- Added gross, net and pay thickness calculations with Net/Gross, Pay/Gross and Pay/Net ratios.
- Added interval split/merge helpers for professional interval editing workflows.
- Added UI-ready interval/issue tables, audit manifest and Markdown pay-zone report.
- Added profile tests for interval derivation, custom cutoffs, thickness summary, split, merge and reporting.

## Phase II → B.14 Formation Evaluation Summary Foundation

- Added `las_editor/formation_evaluation_summary.py`.
- Added integrated well/interval summary based on LAS QC, mud-gas interpretation and curve statistics.
- Added interval-level reservoir flags, dominant fluid character, confidence, QC counters and property averages.
- Added UI-ready interval/issue tables, audit manifest and Markdown engineering report.
- Added source reference support for evidence-backed interpretation reports.
- Added profile tests for summary generation, explicit intervals, manifest, UI helpers and Markdown report.

## Phase II — B.8 Documentation Evidence & Citation Audit Foundation

- Added `projects/documentation_evidence.py`.
- Added audit for `docs/sources/source_registry.json`, registered PDF files and documentation references.
- Added detection of local Windows paths such as `C:\Users\...` in committed documentation.
- Added checks for missing registered sources, missing referenced PDFs, unregistered PDF references and orphan source files.
- Added UI-ready source/reference/issue tables, evidence manifest and Markdown audit report.
- Added profile tests for documentation evidence validation and reporting.


## Phase II — B.7 Reference Sources Manager Foundation

- Added `projects/reference_sources.py`.
- Added project PDF source registry support.
- Added source copying/compression workflow for PDF evidence files.
- Added validation for missing sources and local Windows path references.
- Added UI-ready source and validation tables.
- Added `docs/sources/` with registered project reference PDFs.
- Added Reference Sources specification draft.

## Phase II B.5 — LAS Validator Professional Foundation

- Добавлен модуль `las_editor/las_validator.py`.
- Реализована проверка обязательных LAS-секций `~Version`, `~Well`, `~Curve`, `~Parameter`, `~ASCII`.
- Добавлена проверка LAS header cards, обязательных depth/header элементов и дубликатов.
- Добавлена сверка секции `~Curve` с колонками ASCII-таблицы.
- Добавлена проверка ASCII-данных: глубина, дубликаты, шаг, STRT/STOP, NULL-значения.
- Добавлены validation report, summary, UI-ready таблицы и markdown-render отчета качества.
- Модуль экспортирован через `las_editor/__init__.py`.
- Добавлены профильные тесты `tests/test_las_validator_professional.py`.

## Phase II B.3 — LAS Header Editor Professional Foundation
## Phase II B.4 — LAS ASCII Data Editor Professional Foundation

- Добавлен модуль `las_editor/ascii_data_editor.py`.
- Реализованы операции редактирования секции `~ASCII`: изменение ячейки, массовое редактирование диапазона, вставка и удаление строк.
- Добавлены сортировка по глубине, поиск/замена значений, проверка дубликатов глубины и нарушений шага.
- Добавлены UI-ready таблицы, сводка ASCII-данных, preview изменений и render ASCII body.
- README переписан в кратком пользовательском формате на русском языке без внутренних Roadmap и правил разработки.
- Добавлены профильные тесты `tests/test_las_ascii_data_editor_professional.py`.


- Added `las_editor/header_editor.py` for professional LAS header metadata editing.
- Added normalized header cards for `~Version`, `~Well`, `~Curve` and `~Parameter` sections.
- Added default header card builder for newly created LAS files.
- Added add/update/delete operations with protection for mandatory cards such as `VERS`, `WRAP`, `STRT`, `STOP`, `STEP`, `NULL` and `DEPT`.
- Added header validation for mandatory LAS items, positive depth step and reversed depth ranges.
- Added render helpers for LAS header sections and UI-ready header tables.
- Added operation history entries and safe header-only diagnostics.
- Added regression tests for Header Editor backend operations, validation, rendering and protected item behavior.


## Phase II B.2 — LAS Curve Manager Professional Foundation

- Added `las_editor/curve_manager.py` as a unified metadata-safe Curve Manager layer.
- Added curve manifest generation with order, protected flag, aliases, groups, categories, units, quality, status and sample statistics.
- Added managed add/delete/reorder/update operations for LAS curves without overwriting source LAS files.
- Added UI-ready Curve Manager table helpers.
- Updated `README.md` with project summary, author, setup, launch and testing instructions.
- Added tests for Curve Manager Professional foundation.

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
## Phase II Implementation — LAS Platform Professional B.1

- Started implementation from `ROADMAP_v3.0` using Specification First workflow.
- Added `las_editor/las_creator.py` for LAS creation from scratch.
- Added `LasCreationSpec`, `LasCurveSpec`, `LasCreationResult` and LAS validation issue objects.
- Added built-in LAS templates: `empty`, `mud_gas`, `petrophysics`.
- Added depth index generation, mandatory LAS sections and UTF-8 LAS writer text/bytes output.
- Added basic professional curve operations: add non-depth curve, delete non-depth curve, mnemonic/unit normalization.
- Exported LAS creation API through `las_editor/__init__.py`.
- Added regression tests for LAS Creation Wizard backend, templates, validation and curve add/delete operations.
## Phase II Implementation — LAS Platform Professional B.6

- Added LAS Safe Export Professional foundation with safe destination validation.
- Added built-in LAS template profiles for empty, mud gas and petrophysical LAS workflows.
- Added export manifests with schema marker, status, target/source paths, data size, row/curve counts and validation summary.
- Added source-overwrite protection: exported LAS files cannot be saved over the original source LAS path.
- Added existing-target protection unless overwrite is explicitly enabled for a non-source target.
- Added safe LAS text/document export helpers and UI-ready export/template tables.
- Exported safe export API through `las_editor/__init__.py`.
- Added regression tests for template profiles, safe path validation, source overwrite blocking and safe LAS writing.

## Phase II — B.9 LAS Curve Import Professional Foundation

- Added `las_editor/curve_importer.py`.
- Added safe CSV/XLSX curve import helpers.
- Added curve import planning before merge.
- Added exact, nearest and interpolation depth matching policies.
- Added conflict policies: skip, suffix and replace.
- Added import manifest, UI-ready plan tables and issue tables.
- Added tests for curve import workflow.

## Phase II — B.10 LAS Curve Calculator Professional Foundation

- Added `las_editor/curve_calculator.py`.
- Added safe formula validation without Python `eval`/`exec`.
- Added calculated curve workflow for working copies of LAS ASCII tables.
- Added built-in formula templates for Haworth wetness/balance/character ratios, Pixler C1/C2, oil indicator, inverse oil indicator, Net/Gross and porosity percent.
- Added supported formula functions: `IF`, `ABS`, `SQRT`, `LOG`, `LOG10`, `EXP`, `ROUND`, `MIN`, `MAX`.
- Added preview rows, calculated curve specs, UI-ready issue/template tables and calculation manifest.
- Exported Curve Calculator API through `las_editor/__init__.py`.
- Added regression tests for formula validation, calculation, templates, IF logic, manifest and safe non-destructive behavior.

## Phase II — B.11 LAS Quality Control Professional Foundation

- Added `las_editor/las_quality_control.py`.
- Added LAS quality-control profiles for common well-log curves.
- Added depth QC: duplicate samples, non-monotonic depth and missing/irregular depth intervals.
- Added curve QC: missing values, negative values, expected range checks, spikes, flat-line segments, statistical outliers and unit mismatch warnings.
- Added UI-ready issue/profile tables.
- Added quality-control manifest and Markdown report renderer.
- Exported LAS Quality Control API through `las_editor/__init__.py`.
- Added regression tests for the new QC foundation.

## Phase II B.12 — LAS Processing Pipeline Professional Foundation

- Added `las_editor/las_processing_pipeline.py`.
- Added reproducible non-destructive LAS curve processing pipelines.
- Added operations: moving average, median filter, despike, null filling, min-max normalization, z-score normalization, clipping and depth resampling.
- Added processing plan validation, operation history, processing manifest, preview data and Markdown processing report.
- Exported the processing API through `las_editor/__init__.py`.
- Added regression tests in `tests/test_las_processing_pipeline_professional.py`.

## Phase II B.13 — Mud Gas Interpretation Toolkit Foundation

- Added `las_editor/mud_gas_interpretation.py`.
- Added Haworth wetness, balance and character ratio calculation support.
- Added Pixler C1/C2 fluid-character classification support.
- Added Oil Indicator and Inverse Oil Indicator classification support.
- Added combined per-depth mud-gas interpretation rows.
- Added interval summaries, UI-ready tables, Markdown report and interpretation manifest.
- Exported the mud gas interpretation API through `las_editor/__init__.py`.
- Added regression tests in `tests/test_mud_gas_interpretation_professional.py`.

## Phase II - B.16 Petrophysical Workspace Foundation

- Added `las_editor/petrophysical_workspace.py`.
- Added transparent petrophysical calculations for Vsh, PHIE, Archie Sw, SO, RES/NET/PAY and NG flags.
- Added petrophysical interval summaries, manifest generation and Markdown report rendering.
- Added profile tests for the new Petrophysical Workspace foundation.

## Phase II - B.17 Advanced Saturation Models Foundation

- Added `las_editor/advanced_saturation_models.py`.
- Added advanced water-saturation calculations: Archie, Simandoux, Indonesia and Dual Water foundation.
- Added deterministic model comparison by interval with average Vsh, model spread, recommendation and confidence.
- Added validation for required curves, numeric model parameters and output curve conflicts.
- Added manifest generation, UI-ready issue/comparison tables and Markdown report rendering.
- Exported Advanced Saturation Models API through `las_editor/__init__.py`.
- Added regression tests in `tests/test_advanced_saturation_models.py`.

## Phase II - B.18 Petrophysical Crossplot Workspace Foundation

- Added `las_editor/petrophysical_crossplot_workspace.py`.
- Added backend crossplot specifications for Pickett, Hingle, Buckles, Density-Neutron, Sonic-Density and GR-Resistivity plots.
- Added depth-window filtering, linear trend summaries, deterministic cluster summaries and UI-ready tables.
- Added crossplot manifest generation and Markdown report rendering.
- Exported Petrophysical Crossplot Workspace API through `las_editor/__init__.py`.
- Added regression tests in `tests/test_petrophysical_crossplot_workspace.py`.

## Phase II — B.19 Reservoir Property Calculator Foundation

- Added `las_editor/reservoir_property_calculator.py`.
- Added deterministic BRV, NRV, PV, HCPV, OOIP and OGIP foundation calculations.
- Added interval summaries, recovery estimates, manifests, Markdown reporting and UI-ready tables.
- Added tests for reservoir volumetric calculations.

## Phase II — B.20 Petrophysical Report Package Foundation

- Added `las_editor/petrophysical_report_package.py`.
- Added normalized report sections for Petrophysical Workspace, Advanced Saturation Models, Petrophysical Crossplots, Well Intervals and Reservoir Volumes.
- Added deterministic package manifest, Markdown report renderer and UI-ready section/issue tables.
- Added evidence source aggregation for report packages.
- Exported Petrophysical Report Package API through `las_editor/__init__.py`.
- Added regression tests in `tests/test_petrophysical_report_package.py`.

## Phase II — C.1 Property Modeling Workspace Foundation

- Added `projects/property_modeling_workspace.py`.
- Added property cube metadata registry for facies, lithology, NG, porosity, permeability and saturation properties.
- Added fluid contact and geometry property foundation.
- Added Net/Gross calculation from facies labels.
- Added property statistics, manifest, UI-ready tables and Markdown report.
- Added profile tests for Property Modeling Workspace.

## Phase II — C.2 Facies Modeling Workspace Foundation

- Added `projects/facies_modeling_workspace.py`.
- Added facies registry with reservoir/pay candidate flags and color metadata.
- Added zone-based facies modeling settings.
- Added vertical proportion curve calculation.
- Added discrete facies statistics and run-length summary.
- Added facies simulation job manifest foundation.
- Added UI-ready tables and Markdown reporting.
- Added profile tests for Facies Modeling Workspace.

## Phase II — C.3 Geostatistics Workspace Foundation

- Added `projects/geostatistics_workspace.py`.
- Added experimental variogram calculation from spatial samples.
- Added theoretical variogram models: spherical, exponential, gaussian, linear and nugget.
- Added deterministic foundation model fitting for experimental variogram bins.
- Added search ellipsoid metadata for future Kriging/SGS workflows.
- Added geostatistics jobs, manifest generation, UI-ready tables and Markdown report rendering.
- Exported Geostatistics Workspace API through `projects/__init__.py`.
- Added regression tests in `tests/test_geostatistics_workspace.py`.

## Phase II — C.5 Property Simulation Engine Foundation

- Added `projects/property_simulation_engine.py`.
- Added Sequential Gaussian Simulation foundation for continuous property realizations.
- Added Sequential Indicator Simulation foundation for facies/discrete property realizations.
- Added reproducible seed-based simulation, realization metadata, uncertainty and confidence fields.
- Added simulation job registry, manifest generation, UI-ready tables and Markdown report rendering.
- Exported Property Simulation Engine API through `projects/__init__.py`.
- Added regression tests in `tests/test_property_simulation_engine.py`.

## Phase II - C.6 Fluid Contacts & Geometrical Properties Foundation

- Added `projects/fluid_contacts_geometry.py`.
- Added fluid contact registry for OWC, GOC, GWC, FWL and custom contacts.
- Added constant/surface contact metadata with confidence and source tracking.
- Added geometry calculations: Cell Height, Cell Volume, Bulk Volume, Depth, Elevation, Relative Depth and Above Contact.
- Added contact set coding for gas/oil/water zones.
- Added job registry, manifest, Markdown report and UI-ready tables.
- Added tests for contact classification, geometry properties, manifest and reports.

## Phase II — C.7 Reservoir Volumetrics Workspace Foundation

- Added `projects/reservoir_volumetrics_workspace.py`.
- Added grid/property-level volumetric calculations: BRV, NRV, PV, HCPV.
- Added foundation OOIP/OGIP and recoverable estimates.
- Added cutoffs for porosity, water saturation, net flag and pay flag.
- Added zone summaries, uncertainty summary, manifest, Markdown report and UI-ready tables.
- Added tests for reservoir volumetrics workspace.

## Phase II - C.8 Geological Model Workspace Foundation

- Added `projects/geological_model_workspace.py`.
- Added Geological Model Workspace foundation with model/grid/horizon/zone/surface/fault registries.
- Added model links for wells, intervals, facies, property cubes and volumetrics.
- Added workspace validation, manifest, Markdown report and UI-ready helper tables.
- Added tests for C.8 workspace persistence, validation and reporting.

## Phase II - C.9 Structural Modeling Workspace Foundation

- Added `projects/structural_modeling_workspace.py`.
- Added Structural Framework registry, Horizon Manager, Horizon Groups, Fault Manager Foundation, Zone/Layer Framework and Surface registry.
- Added structural validation for missing horizons/surfaces, invalid depth ranges, top/base consistency and fault horizon links.
- Added layer generation helper, manifest, Markdown report and UI-ready helper tables.
- Exported Structural Modeling Workspace API through `projects/__init__.py`.
- Added regression tests in `tests/test_structural_modeling_workspace.py`.

## Phase II - C.10 Geological Model Integration Workspace Foundation

- Added `projects/geological_model_integration_workspace.py`.
- Added integrated model object registry for geological model, structural model, grids, facies, property cubes, volumetrics, wells, LAS datasets, reports and source documents.
- Added dependency graph foundation for tracing model inputs, outputs, derived objects and documentation references.
- Added integration views, validation, manifest, Markdown report and UI-ready helper tables.
- Exported Geological Model Integration Workspace API through `projects/__init__.py`.
- Added regression tests in `tests/test_geological_model_integration_workspace.py`.

## Engineering Review & Project Redesign — Roadmap v4.0

- Added full project audit document.
- Added ROADMAP_v4.0 focused on UI/UX, Plot Studio, Report Studio, LAS visibility and Geological Modeling UI.
- Added MASTER_PROJECT_SPECIFICATION_v3.0.
- Added LAS Workspace Redesign specification.
- Added Plot Studio Professional Redesign specification.
- Added Report Studio 2.0 specification.
- Added Geological Modeling Workspace Redesign specification.
- Added implementation plan after Roadmap v4.0.
- Marked triangular diagram as requiring repair/redesign.
- Deferred project packaging until core workflows and UI are corrected.

## Project Manager 2.0 backup restore foundation

- Added managed project backup restore from Project Manager 2.0 ZIP archives.
- Added safe ZIP extraction with path traversal protection.
- Added overwrite protection for existing project directories.
- Added service-layer backup, restore and recovery checkpoint methods.
- Added tests for restore workflow, overwrite protection and service integration.

## Application State Controller cleanup foundation

- Added generic application-owned session value helpers to `ApplicationStateController`.
- Routed interpretation dataset storage through the application-state controller.
- Added regression tests preventing direct `st.session_state` writes in the interpretation storage helper.

## Architecture Review LTS Freeze Checklist

- Added Architecture Review documentation for the post-Sprint 1.5 gate.
- Added Core LTS Freeze checklist before Sprint 2 Workspace Framework.
- Added regression tests for required freeze-gate sections and core architecture rules.


## Hydrocarbon Interval Engine v9

- Added Method Registry for report-facing calculation methods.
- Added interval evidence provenance metadata.
- Added method/source fields to structured evidence records.
- Updated hydrocarbon interval schema to v9.

## Hydrocarbon Interval Engine v11

- Added auditable interpretation rule model.
- Added rule traces for interval-level decision explanation.
- Added applied rule IDs to interval/table/marker payloads.
- Added interpretation status for practical reporting workflows.
- Added rule-based confidence adjustment factors.
- Updated interval schema to `gas-ratio-pro/hydrocarbon-intervals/v11`.


## Hydrocarbon Interval Engine v12

- Added validation case model for practical geology scenarios.
- Added validation result export rows for QA tables.
- Added public API contract for report, plot, UI and export consumers.
- Updated schema to `gas-ratio-pro/hydrocarbon-intervals/v12`.

## Hydrocarbon Interval Engine v13

- Added `HydrocarbonInterpretationContext`.
- Added data/geological confidence split.
- Added engineer-facing `decision_level`.
- Added grouped `evidence_tree` for UI/report explanations.
- Added neighbor/barrier context enrichment.
- Updated schema to `gas-ratio-pro/hydrocarbon-intervals/v13`.

## Hydrocarbon Interpretation Engine v15

- Added `InterpretationExplanation` as the engineer-facing explanation package for every interval.
- Added explanation summaries to interval, marker and public API payloads.
- Added cautious preliminary interpretation wording and recommendation/limitation blocks.
- Updated schema to `gas-ratio-pro/hydrocarbon-intervals/v15`.

## Hydrocarbon Interval Engine v14

- Stabilized the public Hydrocarbon Interval Engine payload for downstream UI, plot, report and export consumers.
- Added engineer-facing result summary that focuses on intervals, fluid type, confidence and review status instead of internal row counters.
- Added technical payload opt-in for diagnostics, row counts, method registry and expert/debug views.
- Updated schema to `gas-ratio-pro/hydrocarbon-intervals/v14`.

## Hydrocarbon Interpretation Engine v17

- Added built-in Validation Dataset v2 for regression checks of practical geological scenarios.
- Added validation catalog helpers: `hydrocarbon_validation_cases`, `hydrocarbon_validation_case_frame`, `hydrocarbon_validation_catalog_rows`.
- Added `run_hydrocarbon_validation_suite` as a public regression suite entry point.
- Added no-numeric-data interpretation rule for missing gas-ratio evidence.
- Updated public API contract and schema to `gas-ratio-pro/hydrocarbon-intervals/v17`.
