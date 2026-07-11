# GAS RATIO PRO — Active Project Roadmap

Status: Active  
Baseline: v179  
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

Status: **ACTIVE**

Цель: собрать уже реализованные viewport, cursor, selection, layout и render pipeline в законченный инженерный viewer.

Обязательные задачи:

1. Реальный LAS-open workflow через существующий импортёр.
2. Полноценное построение multi-track viewer из LAS curves.
3. Общие depth viewport, cursor и selection.
4. Track configuration: порядок, ширина, шкала, видимость.
5. Zoom, pan, fit, reset и стабильная работа на больших LAS.
6. Экспорт текущего вида в SVG/PDF через Visualization Engine.
7. Ошибки, пустые кривые, null intervals и invalid units.

Definition of Done:

- пользователь открывает LAS и получает рабочий viewer без ручной подготовки payload;
- интерактивность и экспорт используют одни контракты;
- состояние viewer восстанавливается без сохранения raw dataframe в UI session;
- viewer проходит функциональные, performance и export-тесты.

### Stage 3 — Modern Workbench and new main page

Status: **BLOCKED BY STAGE 2**

Цель: один раз выполнить полноценный редизайн после стабилизации графического ядра.

Обязательные задачи:

1. Workbench shell и navigation model.
2. Dock Manager и панели инструментов.
3. Command Framework и Event Bus integration.
4. LAS Viewer как основной рабочий модуль.
5. Project/recent-session entry points без дублирования навигации.
6. Полный responsive и accessibility audit.

Запрещено до Stage 3:

- косметически переделывать главную страницу;
- создавать второй параллельный UI workflow;
- переносить вычисления в UI.

### Stage 4 — Petrophysical Engine

Status: **PLANNED**

- подтверждённые формулы и единицы;
- transparent calculation contracts;
- petrophysical curves and quality flags;
- integration with LAS Viewer and reports.

### Stage 5 — Modeling Engine

Status: **PLANNED**

- correlation;
- structural/facies/property modeling;
- 2D/3D visualization;
- plugin/API extensibility.

## 4. Замороженные боковые направления

До завершения Stage 3 не расширять:

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
