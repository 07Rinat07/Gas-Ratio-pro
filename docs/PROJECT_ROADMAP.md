# GAS RATIO PRO — Active Project Roadmap

Status: Active  
Baseline: v208  
Purpose: единственная активная последовательность реализации проекта.

## 1. Обязательные правила

- Работать только с последним подтверждённым архивом.
- UI не содержит бизнес-логику и инженерные вычисления.
- Не создавать боковые подсистемы вне активного этапа.
- Новый этап начинается только после Definition of Done текущего этапа.
- Каждый инкремент проходит: реализация → тесты → исправление → preflight → архив.
- Документация обновляется в существующих управляющих файлах; отдельные version-note документы по умолчанию не создаются.

## 2. Целевая архитектурная цепочка

```text
Source Adapter
→ Domain Model
→ Scene
→ Layout
→ Axis / Grid
→ Track
→ Curve Quality
→ Label / Legend
→ Print Layout
→ Render Model
→ Renderers
```

Поток данных продукта:

```text
LAS → Core → Interpretation → Presentation → UI / Reports
```

## 3. Активная последовательность работ

### Stage 1 — Visualization Engine completion

Status: **COMPLETED v179**

Цель: завершить графическое ядро и доказать одинаковую, печатно пригодную геометрию SVG/PDF.

Оставшиеся обязательные задачи:

1. Точечное исправление дефектов, обнаруживаемых Render Validation Pipeline.
2. Расширенная проверка коллизий легенд, осей и track headers.
3. Визуальная проверка эталонных multi-track сцен и фиксация ожидаемых артефактов. **COMPLETED v177**
4. Проверка Unicode и читаемости печати на эталонных экспортных файлах.
5. Финальный performance/large-LAS regression. **COMPLETED v179 — 1743 tests passed; preflight OK**

Definition of Done:

- validation pipeline не только сообщает ошибки, но предотвращает некорректный export;
- SVG и PDF используют один Render Model и одинаковую geometry signature;
- эталонные сцены проходят автоматическую и визуальную QA;
- большие LAS не приводят к неконтролируемому росту памяти;
- полный test suite и preflight проходят.

### Stage 2 — LAS Viewer completion

Status: **COMPLETED v186**

Цель: собрать уже реализованные viewport, cursor, selection, layout и render pipeline в законченный инженерный viewer.

Обязательные задачи:

1. Реальный LAS-open workflow через существующий импортёр. **COMPLETED v180**
2. Полноценное построение multi-track viewer из LAS curves. **COMPLETED v181**
3. Общие depth viewport, cursor и selection. **COMPLETED v182**
4. Track configuration: порядок, ширина, шкала, видимость. **COMPLETED v183**
5. Zoom, pan, fit, reset и стабильная работа на больших LAS. **COMPLETED v184**
6. Экспорт текущего вида в SVG/PDF через Visualization Engine. **COMPLETED v185**
7. Ошибки, пустые кривые, null intervals и invalid units. **COMPLETED v186**

Definition of Done:

- пользователь открывает LAS и получает рабочий viewer без ручной подготовки payload;
- интерактивность и экспорт используют одни контракты;
- состояние viewer восстанавливается без сохранения raw dataframe в UI session;
- viewer проходит функциональные, performance и export-тесты.

### Stage 3 — Modern Workbench and new main page

Status: **COMPLETED v193**

Цель: один раз выполнить полноценный редизайн после стабилизации графического ядра.

Обязательные задачи:

1. Workbench shell и navigation model. **COMPLETED v187**
2. Dock Manager и панели инструментов. **COMPLETED v188**
3. Command Framework и Event Bus integration. **COMPLETED v189**
4. LAS Viewer как основной рабочий модуль. **COMPLETED v190**
5. Project/recent-session entry points без дублирования навигации. **COMPLETED v191**
6. Полный responsive и accessibility audit. **COMPLETED v192**
7. Production entry-point integration: Modern Workbench по умолчанию, legacy UI только через явный process-level fallback. **COMPLETED v193**

Запрещено до Stage 3:

- косметически переделывать главную страницу;
- создавать второй параллельный UI workflow;
- переносить вычисления в UI.

### Stage 4 — Workbench UI Completion

Status: **IN PROGRESS v208 — functional menu, branding and remaining workflow acceptance**

Цель: превратить подключённый production Workbench из минимального shell в полноценное инженерное рабочее окружение до подключения следующих domain-модулей.

Обязательные задачи:

