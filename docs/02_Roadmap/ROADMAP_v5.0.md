# GAS RATIO PRO — Roadmap v5.0

## Цель Roadmap v5.0

Roadmap v5.0 фиксирует переход проекта от набора отдельных модулей к единой промышленной инженерной платформе с общим каркасом приложения, единым управлением рабочими пространствами и строгим контролем состояния данных.

## Ключевое архитектурное изменение

Перед дальнейшим расширением функциональности вводится **Workspace Framework 2.0**. Все рабочие пространства подключаются к единому Application Shell и используют общий механизм очистки временных данных.

## Phase 0 — Repository and Documentation Hygiene

- документация хранится только в `docs/`;
- в корне остаются только файлы запуска, конфигурации, лицензии и README;
- служебные файлы ИИ, временные отчеты и history-файлы не хранятся в проекте;
- планы, спецификации и changelog находятся внутри `docs/`.

## Phase 1 — Workspace Framework 2.0

### 1.1 Application Shell

- общий каркас приложения;
- единая верхняя зона приложения;
- единая боковая навигация;
- единый статус-бар;
- управление активным workspace;
- единая точка входа для Home, LAS, Plot, Correlation, Petrophysics, Modeling и Reports.

### 1.2 Workspace Registry

- регистрация рабочих пространств;
- единый API workspace;
- подключение новых модулей без переписывания главного приложения;
- метаданные: id, title, icon, category, order, enabled.

### 1.3 Project Explorer

- дерево проекта;
- Wells;
- LAS files;
- Curves;
- Interpretations;
- Correlation;
- Petrophysics;
- Geological Modeling;
- Reports;
- Templates;
- Settings.

### 1.4 Ribbon / Toolbar System

- Home;
- Project;
- LAS;
- Processing;
- Curves;
- Plot;
- Correlation;
- Interpretation;
- Petrophysics;
- Modeling;
- Reports;
- Settings.

### 1.5 Global Session State Reset Policy

Обязательный пункт Roadmap v5.0.

При смене проекта, скважины, LAS-файла или рабочего пространства приложение обязано сбрасывать все производные данные:

- таблицы;
- статистики;
- dashboard metrics;
- расчетные DataFrame;
- графики;
- планшеты;
- результаты диагностики;
- результаты валидации;
- временные отчеты;
- preview-данные;
- маркеры;
- интерпретации текущей сессии;
- результаты корреляции текущей сессии;
- временные данные геомоделирования.

Не сбрасываются только глобальные настройки:

- тема;
- язык;
- лицензия;
- EULA;
- пользовательские настройки;
- глобальные настройки workspace.

Реализация: `core/session_state_manager.py`.

### 1.6 Command System

- единый механизм операций;
- undo/redo;
- operation journal;
- безопасные операции только над копиями данных;
- подготовка к макросам.

### 1.7 Layout Manager

- сохранение раскладок интерфейса;
- профили: LAS Editor, Petrophysics, Correlation, Modeling, Reports;
- восстановление layout при повторном открытии проекта.

## Phase 2 — Home Workspace 2.0

- последние проекты;
- последние LAS;
- последние отчеты;
- быстрые действия;
- создание LAS;
- открытие LAS;
- импорт CSV/Excel;
- шаблоны;
- состояние проекта;
- видимость всех ключевых инструментов.

## Phase 3 — LAS Workspace 3.0

- Create LAS;
- Open LAS;
- Header Designer;
- Curve Manager;
- ASCII Spreadsheet;
- Validator;
- Diagnostics;
- Cleanup;
- Merge / Append;
- Depth Repair;
- Curve Calculator;
- Processing Pipeline;
- Export Center;
- Operation Journal.

Все инструменты должны быть видны пользователю в рабочем пространстве, даже если файл еще не загружен. Недоступные действия отображаются в disabled-состоянии с объяснением причины.

## Phase 4 — Plot Studio 3.0

- tracks;
- layers;
- curves;
- annotations;
- templates;
- zoom;
- manual scale;
- synchronized scrolling;
- export;
- printing.

## Phase 5 — Correlation Workspace 3.0

- профессиональные планшеты;
- литология;
- пласты;
- кровля/подошва;
- ВНК/ГНК/ГВК;
- нефть/газ/вода/газоконденсат;
- ручная и автоматическая корреляция;
- таблица результатов;
- печать.

## Phase 6 — Petrophysics Workspace

- расчет параметров;
- нормализация кривых;
- saturation models;
- пористость;
- shale volume;
- cutoffs;
- net pay;
- отчетность.

## Phase 7 — Geological Modeling Workspace

- structural modeling;
- fault modeling;
- grid;
- facies modeling;
- property modeling;
- reservoir volumetrics;
- model validation and audit.

## Phase 8 — Report Studio

- шаблоны;
- HTML preview;
- PDF export;
- Word/Excel export;
- печать;
- автоматические инженерные отчеты.

## Phase 9 — Plugin System

- внешние инструменты;
- пользовательские модули;
- расширяемые расчетные алгоритмы;
- расширяемые шаблоны отчетов.

## Текущий следующий этап реализации

После фиксации Roadmap v5.0 реализация продолжается с:

**Workspace Framework State Reset**

Цель: гарантировать, что все таблицы и статистики не показывают старые данные после смены проекта, скважины, LAS или workspace.
