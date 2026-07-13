## Latest implementation — Report Output Modes

- Added user-selectable Brief, Standard and Full Engineering report modes.
- Added Custom mode for manual template and section control.
- Report modes resolve through the existing renderer-neutral Report Designer.
- Export cache signatures now include the selected report mode.
- Next priority: table of contents and PDF bookmarks.

## Latest implementation — Export Performance and Memory Guard

- ExportController now limits artifact cache by count and actual binary payload size.
- Default artifact memory budget: 64 MiB per application session.
- Oversized artifacts are returned to the user but are not retained in cache.
- cache_metrics() exposes model entries, artifact entries and retained bytes.
- Next priority: large-LAS rendering benchmarks and selective dataframe downsampling.

# Latest implementation increment — Unified Chart Theme Engine

Completed:
- centralized Plotly visual profiles for screen, print and presentation;
- standardized typography, grids, axes, margins, legend surfaces, line widths and markers;
- added deterministic theme signatures for renderer/export cache invalidation;
- kept scientific data and axis ranges unchanged during visual styling;
- added regression tests for profile selection, immutability and export behavior.

Next priority: optimize large-LAS visualization and export performance.

# Latest increment — Unified Tooltip and Operation Feedback Layer

Status: COMPLETED

Implemented:
- centralized tooltip registry in `ui/ux_feedback.py`;
- validated progress plan for professional report export;
- Report Designer UI uses shared tooltip keys instead of duplicated text;
- progress stages are deterministic and covered by tests.

Next priority: expand tooltip coverage and start unified chart theme integration.

# GAS RATIO PRO — AI HANDOFF

## Текущее состояние

Готово:

- импорт LAS;
- автоматический и ручной mapping;
- расчет коэффициентов и интерпретация;
- инженерные планшеты;
- экспорт DOCX и PNG;
- Industrial PDF Layout;
- Professional Export Wizard;
- preflight-проверка экспорта;
- Professional Report Designer foundation;
- Streamlit Report Designer integration;
- designed PDF/DOCX/bundle export with cache-safe settings.

## Последний реализованный инкремент

Professional Report Designer UI Integration:

- шаблоны Engineering, Corporate и Minimal подключены к Streamlit;
- добавлены настройки заголовка, состава разделов, технического приложения и колонтитулов;
- PDF, DOCX и bundle строятся из одного designed EngineeringDocument;
- параметры дизайна включены в сигнатуру export cache;
- PNG, SVG и XLSX сохранены как отдельные специализированные каналы;
- добавлены интеграционные тесты.

## Следующий этап

1. Интерактивный preview структуры отчета.
2. Единый tooltip/help layer для Report Designer и Export Wizard.
3. Индикаторы выполнения операций.
4. Унификация графиков.
5. Оптимизация производительности.

## Архитектурные правила

- Не выполнять повторные инженерные расчеты в UI и renderers.
- Использовать PresentationModel и EngineeringDocument как единые источники данных.
- Не ухудшать производительность.
- Не ломать существующие export contracts.
- PDF должен выглядеть как промышленный инженерный отчет.

# Latest increment — Large-LAS Performance Acceptance Gates

Status: COMPLETED

Implemented:
- deterministic large-LAS benchmark payloads;
- cold/warm visualization pipeline measurements;
- acceptance gates for latency, memory, cache reuse and downsampling reduction;
- JSON CLI report via `scripts/run_large_las_benchmark.py`;
- regression tests for gate evaluation and real pipeline behavior.

Next priority: CI integration and runtime performance summary UI.
