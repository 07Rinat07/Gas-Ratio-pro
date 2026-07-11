# GAS RATIO PRO — Active Project Roadmap

Status: Active  
Baseline: v197  
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

Status: **COMPLETED v197**

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
9. Smoke-проверка production startup и основных navigation/tool workflows. **COMPLETED v197**

Definition of Done:

- после запуска пользователь получает заполненное инженерное рабочее пространство, а не список shell-кнопок;
- центральный workspace занимает доступную площадь и отображает активный модуль;
- Project Explorer, Properties, Toolbar и Status Bar используют только application/render contracts;
- LAS Viewer открывается внутри workspace-host;
- UI не содержит repository/file operations, инженерные вычисления или raw DataFrame;
- responsive/accessibility, Workbench regression и preflight проходят.

### Stage 5 — Petrophysical Engine

Status: **ACTIVE v197 — starts after confirmed Stage 4 production completion**

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

До завершения активного Petrophysical Engine не расширять:

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

Любое изменение должно быть отражено одновременно в `PROJECT_ROADMAP.md`, `PROJECT_STATUS.md` и `CHANGELOG.md`.