1. Полноэкранный application layout без неиспользуемой центральной области. **COMPLETED v195**
2. Верхний command toolbar/ribbon, использующий существующий Command Framework. **COMPLETED v196**
3. Центральный workspace-host для LAS Viewer и последующих инженерных модулей. **COMPLETED v196**
4. Project Explorer слева с сериализуемым project-tree contract. **COMPLETED v196**
5. Context-sensitive Properties panel справа без domain-вычислений в UI. **COMPLETED v196**
6. Status bar: активный проект, скважина, LAS, viewport/scale и operational status. **COMPLETED v196**
7. Реальное размещение, collapse/restore и изменение размеров dock panes в поддерживаемых Streamlit границах. **COMPLETED v196**
8. Responsive, keyboard-navigation и accessibility regression для нового layout. **COMPLETED v197**
9. Smoke-проверка production startup и основных navigation/tool workflows. **AUTOMATED COMPLETE v197; LIVE ACCEPTANCE FAILED**
10. Runtime build/source identity visible in UI. **COMPLETED v198**
11. Launcher port ownership and stale-process protection. **COMPLETED v198**
12. Live acceptance on the owner environment with confirmed five-region layout. **COMPLETED v198**
13. Professional UX redesign: readable ribbon, balanced panels, dominant workspace, compact dock controls and visual hierarchy. **IMPLEMENTED v199; LIVE FIXES v200**
14. Production interaction acceptance: unobscured title bar, visible active navigation, deterministic command feedback, and state-aware dock commands. **COMPLETED v200**
15. Command-backed quick actions and visible workspace-context transitions in the empty production workspace. **COMPLETED v201**
16. Live visual acceptance of the redesigned Workbench. **COMPLETED v201**
17. Existing LAS import/analysis, LAS editor and LAS correlation screens embedded in the central Workbench host. **COMPLETED v202**
18. Existing interpretation graphs, printable reports, export archive and Documentation Center routed through the single Workbench navigation model. **COMPLETED v202**
19. Live functional acceptance: upload a LAS, edit/create LAS, view graphs, generate/download a report and open documentation. **FAILED IN v202 — modules changed navigation state but real workflows were not observable**
20. Workbench Module Integration Audit: for every route confirm command → state → renderer → provider → visible workflow → user result. **ACTIVE v203**
21. Centralized runtime diagnostics: correlation ID, rotating log traceback, compact incident state, command failure events and module-binding snapshot. **IMPLEMENTED v203**
22. Developer Diagnostics panel behind an explicit process flag; no diagnostics runtime objects in normal presentation state. **IMPLEMENTED v203**
23. Production acceptance gates for each route: module loaded, controls visible, input accepted, output visible/downloadable, no traceback. **REQUIRED BEFORE CLOSURE**
24. Browser form/accessibility findings: stable widget keys, labels and supported autocomplete semantics where Streamlit permits control. **PLANNED AFTER MODULE BINDING**
25. Arrow-safe UI tables: normalize mixed presentation columns before Streamlit serialization. **COMPLETED v204**
26. Streamlit API compatibility: replace deprecated raw HTML component usage and capture Streamlit/PyArrow warnings in the single rotating application log. **COMPLETED v205**
27. Module Render Audit: log route resolution, provider, renderer, start/completed/failed phase, duration and expected visible controls for every Workbench route. **COMPLETED v205**
28. Live module acceptance using render-audit evidence and visible controls for LAS, Interpretation, Reports, Exports and Documentation. **FAILED AFTER v205 OWNER TEST — renderers completed but controls were pushed below an empty fixed-height shell**
29. Functional visibility repair: remove the empty fixed-height HTML workspace shell so native Streamlit controls render immediately inside the central column. **COMPLETED v206**
30. Repeat live acceptance for LAS upload/editor/viewer, Interpretation, Reports, Exports and Documentation. **FAILED AFTER v206 OWNER TEST — dead menu/tree controls and missing Data Workspace blocked calculations**
31. Restore Data Workspace as a first-class Workbench route and replace decorative top-menu/Project Explorer entries with command-backed buttons. **COMPLETED v207**
32. Restore the end-to-end flow Data input → calculation → Interpretation → Reports, with an actionable Reports prerequisite state. **COMPLETED v207; LIVE ACCEPTANCE REQUIRED**
33. Replace silent File/Project labels with real project/session controls and move the single compact brand logo to the Workbench title bar; remove the duplicate Documentation logo overlay. **COMPLETED v208; LIVE ACCEPTANCE REQUIRED**

Definition of Done:

- после запуска пользователь получает заполненное инженерное рабочее пространство, а не список shell-кнопок;
- центральный workspace занимает доступную площадь и отображает активный модуль;
- Project Explorer, Properties, Toolbar и Status Bar используют только application/render contracts;
- LAS Viewer открывается внутри workspace-host;
- UI не содержит repository/file operations, инженерные вычисления или raw DataFrame;
- responsive/accessibility, Workbench regression и preflight проходят;
- каждая runtime-ошибка получает correlation ID и полный traceback в `logs/app.log`;
- route считается интегрированным только когда отображается и выполняется реальный пользовательский workflow, а не только меняется navigation state.

### Stage 5 — Petrophysical Engine

Status: **BLOCKED — starts only after confirmed Stage 4 live production acceptance**

- подтверждённые формулы и единицы;
- transparent calculation contracts;
- petrophysical curves and quality flags;
- integration with LAS Viewer and reports.

### Stage 6 — Modeling Engine

Status: **PLANNED**

- correlation;
- structural/facies/property modeling;
- 2D/3D visualization;
- plugin/API extensibility.

## 4. Замороженные боковые направления

До подтверждённого завершения Stage 4 и последующего Petrophysical Engine не расширять:

- bookmarks/recent-session convenience features;
- audit report exchange and signing infrastructure;
- licensing and activation;
- telemetry;
- cloud collaboration;
- AI assistant.

Существующий код сохраняется и поддерживается только на уровне исправления критических дефектов.

## 5. Изменение roadmap

Roadmap изменяется только когда:

1. найден архитектурный блокер;
2. изменилось подтверждённое требование владельца проекта;
3. текущий этап завершён по Definition of Done.

Любое изменение отражается в `PROJECT_ROADMAP.md` и `PROJECT_STATUS.md`; история фиксируется в `CHANGELOG.md`. Новые plan/status файлы не создаются.
