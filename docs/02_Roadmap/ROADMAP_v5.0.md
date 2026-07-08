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

## Phase 3.1 — LAS Merge / Append and GIS Curve Insert Safety

Обязательное уточнение Roadmap v5.0 для LAS Workspace 3.0.

Редактор LAS должен поддерживать три безопасных сценария:

1. **Сращивание LAS-файлов по глубине**
   - объединение интервалов из нескольких LAS;
   - выравнивание колонок по единой структуре кривых;
   - сортировка итоговой рабочей копии по глубине;
   - политика обработки дубликатов глубины: keep_first, keep_last, keep_all, error;
   - исходные LAS не изменяются.

2. **Вставка данных ГИС из другого LAS**
   - выбор кривых из LAS-источника;
   - вставка выбранных кривых в текущий рабочий LAS;
   - сопоставление по глубине: exact, nearest, interpolate;
   - политика конфликтов имен кривых: skip, suffix, replace;
   - исходный и целевой LAS не изменяются, результат создается как рабочая копия.

3. **Безопасный Depth Repair**
   - при убывающей глубине создается backup оригинального LAS;
   - создается рабочая копия LAS для исправления;
   - ремонт выполняется только над рабочей копией;
   - строки сортируются по глубине стабильной сортировкой;
   - значения GR, RHOB, газовых и остальных кривых остаются в той же строке относительно своей исходной глубины;
   - оригинальный LAS не перезаписывается.

Реализация:

- `las_editor.las_merge_append_center`;
- `las_editor.curve_importer`;
- `las_editor.depth_repair`.

Acceptance Criteria:

1. Сращивание LAS-файлов не мутирует входные данные.
2. Вставка кривых из LAS не мутирует исходный LAS и текущий рабочий LAS.
3. Все операции возвращают manifest для Operation Journal.
4. Depth Repair создает backup и working copy перед исправлением.
5. UI показывает эти инструменты постоянно, а недоступные действия переводит в disabled-состояние с причиной.

## Phase 3.0 — LAS Creation Wizard Priority Update

Создание нового LAS является обязательной базовой функцией редактора и переносится в ближайший приоритет реализации LAS Workspace 3.0.

Редактор должен уметь создавать LAS без предварительно открытого файла. Инструмент **New LAS** всегда отображается в LAS Workspace и Home Workspace.

Функциональные требования:

1. **New LAS без загруженного файла**
   - кнопка создания LAS видна сразу;
   - пользователь может создать LAS с нуля;
   - после создания файл открывается как рабочая копия в LAS Workspace.

2. **LAS Creation Wizard**
   - Header Builder: Well, UWI/API, Company, Field, Location, Service Company;
   - Depth Generator: start, stop, step, unit;
   - Template Manager: empty, mud gas, petrophysics;
   - Curve Library: стандартные ГИС, газовые и петрофизические кривые;
   - ASCII Builder: автоматическая генерация таблицы;
   - Validate Before Save: проверка обязательных секций и монотонности глубины.

3. **Постоянная видимость инструментов**
   - New LAS;
   - Open LAS;
   - Merge / Append;
   - GIS Curve Insert;
   - Depth Repair;
   - Validator;
   - Diagnostics;
   - Export.

4. **Безопасность**
   - создание нового LAS не изменяет существующие LAS;
   - сохранение выполняется только в новый файл или рабочую копию;
   - все действия должны быть готовы для Operation Journal.

Реализация:

- `las_editor.las_creation_wizard`;
- `las_editor.las_creator`;
- `las_editor.las_merge_append_center`;
- `las_editor.depth_repair`.

Acceptance Criteria:

1. LAS можно создать без открытого файла.
2. Все инструменты LAS Workspace видны всегда.
3. Недоступные действия могут быть disabled, но не скрываются.
4. Wizard возвращает manifest для UI.
5. Созданный LAS содержит `~Version`, `~Well`, `~Curve`, `~Parameter`, `~ASCII`.
6. Созданный LAS можно сразу передать в Validator, Plot Studio и Export Center.


## Sprint 1 — Storage Lifecycle Framework

Sprint 1 не считается завершенным, пока не реализован Storage Lifecycle Framework.

Обязательные компоненты:

- ResourceManager;
- FileHandleManager;
- DeleteEngine;
- BackupEngine;
- CacheManager;
- IndexManager;
- Retry Delete;
- Session Cleanup;
- UI Refresh;
- Diagnostics.

Архитектурное правило: любые операции создания, удаления, переименования и очистки файлов проекта должны автоматически синхронизировать Repository, файловую систему, Project Storage Index и UI.

## Sprint 1 Update — IndexManager Integration

`IndexManager` включен в обязательный Storage Lifecycle Framework.

Обновленное правило: Dataset/LAS/Export/Report/Project delete считается завершенным только после физического удаления, обновления manifest/repository и автоматического rebuild Project Storage Index.

Реализовано в текущем проходе:

- `IndexManager.rebuild_project_index(...)`;
- `IndexManager.validate_project_index(...)`;
- `IndexManager.sync_after_delete(...)`;
- автоматическая синхронизация индекса после операций DatasetManagerService;
- команда `🧹 Перестроить индекс` в Project Database UI.


### Storage Lifecycle Update

- CacheManager реализован.
- FileHandleManager реализован.
- DatasetManagerService интегрирован с освобождением file handles/cache перед удалением.

## Sprint 1 Service Compatibility Pass — DatasetManagerService

- Fixed Dataset Manager public service contract.
- Added LAS section support to DatasetManagerService so `Dataset Manager · LAS` uses the same lifecycle-managed delete/clear path as CSV, Excel, Core, Mud Log and Production.
- Dataset destructive operations must release resources, file handles and cache entries, delete through DeleteEngine and rebuild Project Database index through IndexManager.
- Added service contract document: `docs/09_Architecture/contracts/DATASET_MANAGER_SERVICE_CONTRACT.md`.



### Service Compatibility Pass — ProjectManagerService

- Project deletion is routed through `DeleteEngine`.
- Recent project history cleanup stays behind `ProjectManagerService`.
- Project index synchronization is exposed through the service contract.
- Compatibility aliases are preserved for the current Streamlit UI during Sprint 1/Sprint 1.5.
