# GAS RATIO PRO — ROADMAP v4.0

**Статус:** новый основной Roadmap проекта  
**Основание:** пользовательский аудит, пересмотр UI/UX и переход от foundation-модулей к профессиональным Workspaces  

---

## 0. Принцип Roadmap v4.0

Roadmap v4.0 строится не вокруг отдельных backend-модулей, а вокруг рабочих процессов инженера:

```text
Создать/открыть проект
↓
Создать или загрузить LAS
↓
Проверить и отредактировать данные
↓
Построить информативные графики
↓
Выполнить расчеты и интерпретацию
↓
Выделить интервалы и флюиды
↓
Сформировать PDF/Excel/PNG/DOCX отчет
↓
При необходимости перейти к геомоделированию
```

Новые функции не считаются готовыми, пока они не доступны пользователю через понятный интерфейс.

---

# A. UI Shell & Workspace Framework

## A.1 Application Shell Redesign

Цель: заменить набор отдельных страниц на профессиональную оболочку инженерного приложения.

Требования:

- Sidebar как основная навигация;
- Ribbon/Toolbar для текущего workspace;
- Project Explorer слева;
- Workspace center;
- Inspector/Properties справа;
- Output/Logs снизу;
- статус-бар проекта;
- единый стиль кнопок, вкладок, таблиц и карточек.

## A.2 Workspace Registry

- регистрация всех рабочих пространств;
- единая точка входа;
- доступность workspace без предварительной загрузки файла, если это логично;
- empty-state панели с действиями.

## A.3 Action Panel Components

- красивые кнопки действий;
- группы инструментов;
- раскрывающиеся панели;
- disabled/enabled state с объяснением причины.

---

# B. LAS Workspace Professional Redesign

## B.1 LAS Start Screen

Ключевое исправление: пользователь должен видеть создание LAS даже без загруженного файла.

Должны быть кнопки:

- Создать LAS;
- Открыть LAS;
- Импорт CSV/Excel;
- Шаблоны LAS;
- Последние файлы;
- Проверить пример.

## B.2 LAS Creation Wizard UI

- Well information;
- depth range;
- step;
- null value;
- units;
- curve template;
- preview;
- export to new LAS.

## B.3 LAS Editor Tools Panel

Инструменты должны быть видимыми и раскрываемыми:

- Header Editor;
- Curve Manager;
- ASCII Editor;
- Validator;
- Curve Calculator;
- Processing Pipeline;
- Quality Control;
- Safe Export.

## B.4 LAS Print & Export

- export LAS;
- export PDF summary;
- export Excel workbook;
- export PNG/SVG plots;
- export ZIP report package.

---

# C. Plot Studio Professional Redesign

## C.1 Plot Engine Audit

- проверить текущие графики;
- определить, какие графики неинформативны;
- удалить/переписать слабые графики.

## C.2 Manual Scale Controls

Для каждой дорожки:

- X min;
- X max;
- scale type: linear/log;
- auto/manual;
- reverse axis;
- units.

Для глубины:

- Depth From;
- Depth To;
- step/grid;
- синхронизация всех дорожек.

## C.3 Mouse Interaction

- zoom wheel;
- pan;
- drag;
- box zoom;
- reset;
- crosshair;
- tooltips;
- track hover.

## C.4 Plot Markers & Annotations

Добавить отображение:

- gas;
- oil;
- water;
- condensate;
- OWC;
- GOC;
- GWC;
- FWL;
- pay zones;
- reservoir zones;
- perforations;
- core;
- tests;
- comments.

## C.5 Plot Print Range

- печать всей скважины;
- печать выбранного интервала;
- печать нескольких интервалов;
- preview страницы;
- масштаб дорожек;
- orientation: portrait/landscape.

## C.6 Plot Export

- PDF;
- PNG;
- SVG;
- TIFF;
- JPEG;
- HTML как дополнительный формат, а не основной.

---

# D. Interpretation Workspace

## D.1 Well Interpretation Summary

- интерпретация по всей скважине;
- флюид по интервалам;
- confidence;
- reservoir/pay flags;
- итоговые таблицы.

## D.2 Fluid Marking System

- gas/oil/water/condensate/no show;
- transition zone;
- uncertain zone;
- custom labels.

## D.3 Mud Gas Interpretation UI

- Haworth ratios;
- Pixler ratios;
- Oil Indicator;
- графики по глубине;
- интервализация;
- выводы.

## D.4 Triangular Diagram Repair

Статус: broken / redesign required.

Требования:

