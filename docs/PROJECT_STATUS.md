# GAS RATIO PRO — Current Project Status

Baseline: v188  
Current stage: Modern Workbench and new main page  
Last fully verified baseline: v188 — application-level Dock Manager controls pane open/close/collapse/restore/focus through the command framework and Event Bus; registered Workbench tools are connected to serializable dock panes; preflight OK.

## 1. Что подтверждено кодом и тестами

Visualization Engine:

- Domain Model, Scene, Layout и Render Model;
- Axis/Grid, Track, Curve Quality, Label/Legend и Print Layout;
- SVG/PDF renderers и geometry signature parity;
- adaptive downsampling, cache и memory budget;
- viewport, pan/zoom, hit testing, cursor и selection;
- render/export QA и Render Validation Pipeline;
- strict export enforcement: SVG/PDF export блокируется при fatal/error geometry findings;
- три эталонные multi-track сцены для linear, Unicode и overlay regression;
- утверждённые SVG/PDF reference artifacts с SHA-256 manifest и structural regression checks.

LAS Viewer foundation:

- viewer session и track layout;
- viewport-aware render pipeline;
- synchronized cursor/selection overlays;
- workspace persistence/autosave foundations.

## 2. Что не считается завершённым

- Command Framework и Event Bus требуют финальной интеграции на уровне Workbench shell.
- Responsive и accessibility audit ещё не выполнены.

## 3. Следующий разрешённый инкремент

**Complete Command Framework and Event Bus integration for the Workbench shell.**

Состав:

1. единый command dispatch для navigation, tools и dock lifecycle;
2. нормализованные события Workbench shell без прямых UI state mutations;
3. согласованное обновление active module, tool pane и dock focus;
4. renderer-facing event/command contract без бизнес-логики;
5. unit, integration и regression tests.

Dock Manager и tool panels завершены в v188.

Stage 4 Petrophysical Engine в следующий инкремент не входит.

## 4. Критерий перехода к LAS Viewer

Переход разрешён, когда:

- reference scenes проходят validation без fatal findings;
- SVG/PDF parity подтверждён;
- Unicode и печатные размеры проверены;
- large-LAS performance regression проходит;
- full tests и preflight зелёные.
