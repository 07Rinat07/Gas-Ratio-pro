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

### Stage 4W — Workbench Stabilization and Information Architecture

Status: **IN PROGRESS v214**

Цель: устранить ложные состояния, дублирующую навигацию и визуальный хаос до перехода к новому Well Log Renderer.

Обязательные задачи:

1. Разделить текущую рабочую сессию и архив проекта.
2. Не показывать предупреждения, integrity-check и экспорт архивного расчета без явного открытия пользователем.
3. Оставить один основной уровень навигации; ribbon использовать только для контекстных команд активного модуля.
4. Синхронизировать Project Explorer с реальными объектами и счетчиками проекта.
5. Добавить понятные empty states для проекта, LAS и расчетов.
6. Провести live visual acceptance на широком и обычном desktop-разрешении.

Definition of Done:

- пустая рабочая сессия не показывает ошибки и предупреждения архивных расчетов;
- архивные snapshots открываются только по явному действию;
- верхнее меню, Explorer и ribbon не дублируют одну и ту же навигацию;
- счетчики Explorer соответствуют проекту;
- центральная рабочая область визуально доминирует над служебными панелями.

### Stage 4 — Workbench UI Completion

Status: **IN PROGRESS v213 — live acceptance failed for professional visualization, reporting and runtime responsiveness; controlled refactor approved**

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

### Stage 4R — Engineering Presentation Refactor

Status: **ACTIVE — approved after v213 live review**

Цель: заменить накопившиеся patch-level решения в визуализации, корреляции и отчетности единым инженерным presentation pipeline без изменения проверенной расчетной логики.

#### 4R.1. Refactor boundaries

В рефакторинг входят только следующие подсистемы:

1. `WellLogRenderModel` и профессиональный multi-track планшет.
2. `CorrelationRenderModel` и синхронизированная multi-well визуализация.
3. `DiagnosticPlotModel` для Pixler и ternary.
4. `ReportDocumentModel` и независимые PDF/DOCX/HTML renderers.
5. Streamlit state/rerun boundary для тяжелых графиков и экспорта.
6. Interval consolidation и правила отбора интервалов для пользовательских отчетов.

В рефакторинг **не входят** новые петрофизические формулы, геомоделирование, 3D и новые domain-модули.

#### 4R.2. Architectural target

```text
CalculationResult
→ ValidatedInterpretationDataset
→ PresentationModels
   ├─ WellLogRenderModel
   ├─ CorrelationRenderModel
   ├─ PixlerModel
   ├─ TernaryModel
   └─ ReportDocumentModel
→ Independent Renderers
   ├─ Interactive Plotly/Streamlit
   ├─ Static SVG/PNG
   ├─ PDF
   ├─ DOCX
   └─ HTML
```

Требования:

- UI не вычисляет инженерные показатели;
- каждый renderer получает готовую типизированную модель;
- экран и печать используют одинаковые диапазоны, единицы, подписи и interval selection;
- PDF и DOCX не строятся путем слепого копирования HTML-таблиц;
- raw diagnostics и внутренние dict/list структуры не попадают в пользовательские документы;
- изменение UI-настроек не перечитывает LAS и не запускает расчет заново.

#### 4R.3. Implementation sequence

**R1 — State and performance foundation**

- убрать оставшиеся конфликты widget default/session state, включая `interpretation_tablet_marker_count`;
- перенести mapping, tablet settings и export settings в подтверждаемые формы;
- кэшировать LAS parsing по content hash;
- разделить data revision, calculation revision и presentation revision;
- запретить построение пяти тяжелых фигур на нерелевантном rerun;
- заменить непонятный floating running indicator на нормальный inline status;
- добавить измерение `parse_ms`, `calculation_ms`, `model_ms`, `render_ms`, `export_ms`.

**R2 — Professional Well Log Renderer**