- корректная нормализация компонентов;
- проверка входных кривых;
- сообщение при отсутствии данных;
- интерпретационные зоны;
- легенда;
- тестовые dataset;
- экспорт PNG/PDF/SVG.

---

# E. Report Studio 2.0

## E.1 Report Export Core

Поддерживаемые форматы:

- PDF;
- DOCX;
- XLSX;
- PNG;
- SVG;
- TIFF;
- JPEG;
- HTML;
- Markdown.

## E.2 Well Report Package

Секции отчета:

- общее описание скважины;
- LAS summary;
- QC summary;
- plot pages;
- mud gas interpretation;
- petrophysics;
- intervals;
- fluid interpretation;
- volumetrics;
- conclusions.

## E.3 Excel Workbook Export

Листы:

- Curves;
- QC;
- Mud Gas;
- Petrophysics;
- Intervals;
- Fluids;
- Volumetrics;
- Sources.

## E.4 Print Template Manager

- шаблоны печати;
- логотип/титульный лист;
- размеры страниц;
- поля;
- шапки/подвалы;
- автоматическая нумерация страниц.

---

# F. Data Browser & Project Explorer

## F.1 Project Explorer

Показывать:

- projects;
- wells;
- LAS files;
- curves;
- reports;
- plots;
- intervals;
- geological models;
- sources.

## F.2 Data Browser

- таблицы данных;
- фильтрация;
- поиск;
- сортировка;
- preview;
- export.

---

# G. Geological Modeling Workspace UI

## G.1 Geological Modeling Home

Пользователь должен видеть, что можно делать:

- создать структурную модель;
- создать grid;
- задать горизонты;
- задать зоны;
- задать контакты;
- построить фации;
- построить property cubes;
- рассчитать объемы;
- проверить модель.

## G.2 Structural Modeling UI

- Horizon Manager;
- Fault Manager;
- Zone/Layer Manager;
- Surface Manager;
- validation panel.

## G.3 Property Modeling UI

- property cube list;
- facies;
- NG;
- POR;
- PERM;
- SW/SO/SG;
- statistics;
- preview.

## G.4 Geostatistics UI

- variogram viewer;
- model fitting;
- search ellipsoid;
- interpolation jobs;
- simulation jobs.

## G.5 Volumetrics UI

- BRV/NRV/PV/HCPV;
- OOIP/OGIP;
- zone summaries;
- uncertainty low/base/high.

---

# H. Job Manager

## H.1 Long Operations

Любая длительная операция должна выполняться как job:

- import;
- export;
- interpolation;
- simulation;
- report generation;
- model validation.

## H.2 Job UI

- progress;
- cancel;
- retry;
- logs;
- status;
- result preview.

---

# I. Settings & Preferences v2

- plot defaults;
- units;
- export formats;
- color palettes;
- keyboard shortcuts;
- workspace layout;
- autosave;
- theme.

---

# J. Testing & Stabilization

## J.1 UI Regression Tests

- empty project screen;
- LAS creation visible;
- plot scale controls visible;
- report export controls visible.

## J.2 Golden Dataset Tests

- sample LAS;
- sample mud gas;
- sample petrophysics;
- sample report.

## J.3 Broken Feature Tracking

Особый статус:

- triangular diagram;
- weak plots;
- missing export formats;
- invisible LAS creation;
- geological modeling UI missing.

---

# K. Deferred / Optional

Пока не реализуются:

- AI Assistant;
- Licensing / Hardware ID;
- Cloud Sync;
- Multi-user mode;
- telemetry.

---

## Немедленный порядок реализации после утверждения Roadmap v4.0

1. A.1 Application Shell Redesign.
2. B.1 LAS Start Screen.
3. B.2 LAS Creation Wizard UI.
4. C.2 Manual Scale Controls for plots.
5. C.3 Mouse Interaction for plots.
6. E.1 Report Export Core.
7. E.3 Excel Workbook Export.
8. D.4 Triangular Diagram Repair.
9. G.1 Geological Modeling Home.
10. F.1 Project Explorer.

## A.1 LAS Workspace Home & Action Launcher — Implemented

Цель: убрать пустой экран LAS-редактора и показать пользователю основные действия даже без загруженного файла.

Реализовано:
- видимое рабочее пространство `LAS Workspace 2.0`;
- карточки действий: `Создать LAS`, `Открыть LAS`, `Импорт CSV`, `Импорт Excel`, `Шаблоны LAS`, `Проверка LAS`;
- мастер создания LAS с параметрами скважины, глубины, шаблона и пользовательских кривых;
- предпросмотр созданного LAS;
- сохранение созданного LAS в рабочую сессию;
- скачивание нового LAS без перезаписи исходных файлов.

