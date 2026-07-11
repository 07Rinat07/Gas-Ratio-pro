# GAS RATIO PRO — Current Project Status

Baseline: v186  
Current stage: Modern Workbench and new main page  
Last fully verified baseline: v186 — LAS Viewer now handles malformed curves, empty/all-null curves, partial null intervals and unsupported units through one renderer-neutral validation contract; Stage 2 Definition of Done is complete; preflight OK.

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

- Modern Workbench и новая главная страница ещё не собраны как единый shell.
- Существующие workbench-компоненты должны быть сведены в один navigation model без параллельного UI workflow.
- LAS Viewer завершён как инженерное ядро и должен подключаться к Workbench без переноса бизнес-логики в UI.

## 3. Следующий разрешённый инкремент

**Build the Modern Workbench shell and navigation model.**

Состав:

1. собрать единый application-level Workbench shell;
2. определить единый navigation model для основных рабочих модулей;
3. подключить LAS Viewer как основной модуль через существующие service contracts;
4. исключить прямую бизнес-логику и файловые операции из UI;
5. покрыть unit, integration и regression tests.

Track configuration, interaction, export и curve validation LAS Viewer завершены в Stage 2.

Stage 4 Petrophysical Engine в следующий инкремент не входит.

## 4. Критерий перехода к LAS Viewer

Переход разрешён, когда:

- reference scenes проходят validation без fatal findings;
- SVG/PDF parity подтверждён;
- Unicode и печатные размеры проверены;
- large-LAS performance regression проходит;
- full tests и preflight зелёные.