- единая depth axis;
- компактные track headers с названием, единицами и шкалой;
- linear/log scale;
- стандартные grid/ticks;
- ограничение числа треков на лист;
- автоматический active-depth window с ручным override;
- interval lane вместо десятков пересекающихся горизонтальных линий;
- отдельные screen и print presets при общей модели;
- визуальные golden tests для A4 portrait, A4 landscape и wide screen.

**R3 — Pixler, ternary and validation plots**

- модели строятся по набору всех валидных строк, а не по случайной первой строке;
- явные причины исключения точек;
- нормализация и фильтрация NaN/Inf/zero denominator до renderer;
- минимум одна валидная точка отображается;
- пустое состояние содержит агрегированную диагностику, а не каскад повторяющихся предупреждений.

**R4 — Correlation Workspace**

- минимум две реальные скважины;
- общий depth window и синхронный zoom/scroll;
- выбор кривых и tops;
- нормальные масштабы по каждой скважине;
- отсутствие пустой геологической панели;
- экспорт correlation board в SVG/PDF/PNG через тот же render model.

**R5 — Reports v4**

- инженерный отчет: 6–10 страниц;
- экспертный отчет: ограниченный основной документ плюс приложения CSV/XLSX/JSON;
- PDF renderer с фиксированными page templates;
- DOCX renderer через `python-docx` с управляемыми widths, captions и page breaks;
- HTML renderer без raw diagnostic structures;
- таблицы максимум 5–6 смысловых колонок;
- длинные заключения выводятся карточками/абзацами, а не узкой колонкой;
- нулевые интервалы исключаются из основного отчета;
- одинаковые русские термины и единицы во всех форматах.

**R6 — Interval consolidation and acceptance**

- объединять соседние интервалы одного типа по настраиваемому depth gap;
- одиночные точки маркировать как anomalies, а не полноценные пласты;
- отдельно считать raw candidates и consolidated intervals;
- live acceptance на одном и нескольких LAS;
- regression, golden-image, document-layout и performance gates.

#### 4R.4. Definition of Done

Рефакторинг завершен только если одновременно выполнено следующее:

- смена вкладки без изменения данных не перечитывает LAS и не пересчитывает формулы;
- обычный navigation rerun не показывает пустой floating square;
- Interpretation cached rerender укладывается в целевой бюджет до 2 секунд на тестовом LAS;
- профессиональный планшет читаем на экране и на A4, без пустых 60–70% листа;
- Pixler и ternary отображают валидные точки либо одну понятную агрегированную причину отсутствия данных;
- correlation открывается без route errors и показывает минимум две скважины;
- инженерный PDF/DOCX не содержит вертикального текста, raw keys, нулевых интервалов и повторяющихся таблиц;
- PDF, DOCX и HTML проходят визуальную приемку пользователем;
- Stage 5 остается заблокирован до полного закрытия Stage 4R.

#### 4R.5. First authorized increment

Следующий разрешенный инкремент: **v214 — Presentation Refactor Foundation**.

Текущий прогресс: explicit mapping apply, explicit interpretation run и explicit presentation/tablet build реализованы; inline runtime status и оставшиеся вторичные presentation/export boundaries являются следующим подэтапом.

Состав:

1. revision-based state model;
2. устранение всех widget/session-state conflicts;
3. deferred tablet/export forms;
4. LAS parse cache;
5. inline progress state вместо floating indicator;
6. базовые типы `WellLogRenderModel` и `ReportDocumentModel`;
7. characterization tests текущего поведения перед заменой renderers.

До завершения v214 запрещено одновременно переписывать PDF, DOCX и correlation renderer: сначала должен быть стабилизирован общий state/model boundary.

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

## Stage 4 corrective increment — v209

