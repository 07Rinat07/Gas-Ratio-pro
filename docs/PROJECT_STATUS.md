# GAS RATIO PRO — Current Project Status

Baseline: v191  
Current stage: Modern Workbench and new main page  
Last fully verified baseline: v191 — project and recent-session entry points use command-backed application services, existing Workbench navigation routes and lightweight session restoration without direct repository/file operations in UI; preflight OK.

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

- Responsive и accessibility audit ещё не выполнены.

## 3. Следующий разрешённый инкремент

**Perform the full responsive and accessibility audit for Modern Workbench.**

Состав:

1. responsive shell/layout behavior for supported viewport classes;
2. keyboard navigation and focus order;
3. accessible labels, roles and action descriptions in renderer contracts;
4. contrast/readability audit for the active Workbench presentation;
5. unit, integration and regression tests.

Project/recent-session entry points завершены в v191.

Stage 4 Petrophysical Engine в следующий инкремент не входит.

## 4. Критерий перехода к LAS Viewer

Переход разрешён, когда:

- reference scenes проходят validation без fatal findings;
- SVG/PDF parity подтверждён;
- Unicode и печатные размеры проверены;
- large-LAS performance regression проходит;
- full tests и preflight зелёные.