Критерий приемки: пользователь может начать работу с LAS Platform без предварительно загруженного файла.

---

# Roadmap v4.0 Update — LAS Merge, Depth Repair, Correlation Redesign

**Статус:** обязательное обновление Roadmap v4.0  
**Причина:** пользовательский аудит выявил дополнительные критичные проблемы LAS Editor и Correlation Workspace.

## B.5 LAS Merge & Append Center — Required

Цель: редактор LAS должен уметь объединять и сращивать LAS-файлы одной скважины, а также вставлять данные из одного LAS в другой.

Требования:

- сращивание LAS-файлов по глубине;
- объединение нескольких LAS одной скважины;
- вставка кривых из другого LAS, включая ГИС-данные;
- вставка данных из отдельного LAS в текущий LAS без потери исходных данных;
- выбор главного LAS-файла;
- проверка совпадения скважины, единиц измерения, глубинного диапазона и шага;
- выбор политики конфликтов кривых:
  - заменить;
  - пропустить;
  - переименовать с суффиксом;
  - оставить обе версии;
- выравнивание глубины:
  - exact;
  - nearest;
  - interpolate;
- предварительный просмотр результата перед объединением;
- отчет изменений по кривым, глубинам, NULL-значениям и конфликтам;
- безопасное сохранение только в новый LAS-файл;
- исходные LAS-файлы никогда не перезаписываются.

## B.6 LAS Depth Repair & Direction Correction — Required

Цель: редактор LAS должен исправлять некорректное направление глубины и другие проблемы depth index.

Обязательный пользовательский сценарий:

> Если в LAS глубина не нарастает вниз, а убывает, редактор должен уметь исправить это и создать новую копию LAS. При этом значения кривых не должны пересчитываться, перемешиваться или подменяться. По умолчанию исправляется именно столбец глубины, а значения кривых остаются в своих исходных строках измерений.

Требования:

- автоматическое определение направления глубины:
  - возрастает;
  - убывает;
  - перемешана;
  - содержит дубликаты;
  - содержит пропуски шага;
- исправление убывающей глубины в возрастающую;
- пересчет `STRT`, `STOP`, `STEP`;
- проверка знака `STEP`;
- восстановление регулярного depth index;
- удаление/обработка дубликатов глубины только после подтверждения пользователя;
- preview до/после;
- отчет исправлений;
- безопасное сохранение исправленного LAS только как новой копии.

Критически важно:

- операция `Depth Direction Correction` по умолчанию **не сортирует строки вместе со значениями кривых**;
- операция не должна менять значения `GR`, `RT`, `RHOB`, `NPHI`, `C1`, `C2` и других кривых;
- операция должна менять только depth vector и связанные header cards;
- альтернативный режим `Sort Rows With Curve Values` допускается только как отдельная явная опция с предупреждением пользователю.

## C.7 Correlation Workspace Redesign — Required

Проблема: в текущей вкладке корреляции скважины и LAS-файлы отображаются разрозненно, пользователю непонятно, какие скважины сравниваются, по каким кривым, маркерам, интервалам и правилам выполняется корреляция.

Требования:

- создать понятный Correlation Workspace вместо разрозненного отображения LAS;
- добавить Well Selection Panel;
- добавить Correlation Track Layout;
- показывать, какие LAS-файлы назначены каждой скважине;
- показывать выбранные корреляционные кривые;
- добавить Marker Manager:
  - tops;
  - formations;
  - contacts;
  - user markers;
- добавить Tie Line Manager;
- добавить режимы корреляции:
  - by depth;
  - by formation tops;
  - by selected curve similarity;
  - manual tie-lines;
- добавить понятную легенду и подписи;
- добавить синхронизацию глубины между скважинами;
- добавить ручной выбор глубинного интервала;
- добавить export correlation panel в PDF/PNG/SVG;
- добавить пустое состояние с объяснением: `Выберите минимум две скважины для корреляции`.

Критерий приемки: пользователь должен понимать, какие скважины коррелируются, по каким данным и где находятся маркеры/линии корреляции.


## Phase A.2 — LAS Workspace Master Specification + Project Explorer Foundation

Status: implemented foundation.

Scope:
- global Project Explorer tree;
- contextual LAS actions from selected well/LAS/curve;
- Operation Journal foundation;
- Undo/Redo foundation;
- LAS Workspace Master Specification v2.0;
- safe descending-depth repair rule.

Acceptance rule for depth repair:
If `GAS_SUM = 10%` at `500 m` before repair, then `GAS_SUM = 10%` must remain at `500 m` after sorting depth to ascending order.