- [x] Expose a dedicated `nav.correlation` route in the top menu, LAS workflows and Project Explorer.
- [x] Reuse the existing multi-well LAS correlation renderer and export controls.
- [x] Move the engineering well-log figure before long report tables.
- [x] Limit the engineering profile to the 15 strongest non-zero-thickness intervals.
- [x] Move full interval reasoning to the expert appendix.
- [x] Add static Plotly-to-PDF rendering with a controlled Kaleido fallback.
- [x] Connect Project Explorer object clicks to Workbench Selection Service.
- [x] Render contextual Properties for project, well, LAS, curve and collection selections.
- [x] Replace technical empty Properties rows with an actionable empty state.
- [x] Prevent Developer Diagnostics from rendering inside a collapsed narrow dock rail.
- [x] Preserve Properties collapse/restore state through the existing Dock Manager.
- [ ] Live acceptance: load two wells, render correlation, export correlation, generate PDF with embedded plot.


## Stage 4 corrective increment — v210

- [x] Stop implicit professional report generation on every Streamlit rerun.
- [x] Batch profile/format controls behind an explicit prepare action.
- [x] Keep prepared export bytes in the existing session state.
- [x] Make the download label, MIME type and filename match the prepared format.
- [x] Add timing/error logging for presentation export.
- [x] Reuse unchanged interpretation figure sets across reruns.
- [ ] Complete live acceptance for HTML, PDF, DOCX and bundle downloads on Windows.


## Stage 4 corrective increment — v211

- строгая валидация mapping C1, C2, C3, iC4, nC4, iC5, nC5;
- блокировка расчета при неполном mapping;
- очистка устаревших графиков/отчетов при смене источника;
- явный текстовый индикатор подготовки экспорта вместо пустого spinner;
- acceptance: новый файл с неверным mapping не может показывать графики предыдущего расчета.

### Stage 4 — v212 printable-report acceptance
- [x] Remove widget/session-state conflict for tablet track selection.
- [x] Remove raw Python diagnostic payloads from printable reports.
- [x] Crop report tablets to active data and limit interval overlays.
- [x] Embed plot images into DOCX instead of renderer placeholders.
- [ ] Live acceptance: PDF, DOCX, HTML and browser printing on Windows.
- [ ] Confirm no floating empty status box during navigation and export settings.

- v213: repair correlation route registration, printable plot depth crop, report table density, and valid interval defaults.


## Stage 4R v214 export preparation boundary

- [x] Generate PNG/PDF/SVG only after an explicit prepare action.
- [x] Cache static Plotly artifacts by source signature, presentation revision and export dimensions.
- [x] Generate interpretation HTML and printable interval reports only after explicit preparation.
- [x] Generate selected-interval CSV only after explicit preparation.
- [x] Generate LAS-correlation HTML only after explicit preparation.
- [x] Increment export revision only when artifact bytes are generated.
- [ ] Complete live Windows acceptance with Kaleido installed for PNG/PDF/SVG.

### Stage 4W Dataset lifecycle hardening
- [x] Audit active, archived and orphan dataset storage per table section.
- [x] Add safe cleanup actions with project ID confirmation.
- [x] Create automatic ZIP backup before bulk dataset cleanup.
- [x] Rebuild manifests and project index after deletion.

### Stage 4W — Project Database table lifecycle (completed)

- Separate derived metadata cleanup from user-file deletion.
- Add synchronized maintenance for file index, file versions and UUID registry.
- Add safe compaction/reset with automatic project backup.
- Permit real-file cleanup only for verified exact duplicates with explicit confirmation.

- [x] Improve Project Database tables with filtering, sorting, pagination and optional technical metadata.

### Unified Workbench Data Grid

- [x] Project Database tables
- [x] Dataset Manager tables
- [x] Saved calculation archive
- [x] Project export catalog
- [ ] Dedicated persisted report catalog, after Report Repository is introduced

### Unified Workbench Data Grid — selection boundary

- [x] Publish selected Dataset rows to Properties.
- [x] Publish selected Calculation rows to Properties.
- [x] Publish selected Export rows to Properties.
- [x] Remove duplicate selectors below unified grids.
- [x] Move contextual object actions into Properties.
- [ ] Add multi-selection and bulk actions.
- [ ] Extend selection to all Project Database tables.

### Workbench UX Refactor — Project Explorer 2.0

- [x] Replace the flat Explorer counter list with the persisted metadata-only project hierarchy.
- [x] Add expandable project, folder, well group, well, LAS version, calculation and export nodes.
- [x] Add project-object search that retains ancestor context.
- [x] Synchronize Explorer selection with Properties through WorkbenchSelectionService.
- [x] Add compact ready/warning/error/empty status markers.
- [ ] Add persisted report and correlation nodes after their repositories are available.
- [x] Move contextual actions to Properties.
- [ ] Add safe multi-selection and bulk actions.

- [x] Unified Data Grid multi-selection and safe bulk actions for datasets, calculations and exports.

### Calculation Diagnostics 2.0

- [x] Structured C1–nC5 column quality report.
- [x] Per-formula valid/invalid row counts.
- [x] Missing-input, zero-denominator and non-numeric cause counts.
- [x] Problem-row preview and concrete recommendations.
- [x] Replace repeated NaN banners with grouped diagnostics UI.
- [ ] Persist diagnostics snapshots with saved calculations.
- [ ] Add diagnostics comparison between calculation revisions.
- [ ] Export diagnostics into PDF and DOCX reports.

### Persisted Calculation Diagnostics Snapshot

- [x] Store structured diagnostics with each new saved calculation.
- [x] Validate diagnostics JSON during calculation integrity checks.
- [x] Preserve backward compatibility with older snapshots.
- [ ] Display persisted diagnostics after restart without recalculation.
- [ ] Add LAS NULL and sampling-density diagnostics.

- Regression guard added for methodology warning imports used by the Data workspace.

- [x] Preserve active calculation across Data, Interpretation and Reports navigation.
- [x] Add project-bound guard for shared calculation state.


### Completed: durable Data to Interpretation handoff
- Preserve the last explicit calculation across Workbench workspace transitions.
- Invalidate it only on explicit mapping reset, project change, LAS reset or manual cleanup.

- [x] Fix active calculation revision contract used by Data → Interpretation handoff.

- Completed compatibility hardening for revision snapshots used by Data → Interpretation handoff.

- Interpretation first-render fix: initial graphs/tablet now auto-commit on first valid calculation; explicit button remains for later settings changes. Streamlit marker/zone count widgets now use Session State as the single source of truth.

- [x] Stabilize Interpretation full-interval rendering/export metadata and tablet marker/zone widget state.

### Completed: Engineer-oriented interpretation tables
- interval-first summary in Interpretation workspace;
- scrollable calculation and interval tables;
- printable interval registry and decision-oriented executive summary.

## 4. Active engineering refactor — Reservoir Intelligence / Interpretation 2.0

This is the current product priority. The goal is to replace technically correct but weak visual output with an engineer-facing interpretation workspace.

### 4.1 Information architecture and terminology

- [x] Remove dataframe row counters from the primary interpretation summary.
- [x] Show interval, top/base, thickness, probable fluid, confidence, data quality, geological support and conclusion.
- [ ] Add interval filters by fluid, depth, thickness, confidence and review status.
- [ ] Synchronize table selection with Pixler, ternary, depth tracks and interval passport.
- [ ] Keep rows/cells/counts only in Diagnostics and Developer mode.

### 4.2 Pixler rehabilitation

- [ ] Plot all valid samples for the selected interval instead of a single decorative polyline.
- [ ] Add selected-depth marker, interval centroid/median and interval trend.
- [ ] Add named interpretation fields with explicit methodology status.
- [ ] Show depth, ratio, classification, data quality and method agreement in hover details.
- [ ] Explain what the graph supports, contradicts or cannot determine.
- [ ] Provide dark interactive and light print render profiles from one plot model.

### 4.3 Ternary rehabilitation

- [ ] Plot the interval point cloud, selected depth and robust center.
- [ ] Show percentages of valid points by interpretation region.
- [ ] Distinguish confirmed methodology boundaries from project draft boundaries.
- [ ] Report component completeness and points outside defined regions.
- [ ] Link ternary classification to the common confidence engine.

### 4.4 Depth engineering panel

- [x] Use a shared reversed depth axis across every track.
- [x] Add Total Gas, C1–C5, Wh/Bh/Ch, Pixler ratios, reservoir type and confidence tracks.
- [x] Draw top/base boundaries, interval fills, IDs, thickness and selected-depth marker.
- [ ] Use logarithmic scale only for curves whose physical range requires it.
- [x] Never replace missing measurements with zero for presentation.
- [ ] Add practical track presets and readable print layout.
- [x] Add collision-aware interval labeling: suppress tiny/overlapping labels, show selected interval prominently and keep full details in hover.
- [x] Add a compact QC/recommendation track with hover details instead of long text inside the depth panel.

### 4.5 Interval passport and method agreement

- [ ] Show interval ID, top, base, thickness, probable fluid and confidence.
- [ ] Show robust interval statistics for gas components and calculated ratios.
- [ ] List supporting, conflicting and unavailable methods.
- [ ] Show data limitations and concrete verification recommendations.
- [ ] Keep water, non-productive and insufficient-data conclusions methodologically distinct.

### 4.6 Reporting profiles

- [ ] Customer Summary: concise deliverable for the customer, focused on intervals, confidence, limitations and recommendations.
- [ ] Engineering Report: full working interpretation with plots, interval registry, passports and methodology agreement.
- [ ] Technical Report: reproducible audit with mapping, formulas, diagnostics and calculation provenance.
- [ ] Export figures from the shared plot model; do not use UI screenshots.
- [ ] Produce vector or high-resolution print-safe figures for PDF and DOCX.

### 4.7 Refactoring and quality gates

- [ ] Separate interval analytics, plot models, Plotly renderers and report renderers.
- [ ] Reduce `app/streamlit_app.py` by moving interpretation business logic out of UI functions.
- [ ] Add golden-data tests for Pixler, ternary and depth panel classification.
- [ ] Add visual/export smoke tests for dark screen and light print profiles.
- [ ] Each graph must answer: what, where, interpretation, evidence, confidence and limitation.

### Definition of Done

The stage is complete only when an engineer can select an interval and obtain synchronized Pixler, ternary, depth panel, interval passport and printable reports without reading dataframe counters or developer diagnostics.

### Pixler 2.0 — interval-aware visualization (implemented foundation)
- [x] Use all valid measurements of the selected hydrocarbon interval instead of a single row.
- [x] Show interval median and a separate marker for the selected depth.
- [x] Overlay configurable interpretation zones and an engineer-facing conclusion.
- [ ] Validate zone limits against approved corporate methodology and field calibration.
- [ ] Add interval selector synchronization with the reservoir register and passport.
- [x] Ternary 2.0 interval foundation: cloud of valid interval measurements, normalized median center, selected-depth marker, configured methodological regions, completeness assessment and engineering conclusion.
- [x] Depth Panel 2.0 foundation: shared reversed depth axis, fluid-colored interval fills, explicit top/base boundaries, interval ID, thickness and selected-depth marker.
- [x] Depth Panel 2.0 engineering tracks: separate Reservoir Type, Confidence and Recommendations tracks driven by the common interval model.

- [x] Depth Panel readability hotfix: removed repeated Depth titles, suppressed overlapping HC labels and confidence text, reduced full-width boundaries, and moved recommendation detail to hover-only QC markers.

### Axis, depth and print controls
- [x] Use factual LAS top/base as the default Y range; never introduce an empty 0..top-depth segment.
- [x] Keep manual depth-from/depth-to controls for the interpretation workspace.
- [x] Add persisted manual Y limits for the Pixler logarithmic crossplot.
- [x] Add an independent depth-from/depth-to interval for PDF/DOCX report generation.
- [ ] Extend the reusable manual X/Y axis contract to correlation and remaining project charts.
- [ ] Add print presets for current interval, selected reservoir and full well.


## Reporting format policy

- [x] Remove user-facing HTML print/export.
- [x] Keep PDF and DOCX as primary professional report formats.
- [x] Keep a PDF + DOCX package for convenient delivery.
- [ ] Continue synchronized interval selection and the two Depth Panel viewing modes.

## Completed: synchronized interval viewing

- [x] Whole-well overview mode.
- [x] Detailed selected-interval mode.
- [x] Adaptive depth-panel height.
- [x] Minimum interval thickness visualization filter.
- [x] Shared selected interval state for the interpretation workspace.
- [x] Selected interval passport foundation.

Next: use the same selection context in the Data workspace Pixler and ternary selectors and in report generation without duplicating interval detection.

## Completed: shared selected interval in Data Workspace and report export

- [x] Drive Data Workspace Pixler and ternary from `selected_reservoir_interval_id`.
- [x] Keep the selected reservoir synchronized between Data Workspace and Interpretation without overwriting a new user choice during rerun.
- [x] Use the selected reservoir top/base as the default PDF/DOCX print interval.
- [x] Preserve manual and current-graph print interval modes as explicit alternatives.

- [x] Выбор инженерного интервала кликом по строке таблицы с общей синхронизацией Pixler, ternary, Depth Panel, паспорта и PDF/DOCX.

- [x] Engineering Navigation 2.0: предыдущий/следующий интервал, центрированное окно таблицы и визуальный маркер активного пласта.

- [x] Unified compact Engineering Header for the selected reservoir above Pixler, ternary and Depth Panel.
- [x] Fluid-colored active-row markers shared by engineering interval tables.

### Reservoir Passport 2.0 — выполнено
- [x] Газовый состав C1–C5 по интервалу.
- [x] Производные коэффициенты и отношения.
- [x] Результаты Pixler, ternary и Haworth.
- [x] Индекс согласованности методик.
- [x] Ограничения, рекомендации и готовность к PDF/DOCX.


## Reservoir Ranking (v214)

- Добавлен прозрачный индекс инженерного приоритета 0–100.
- Весовые компоненты: достоверность 30%, согласованность методик 30%, полнота C1–C5 20%, валовая мощность 20%.
- Нулевые по мощности одиночные точки и неопределённый флюид получают явные штрафы.
- Рейтинг не является оценкой запасов, net pay, насыщенности или коммерческой ценности.
- Выбор строки рейтинга синхронизирует активный интервал, Pixler, ternary, Depth Panel, паспорт и PDF/DOCX.

### Reservoir Ranking 2.0 — выполнено

- [x] Встроенные инженерные профили ранжирования.
- [x] Ручная настройка и автоматическая нормализация весов.
- [x] Сохранение пользовательских профилей в проекте.
- [x] Сравнение текущего рейтинга с выбранным базовым профилем.
- [x] Объяснение изменения места и итогового индекса.
- [x] Передача активного профиля в PDF/DOCX.

Следующий этап: Cross-Method Analysis — структурированный анализ согласий и противоречий Pixler, ternary и Haworth с инженерным объяснением причин расхождений.

## Explainable Interpretation Engine

- [x] Единый формат результата методик.
- [x] Анализ согласия и противоречий Pixler, ternary и Haworth.
- [x] Матрица согласованности.
- [x] Вклад методик в итоговую классификацию.
- [x] QC и причины возможных расхождений.
- [x] Разложение уверенности.
- [x] Интеграция с Reservoir Passport и PDF/DOCX.
- [ ] Расширение Method Library новыми методиками.

## Method Framework 1.0

- [x] Added the common `BaseMethod`, `MethodContext` and `MethodResult` contracts.
- [x] Added an ordered `MethodRegistry` and default registry factory.
- [x] Moved Pixler, ternary and Haworth interval analysis behind the common method interface.
- [x] Changed Reservoir Passport to execute registered methods instead of calling method-specific analyzers directly.
- [x] Added non-throwing unavailable-result diagnostics for missing method inputs.
- [ ] Move plot descriptions behind the same method capability contract.
- [ ] Add project-level enable/disable configuration for registered methods.
- [ ] Add new published methods only through the framework.
